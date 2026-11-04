from __future__ import annotations

import json
from hashlib import sha256

from backend.app.services.ingestion.author_input_adapter import adapt_authored_test_case


def test_authored_input_preserves_exact_text_order_and_json_source() -> None:
    raw = (
        b'{"test_case_id":"TC-7","title":"Case title",'
        b'"steps":[{"step_id":"S-2","procedure":"  Do this\\nthen that  ",'
        b'"expected_result":"Exact result"},{"procedure":"Second step",'
        b'"expected_result":"Second result"}]}'
    )

    result = adapt_authored_test_case(raw)
    case = result.protocol.test_sets[0].test_cases[0]

    assert result.protocol.document.source_bytes == raw
    assert result.protocol.document.source_sha256 == sha256(raw).hexdigest()
    assert case.stated_identifier == "TC-7"
    assert [step.sequence for step in case.steps] == [1, 2]
    assert case.steps[0].stated_identifier == "S-2"
    assert case.steps[0].original_text == "  Do this\nthen that  "
    assert [checkpoint.original_text for checkpoint in case.expected_results] == [
        "Exact result",
        "Second result",
    ]
    assert case.steps[0].source_refs[1].json_pointer == "/steps/0/procedure"


def test_unknown_authored_fields_are_preserved_as_unmapped_content() -> None:
    payload = {
        "test_case_id": "TC-8",
        "procedure": "Keep this",
        "expected_result": "Keep that",
        "review_note": "Unclassified authored content",
    }

    result = adapt_authored_test_case(payload)

    assert any(
        "Unclassified authored content" in item.original_text
        for item in result.protocol.unmapped_content
    )
    assert any(item.source_ref.json_pointer == "/review_note" for item in result.protocol.unmapped_content)


def test_missing_instruction_is_flagged_without_invention() -> None:
    result = adapt_authored_test_case(
        {"test_case_id": "TC-9", "title": "No procedure or expected result"}
    )
    case = result.protocol.test_sets[0].test_cases[0]

    assert case.steps == []
    assert case.expected_results == []
    assert case.interpretation_status == "needs_review"
    assert "missing_procedure" in {issue.code for issue in result.quality_report.issues}
    assert "missing_expected_result" in {issue.code for issue in result.quality_report.issues}


def test_mapping_input_has_reproducible_hash_basis() -> None:
    payload = {"procedure": "Do one thing", "expected_result": "Observe one result"}
    result = adapt_authored_test_case(payload)

    expected = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    assert result.protocol.document.source_sha256 == sha256(expected).hexdigest()
    assert result.protocol.document.hash_basis == "canonical_json_serialization"
    assert result.protocol.document.provenance.warnings


def test_plain_english_string_is_kept_verbatim_and_not_completed_by_inference() -> None:
    original = "  Use the configured record and continue.  "

    result = adapt_authored_test_case(original)
    case = result.protocol.test_sets[0].test_cases[0]

    assert case.steps[0].original_text == original
    assert case.expected_results == []
    assert "missing_expected_result" in {issue.code for issue in result.quality_report.issues}


def test_authored_unfamiliar_directives_repetition_and_conflicting_expectations_are_lossless() -> None:
    raw = (
        b'{ "test_case_id": "CASE-2046-X", "steps": ['
        b'{"procedure":"Use the unusual phrase:\\u00a0keep every symbol?!",'
        b'"expected_result":"The first outcome is observed."},'
        b'{"procedure":"Use the unusual phrase:\\\\u00a0keep every symbol?!",'
        b'"expected_result":"The second, conflicting outcome is observed."}],'
        b'"section_directive":"Continue from the source-defined section, preserving context.",'
        b'"additional_note":"Repeat exactly; do not drop this note." }'
    )

    result = adapt_authored_test_case(raw)
    case = result.protocol.test_sets[0].test_cases[0]
    segment_ids = {segment.segment_id for segment in result.protocol.document.source_segments}
    accounted_ids = {
        segment.segment_id
        for segment in result.protocol.document.source_segments
        if segment.mapping_status in {"mapped", "metadata"}
    }
    accounted_ids.update(item.segment_id for item in result.protocol.unmapped_content)

    assert result.protocol.document.source_bytes == raw
    assert [step.original_text for step in case.steps] == [
        "Use the unusual phrase:\u00a0keep every symbol?!",
        "Use the unusual phrase:\\u00a0keep every symbol?!",
    ]
    assert [item.original_text for item in case.expected_results] == [
        "The first outcome is observed.",
        "The second, conflicting outcome is observed.",
    ]
    assert "/section_directive" in {item.source_ref.json_pointer for item in result.protocol.unmapped_content}
    assert "/additional_note" in {item.source_ref.json_pointer for item in result.protocol.unmapped_content}
    assert segment_ids == accounted_ids
