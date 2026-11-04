from __future__ import annotations

import json
from hashlib import sha256
from typing import Any, Mapping

from backend.app.domain.protocol import (
    Ambiguity,
    CanonicalProtocol,
    ExpectedResultCheckpoint,
    ExtractionProvenance,
    IngestionResult,
    ProcedureStep,
    ProtocolDocument,
    SourceRef,
    SourceSegment,
    TestCase,
    TestSet,
    UnmappedContent,
)
from backend.app.schemas.protocol import AuthoredTestCaseInput
from backend.app.services.ingestion.quality_gate import evaluate_quality


def _stable_id(prefix: str, value: str) -> str:
    return f"{prefix}-{sha256(value.encode('utf-8')).hexdigest()[:16]}"


def _pointer_part(value: str) -> str:
    return value.replace("~", "~0").replace("/", "~1")


def adapt_authored_test_case(
    payload: Mapping[str, Any] | bytes | bytearray | str,
    *,
    original_filename: str = "authored-test-case.json",
) -> IngestionResult:
    """Adapt structured author input without interpreting its natural-language meaning.

    Bytes/JSON strings retain their exact source payload. Mapping inputs use a
    deterministic JSON serialization as the hash basis, which is explicitly
    recorded in document provenance.
    """
    raw_bytes: bytes | None
    source_payload: Any
    if isinstance(payload, Mapping):
        source_payload = dict(payload)
        raw_bytes = None
        serialized = json.dumps(
            source_payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        hash_basis = "canonical_json_serialization"
    elif isinstance(payload, (bytes, bytearray)):
        raw_bytes = bytes(payload)
        source_payload = json.loads(raw_bytes.decode("utf-8"))
        serialized = raw_bytes
        hash_basis = "provided_bytes"
    elif isinstance(payload, str):
        try:
            source_payload = json.loads(payload)
            raw_bytes = payload.encode("utf-8")
            serialized = raw_bytes
            hash_basis = "provided_bytes"
        except json.JSONDecodeError:
            raw_bytes = payload.encode("utf-8")
            source_payload = {"procedure": payload}
            serialized = raw_bytes
            hash_basis = "provided_bytes"
            original_filename = "authored-test-case.txt"
    else:
        raise TypeError("Authored input must be a mapping, JSON bytes/string, or plain-English string.")

    if not isinstance(source_payload, Mapping):
        raise ValueError("Authored test-case JSON must be an object.")
    authored = AuthoredTestCaseInput.model_validate(source_payload)
    source_hash = sha256(serialized).hexdigest()
    document_id = f"authored-{source_hash[:16]}"
    segments: list[SourceSegment] = []
    unmapped: list[UnmappedContent] = []
    order = 0

    def add_segment(pointer: str, text: str, *, mapped: bool) -> SourceRef:
        nonlocal order
        ref = SourceRef(
            document_id=document_id,
            part="authored_json",
            order_index=order,
            json_pointer=pointer,
        )
        segment_id = _stable_id("segment", f"{document_id}:{pointer}:{order}")
        segment = SourceSegment(
            segment_id=segment_id,
            text=text,
            kind="authored_text",
            order_index=order,
            source_ref=ref,
            mapping_status="mapped" if mapped else "unmapped",
        )
        segments.append(segment)
        if not mapped:
            unmapped.append(
                UnmappedContent(
                    segment_id=segment_id,
                    original_text=text,
                    source_ref=ref,
                    reason="Field is outside the Phase 1 authoring adapter contract.",
                )
            )
        order += 1
        return ref

    known_top = {
        "test_set_id", "test_set_title", "test_case_id", "title", "procedure",
        "expected_result", "steps",
    }
    set_ref: list[SourceRef] = []
    if authored.test_set_id is not None:
        set_ref.append(add_segment("/test_set_id", authored.test_set_id, mapped=True))
    if authored.test_set_title is not None:
        set_ref.append(add_segment("/test_set_title", authored.test_set_title, mapped=True))
    case_ref: list[SourceRef] = []
    if authored.test_case_id is not None:
        case_ref.append(add_segment("/test_case_id", authored.test_case_id, mapped=True))
    title_ref = []
    if authored.title is not None:
        title_ref.append(add_segment("/title", authored.title, mapped=True))

    steps: list[ProcedureStep] = []
    expected: list[ExpectedResultCheckpoint] = []
    case_ambiguities: list[Ambiguity] = []
    if authored.steps:
        if authored.procedure is not None:
            ref = add_segment("/procedure", authored.procedure, mapped=False)
            case_ambiguities.append(
                Ambiguity(
                    code="top_level_procedure_with_steps",
                    description="Top-level procedure and an explicit step list coexist; their intended ordering is not inferred.",
                    source_refs=[ref],
                )
            )
        for index, input_step in enumerate(authored.steps):
            base = f"/steps/{index}"
            refs: list[SourceRef] = []
            if input_step.step_id is not None:
                refs.append(add_segment(f"{base}/step_id", input_step.step_id, mapped=True))
            procedure = input_step.procedure or ""
            if input_step.procedure is not None:
                refs.append(add_segment(f"{base}/procedure", input_step.procedure, mapped=True))
            step_ambiguities: list[Ambiguity] = []
            if not procedure.strip():
                step_ambiguities.append(
                    Ambiguity(
                        code="missing_step_procedure",
                        description="This authored step has no non-empty procedure text.",
                        source_refs=refs,
                    )
                )
            steps.append(
                ProcedureStep(
                    sequence=index + 1,
                    stated_identifier=input_step.step_id,
                    original_text=procedure,
                    source_refs=refs,
                    ambiguities=step_ambiguities,
                )
            )
            if input_step.expected_result is not None:
                result_ref = add_segment(
                    f"{base}/expected_result", input_step.expected_result, mapped=True
                )
                expected.append(
                    ExpectedResultCheckpoint(
                        sequence=len(expected) + 1,
                        original_text=input_step.expected_result,
                        source_refs=[result_ref],
                        ambiguities=(
                            [Ambiguity(code="blank_expected_result", description="Expected result is blank in the source.", source_refs=[result_ref])]
                            if not input_step.expected_result.strip()
                            else []
                        ),
                    )
                )
            for key, value in (input_step.model_extra or {}).items():
                pointer = f"{base}/{_pointer_part(key)}"
                value_text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, sort_keys=True)
                add_segment(pointer, value_text, mapped=False)
    elif authored.procedure is not None:
        procedure_ref = add_segment("/procedure", authored.procedure, mapped=True)
        steps.append(
            ProcedureStep(
                sequence=1,
                original_text=authored.procedure,
                source_refs=[procedure_ref],
                ambiguities=(
                    [Ambiguity(code="blank_procedure", description="Procedure is blank in the source.", source_refs=[procedure_ref])]
                    if not authored.procedure.strip()
                    else []
                ),
            )
        )

    if authored.expected_result is not None:
        result_ref = add_segment("/expected_result", authored.expected_result, mapped=True)
        expected.append(
            ExpectedResultCheckpoint(
                sequence=len(expected) + 1,
                original_text=authored.expected_result,
                source_refs=[result_ref],
                ambiguities=(
                    [Ambiguity(code="blank_expected_result", description="Expected result is blank in the source.", source_refs=[result_ref])]
                    if not authored.expected_result.strip()
                    else []
                ),
            )
        )

    for key, value in (authored.model_extra or {}).items():
        if key in known_top:
            continue
        pointer = f"/{_pointer_part(key)}"
        value_text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, sort_keys=True)
        add_segment(pointer, value_text, mapped=False)

    if authored.test_case_id is None:
        case_ambiguities.append(
            Ambiguity(
                code="missing_test_case_identifier",
                description="No source-stated test-case identifier was supplied.",
            )
        )
    case = TestCase(
        internal_id=_stable_id("case", f"{document_id}:/test_case_id"),
        stated_identifier=authored.test_case_id,
        title_original=authored.title,
        steps=steps,
        expected_results=expected,
        source_refs=case_ref + title_ref + [ref for step in steps for ref in step.source_refs],
        ambiguities=case_ambiguities,
        interpretation_status="uninterpreted" if steps and expected else "needs_review",
    )
    test_set = TestSet(
        internal_id=_stable_id("set", f"{document_id}:/test_set_id"),
        stated_identifier=authored.test_set_id,
        title_original=authored.test_set_title,
        test_cases=[case],
        source_refs=set_ref,
    )

    provenance_warnings = []
    if hash_basis == "canonical_json_serialization":
        provenance_warnings.append(
            "Mapping input was hashed as deterministic canonical JSON; original JSON bytes were not provided."
        )
    document = ProtocolDocument(
        document_id=document_id,
        original_filename=original_filename,
        media_type="application/json" if original_filename.endswith(".json") else "text/plain",
        source_sha256=source_hash,
        hash_basis=hash_basis,
        source_bytes=raw_bytes if raw_bytes is not None else serialized,
        source_segments=segments,
        provenance=ExtractionProvenance(
            parser_name="authored-input-adapter",
            parser_version="1.0.0",
            method="structured_fields_without_semantic_interpretation",
            warnings=provenance_warnings,
        ),
    )
    protocol = CanonicalProtocol(
        document=document,
        test_sets=[test_set],
        unmapped_content=unmapped,
    )
    return IngestionResult(protocol=protocol, quality_report=evaluate_quality(protocol))

