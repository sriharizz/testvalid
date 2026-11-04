from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)


class SourceRef(StrictModel):
    document_id: str
    part: Literal[
        "filename",
        "document_property",
        "body_paragraph",
        "table_cell_paragraph",
        "header_paragraph",
        "header_table_cell_paragraph",
        "footer_paragraph",
        "footer_table_cell_paragraph",
        "unsupported_structure",
        "authored_json",
        "unknown",
    ]
    order_index: int = Field(ge=0)
    paragraph_index: int | None = Field(default=None, ge=0)
    table_index: int | None = Field(default=None, ge=0)
    row_index: int | None = Field(default=None, ge=0)
    cell_index: int | None = Field(default=None, ge=0)
    section_index: int | None = Field(default=None, ge=0)
    nested_table_path: tuple[int, ...] = ()
    json_pointer: str | None = None
    xml_path: str | None = None
    paragraph_style: str | None = None
    numbering_id: int | None = None
    numbering_level: int | None = None
    grid_span: int | None = None
    vertical_merge: str | None = None


class ExtractionProvenance(StrictModel):
    parser_name: str
    parser_version: str
    method: str
    warnings: list[str] = Field(default_factory=list)


class SourceSegment(StrictModel):
    segment_id: str
    text: str
    kind: Literal[
        "paragraph",
        "table_cell_paragraph",
        "unsupported_structure",
        "authored_text",
        "authored_unknown",
        "document_metadata",
    ]
    order_index: int = Field(ge=0)
    source_ref: SourceRef
    mapping_status: Literal["unmapped", "mapped", "metadata", "unsupported"] = "unmapped"
    warnings: list[str] = Field(default_factory=list)


class ProtocolDocument(StrictModel):
    document_id: str
    original_filename: str
    media_type: str
    source_sha256: str
    hash_basis: Literal["provided_bytes", "canonical_json_serialization"]
    source_bytes: bytes | None = Field(default=None, exclude=True, repr=False)
    protocol_identifier_as_stated: str | None = None
    protocol_version_as_stated: str | None = None
    source_segments: list[SourceSegment] = Field(default_factory=list)
    provenance: ExtractionProvenance


class DocumentIdentityCandidate(StrictModel):
    identity_type: Literal["protocol_identifier", "protocol_version"]
    raw_value: str
    normalized_value: str
    source_ref: SourceRef


class IdentityConflict(StrictModel):
    identity_type: Literal["protocol_identifier", "protocol_version"]
    candidates: list[DocumentIdentityCandidate]
    description: str


class Ambiguity(StrictModel):
    code: str
    description: str
    source_refs: list[SourceRef] = Field(default_factory=list)
    resolution_status: Literal["unresolved", "resolved_by_reviewer"] = "unresolved"


class DerivedInterpretation(StrictModel):
    """A proposal stored apart from source text and never executable by itself."""

    interpretation_id: str
    target_entity_type: Literal[
        "protocol", "test_set", "test_case", "procedure_step", "expected_result"
    ]
    target_internal_id: str
    proposed_value: Any
    source_refs: list[SourceRef] = Field(default_factory=list)
    status: Literal["proposed", "needs_review", "approved", "rejected"] = "proposed"
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    method: str


class UnmappedContent(StrictModel):
    segment_id: str
    original_text: str
    source_ref: SourceRef
    reason: str


class ExpectedResultCheckpoint(StrictModel):
    sequence: int = Field(ge=1)
    original_text: str
    source_refs: list[SourceRef] = Field(default_factory=list)
    ambiguities: list[Ambiguity] = Field(default_factory=list)


class ProcedureStep(StrictModel):
    sequence: int = Field(ge=1)
    stated_identifier: str | None = None
    original_text: str
    source_refs: list[SourceRef] = Field(default_factory=list)
    ambiguities: list[Ambiguity] = Field(default_factory=list)


class TestCase(StrictModel):
    internal_id: str
    stated_identifier: str | None = None
    title_original: str | None = None
    steps: list[ProcedureStep] = Field(default_factory=list)
    expected_results: list[ExpectedResultCheckpoint] = Field(default_factory=list)
    source_refs: list[SourceRef] = Field(default_factory=list)
    ambiguities: list[Ambiguity] = Field(default_factory=list)
    interpretation_status: Literal["uninterpreted", "needs_review"] = "uninterpreted"


class TestSet(StrictModel):
    internal_id: str
    stated_identifier: str | None = None
    title_original: str | None = None
    test_cases: list[TestCase] = Field(default_factory=list)
    source_refs: list[SourceRef] = Field(default_factory=list)
    ambiguities: list[Ambiguity] = Field(default_factory=list)


class CanonicalProtocol(StrictModel):
    document: ProtocolDocument
    test_sets: list[TestSet] = Field(default_factory=list)
    identity_candidates: list[DocumentIdentityCandidate] = Field(default_factory=list)
    identity_conflicts: list[IdentityConflict] = Field(default_factory=list)
    unmapped_content: list[UnmappedContent] = Field(default_factory=list)
    interpretations: list[DerivedInterpretation] = Field(default_factory=list)


class QualityIssue(StrictModel):
    code: str
    severity: Literal["warning", "needs_review", "blocked"]
    description: str
    source_refs: list[SourceRef] = Field(default_factory=list)


class IngestionQualityReport(StrictModel):
    status: Literal["PASS", "NEEDS_REVIEW", "BLOCKED"]
    source_segment_count: int = Field(ge=0)
    mapped_segment_count: int = Field(ge=0)
    unmapped_segment_count: int = Field(ge=0)
    test_set_count: int = Field(ge=0)
    test_case_count: int = Field(ge=0)
    issues: list[QualityIssue] = Field(default_factory=list)


class IngestionResult(StrictModel):
    protocol: CanonicalProtocol
    quality_report: IngestionQualityReport
