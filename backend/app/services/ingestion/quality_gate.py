from __future__ import annotations

import re
from hashlib import sha256

from backend.app.domain.protocol import (
    CanonicalProtocol,
    IngestionQualityReport,
    QualityIssue,
)


_SHA256_RE = re.compile(r"^[0-9a-f]{64}$", re.IGNORECASE)
_DOCX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def evaluate_quality(protocol: CanonicalProtocol) -> IngestionQualityReport:
    """Check extraction integrity and review gaps; never infer missing content."""
    issues: list[QualityIssue] = []
    document = protocol.document
    if not _SHA256_RE.fullmatch(document.source_sha256):
        issues.append(
            QualityIssue(
                code="invalid_source_hash",
                severity="blocked",
                description="Source SHA-256 is absent or malformed.",
            )
        )
    if (
        document.source_bytes is not None
        and sha256(document.source_bytes).hexdigest() != document.source_sha256
    ):
        issues.append(
            QualityIssue(
                code="source_hash_mismatch",
                severity="blocked",
                description="Retained source bytes do not match the recorded SHA-256.",
            )
        )
    if not document.provenance.parser_name or not document.provenance.parser_version:
        issues.append(
            QualityIssue(
                code="missing_extraction_provenance",
                severity="blocked",
                description="Parser name and version are required for reviewable ingestion.",
            )
        )
    for conflict in protocol.identity_conflicts:
        issues.append(
            QualityIssue(
                code="document_identity_conflict",
                severity="blocked",
                description=conflict.description,
                source_refs=[candidate.source_ref for candidate in conflict.candidates],
            )
        )
    if (
        document.media_type == _DOCX_MEDIA_TYPE
        and document.protocol_identifier_as_stated is None
        and not protocol.identity_conflicts
    ):
        issues.append(
            QualityIssue(
                code="missing_protocol_identifier",
                severity="needs_review",
                description="No protocol identifier could be established from source-labeled content; none was inferred.",
            )
        )

    cases = [case for test_set in protocol.test_sets for case in test_set.test_cases]
    if not protocol.test_sets:
        issues.append(
            QualityIssue(
                code="no_test_sets_mapped",
                severity="needs_review",
                description="No explicit test-set structure was mapped; source content remains available for review.",
            )
        )
    for test_set in protocol.test_sets:
        for ambiguity in test_set.ambiguities:
            issues.append(
                QualityIssue(
                    code=ambiguity.code,
                    severity="needs_review",
                    description=ambiguity.description,
                    source_refs=ambiguity.source_refs,
                )
            )
    for case in cases:
        if not case.stated_identifier:
            issues.append(
                QualityIssue(
                    code="missing_test_case_identifier",
                    severity="needs_review",
                    description="The source did not provide an unambiguous test-case identifier.",
                    source_refs=case.source_refs,
                )
            )
        if not case.steps or not any(step.original_text.strip() for step in case.steps):
            issues.append(
                QualityIssue(
                    code="missing_procedure",
                    severity="needs_review",
                    description="No non-empty procedure text was mapped; no instruction was invented.",
                    source_refs=case.source_refs,
                )
            )
        if not case.expected_results or not any(
            checkpoint.original_text.strip() for checkpoint in case.expected_results
        ):
            issues.append(
                QualityIssue(
                    code="missing_expected_result",
                    severity="needs_review",
                    description="No non-empty expected result was mapped; no acceptance criterion was invented.",
                    source_refs=case.source_refs,
                )
            )
        for ambiguity in case.ambiguities:
            issues.append(
                QualityIssue(
                    code=ambiguity.code,
                    severity="needs_review",
                    description=ambiguity.description,
                    source_refs=ambiguity.source_refs,
                )
            )
        for step in case.steps:
            for ambiguity in step.ambiguities:
                issues.append(
                    QualityIssue(
                        code=ambiguity.code,
                        severity="needs_review",
                        description=ambiguity.description,
                        source_refs=ambiguity.source_refs,
                    )
                )
        for checkpoint in case.expected_results:
            for ambiguity in checkpoint.ambiguities:
                issues.append(
                    QualityIssue(
                        code=ambiguity.code,
                        severity="needs_review",
                        description=ambiguity.description,
                        source_refs=ambiguity.source_refs,
                    )
                )

    for item in protocol.unmapped_content:
        issues.append(
            QualityIssue(
                code="unmapped_source_content",
                severity="needs_review",
                description="Source content is preserved but not mapped to a canonical test field.",
                source_refs=[item.source_ref],
            )
        )

    severity_order = {"warning": 0, "needs_review": 1, "blocked": 2}
    if any(issue.severity == "blocked" for issue in issues):
        status = "BLOCKED"
    elif any(issue.severity == "needs_review" for issue in issues):
        status = "NEEDS_REVIEW"
    else:
        status = "PASS"

    segments = document.source_segments
    return IngestionQualityReport(
        status=status,
        source_segment_count=len(segments),
        mapped_segment_count=sum(segment.mapping_status == "mapped" for segment in segments),
        unmapped_segment_count=sum(
            segment.mapping_status in {"unmapped", "unsupported"} for segment in segments
        ),
        test_set_count=len(protocol.test_sets),
        test_case_count=len(cases),
        issues=sorted(issues, key=lambda item: (-severity_order[item.severity], item.code)),
    )
