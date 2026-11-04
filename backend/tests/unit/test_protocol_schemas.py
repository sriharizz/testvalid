from __future__ import annotations

import pytest
from pydantic import ValidationError

from backend.app.domain.protocol import (
    Ambiguity,
    CanonicalProtocol,
    DocumentIdentityCandidate,
    DerivedInterpretation,
    ExpectedResultCheckpoint,
    ExtractionProvenance,
    IdentityConflict,
    ProcedureStep,
    ProtocolDocument,
    SourceRef,
    SourceSegment,
    TestCase as CanonicalTestCase,
    TestSet as CanonicalTestSet,
)


def _ref(document_id: str = "doc-1") -> SourceRef:
    return SourceRef(document_id=document_id, part="authored_json", order_index=0)


def test_canonical_case_keeps_source_identity_order_and_ambiguity() -> None:
    ref = _ref()
    case = CanonicalTestCase(
        internal_id="case-1",
        stated_identifier="TC 01",
        title_original="Exact title",
        steps=[
            ProcedureStep(
                sequence=1,
                stated_identifier="step B",
                original_text="  Original instruction\nsecond line  ",
                source_refs=[ref],
                ambiguities=[
                    Ambiguity(code="unclear_target", description="Target is unspecified")
                ],
            ),
            ProcedureStep(sequence=2, original_text="Next instruction", source_refs=[ref]),
        ],
        expected_results=[
            ExpectedResultCheckpoint(
                sequence=1,
                original_text="Expected state exactly",
                source_refs=[ref],
            )
        ],
        source_refs=[ref],
        ambiguities=[
            Ambiguity(code="unresolved", description="Kept for reviewer resolution")
        ],
    )

    assert [step.sequence for step in case.steps] == [1, 2]
    assert case.steps[0].original_text == "  Original instruction\nsecond line  "
    assert case.expected_results[0].original_text == "Expected state exactly"
    assert case.ambiguities[0].resolution_status == "unresolved"
    assert "actions" not in CanonicalTestCase.model_fields


def test_document_retains_original_bytes_and_source_segments() -> None:
    raw = b"authored source bytes\x00"
    document = ProtocolDocument(
        document_id="doc-1",
        original_filename="authoring.json",
        source_sha256="a" * 64,
        hash_basis="provided_bytes",
        media_type="application/json",
        source_bytes=raw,
        provenance=ExtractionProvenance(parser_name="test", parser_version="1", method="test"),
        source_segments=[
            SourceSegment(
                segment_id="segment-1",
                text="unaltered text ",
                kind="authored_text",
                order_index=0,
                source_ref=_ref(),
            )
        ],
    )

    assert document.source_bytes == raw
    assert document.source_segments[0].text == "unaltered text "
    assert "source_bytes" not in document.model_dump()


def test_unknown_schema_fields_are_rejected() -> None:
    with pytest.raises(ValidationError):
        SourceSegment(
            segment_id="segment-1",
            text="x",
            kind="authored_text",
            order_index=0,
            source_ref=_ref(),
            executable_action="click",
        )


def test_canonical_protocol_links_document_and_distinct_test_sets() -> None:
    ref = _ref()
    document = ProtocolDocument(
        document_id="doc-1",
        original_filename="source.docx",
        source_sha256="b" * 64,
        hash_basis="provided_bytes",
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        provenance=ExtractionProvenance(parser_name="test", parser_version="1", method="test"),
    )
    protocol = CanonicalProtocol(
        document=document,
        test_sets=[
            CanonicalTestSet(internal_id="set-a", stated_identifier="A", title_original="Group A", source_refs=[ref]),
            CanonicalTestSet(internal_id="set-b", stated_identifier="B", title_original="Group B", source_refs=[ref]),
        ],
    )

    assert [test_set.stated_identifier for test_set in protocol.test_sets] == ["A", "B"]


def test_derived_interpretation_is_separate_source_referenced_and_reviewable() -> None:
    interpretation = DerivedInterpretation(
        interpretation_id="interpretation-1",
        target_entity_type="procedure_step",
        target_internal_id="step-1",
        proposed_value={"intent": "navigate"},
        source_refs=[_ref()],
        status="needs_review",
        confidence=0.61,
        method="human-reviewed structural proposal",
    )

    assert interpretation.status == "needs_review"
    assert interpretation.source_refs[0].document_id == "doc-1"
    assert interpretation.proposed_value == {"intent": "navigate"}
