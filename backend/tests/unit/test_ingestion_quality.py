from __future__ import annotations

from backend.app.domain.protocol import DocumentIdentityCandidate, IdentityConflict
from backend.app.services.ingestion.author_input_adapter import adapt_authored_test_case
from backend.app.services.ingestion.quality_gate import evaluate_quality


def test_missing_source_mapping_and_expectation_require_review() -> None:
    result = adapt_authored_test_case(
        {"test_case_id": "TC-10", "procedure": "Keep this", "expected_result": ""}
    )
    report = evaluate_quality(result.protocol)

    assert report.status == "NEEDS_REVIEW"
    assert "missing_expected_result" in {issue.code for issue in report.issues}
    assert report.unmapped_segment_count >= 0


def test_document_identity_conflict_blocks_quality_gate() -> None:
    result = adapt_authored_test_case(
        {"test_case_id": "TC-11", "procedure": "Do one", "expected_result": "See one"}
    )
    result.protocol.identity_conflicts.append(
        IdentityConflict(
            identity_type="protocol_identifier",
            candidates=[
                DocumentIdentityCandidate(
                    identity_type="protocol_identifier",
                    raw_value=value,
                    normalized_value=value.casefold(),
                    source_ref=result.protocol.document.source_segments[0].source_ref,
                )
                for value in ("DOC-OLD", "DOC-NEW")
            ],
            description="Conflicting identities remain unresolved.",
        )
    )

    report = evaluate_quality(result.protocol)

    assert report.status == "BLOCKED"
