from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from hashlib import sha256
from io import BytesIO
from pathlib import Path
from typing import Any

import docx
from docx.oxml.ns import qn
from docx.table import Table, _Cell
from docx.text.paragraph import Paragraph

from backend.app.domain.protocol import (
    Ambiguity,
    CanonicalProtocol,
    DocumentIdentityCandidate,
    ExpectedResultCheckpoint,
    ExtractionProvenance,
    IdentityConflict,
    IngestionResult,
    ProcedureStep,
    ProtocolDocument,
    SourceRef,
    SourceSegment,
    TestCase,
    TestSet,
    UnmappedContent,
)
from backend.app.services.ingestion.quality_gate import evaluate_quality
from backend.app.services.ingestion.field_labels import build_field_label_map, normalize_field_label


_IDENTIFIER_RE = re.compile(
    r"(?<![A-Z0-9])[A-Z0-9]+(?:[-./][A-Z0-9]+){2,}(?![A-Z0-9])",
    re.IGNORECASE,
)
_IDENTITY_LABEL_RE = re.compile(
    r"\b(?:protocol|document)\s*(?:id|no\.?|number|identifier)\s*[:#]?\s*([A-Z0-9][A-Z0-9._/-]*)",
    re.IGNORECASE,
)
_PROTOCOL_VERSION_RE = re.compile(
    r"\b(?:protocol|document)\s*(?:version|ver)\s*[:#]?\s*([0-9]+(?:\.[0-9]+){0,3})\b",
    re.IGNORECASE,
)
_BARE_VERSION_RE = re.compile(r"\bV(?:ersion)?\s*[:.]?\s*([0-9]+(?:\.[0-9]+){0,3})\b", re.IGNORECASE)
_TEST_SET_RE = re.compile(
    r"^\s*test\s*(?:set|suite|group)\s*#?\s+([A-Z0-9]+(?:[._-][A-Z0-9]+)*)\s*(?:[:\-–—]\s*(.*?))?\s*$",
    re.IGNORECASE,
)
@dataclass
class _CellRecord:
    text: str
    refs: list[SourceRef] = field(default_factory=list)
    segment_ids: list[str] = field(default_factory=list)


@dataclass
class _RowRecord:
    cells: list[_CellRecord]


@dataclass
class _TableRecord:
    table_index: int
    part: str
    rows: list[_RowRecord]
    nested_table_path: tuple[int, ...]


class _Extractor:
    def __init__(
        self,
        document: Any,
        raw_bytes: bytes,
        filename: str,
        label_aliases: Mapping[str, Iterable[str]] | None = None,
    ) -> None:
        self.document = document
        self.raw_bytes = raw_bytes
        self.filename = filename
        self.source_hash = sha256(raw_bytes).hexdigest()
        self.document_id = f"doc-{self.source_hash[:16]}"
        self.segments: list[SourceSegment] = []
        self.tables: list[_TableRecord] = []
        self.order = 0
        self.field_labels = build_field_label_map(label_aliases)

    def _add_segment(
        self,
        text: str,
        kind: str,
        ref: SourceRef,
        *,
        warning: str | None = None,
    ) -> SourceSegment:
        segment_key = f"{self.document_id}:{ref.model_dump_json()}:{self.order}"
        segment_id = f"seg-{sha256(segment_key.encode('utf-8')).hexdigest()[:16]}"
        segment = SourceSegment(
            segment_id=segment_id,
            text=text,
            kind=kind,
            order_index=self.order,
            source_ref=ref,
            mapping_status="unsupported" if warning else "unmapped",
            warnings=[warning] if warning else [],
        )
        self.segments.append(segment)
        self.order += 1
        return segment

    @staticmethod
    def _numbering(paragraph: Paragraph) -> tuple[int | None, int | None]:
        properties = paragraph._p.pPr
        numbering = getattr(properties, "numPr", None) if properties is not None else None
        if numbering is None:
            return None, None
        num_id = getattr(getattr(numbering, "numId", None), "val", None)
        level = getattr(getattr(numbering, "ilvl", None), "val", None)
        return num_id, level

    def _extract_paragraph(
        self,
        element: Any,
        parent: Any,
        *,
        part: str,
        paragraph_index: int,
        table_index: int | None = None,
        row_index: int | None = None,
        cell_index: int | None = None,
        section_index: int | None = None,
        nested_table_path: tuple[int, ...] = (),
        grid_span: int | None = None,
        vertical_merge: str | None = None,
    ) -> SourceSegment:
        paragraph = Paragraph(element, parent)
        numbering_id, numbering_level = self._numbering(paragraph)
        source_ref = SourceRef(
            document_id=self.document_id,
            part=part,
            order_index=self.order,
            paragraph_index=paragraph_index,
            table_index=table_index,
            row_index=row_index,
            cell_index=cell_index,
            section_index=section_index,
            nested_table_path=nested_table_path,
            paragraph_style=paragraph.style.name if paragraph.style is not None else None,
            numbering_id=numbering_id,
            numbering_level=numbering_level,
            grid_span=grid_span,
            vertical_merge=vertical_merge,
            xml_path=(
                f"{part}/table[{table_index}]/row[{row_index}]/cell[{cell_index}]/paragraph[{paragraph_index}]"
                if table_index is not None
                else f"{part}/paragraph[{paragraph_index}]"
            ),
        )
        kind = "table_cell_paragraph" if "table_cell" in part else "paragraph"
        return self._add_segment(paragraph.text, kind, source_ref)

    def _extract_table(
        self,
        table_element: Any,
        parent: Any,
        *,
        part: str,
        section_index: int | None = None,
        nested_table_path: tuple[int, ...] = (),
    ) -> None:
        table_index = len(self.tables)
        table = Table(table_element, parent)
        table_record = _TableRecord(table_index, part, [], nested_table_path)
        self.tables.append(table_record)

        for row_index, row_element in enumerate(table._tbl.tr_lst):
            row_record = _RowRecord([])
            table_record.rows.append(row_record)
            for cell_index, cell_element in enumerate(row_element.tc_lst):
                cell_wrapper = _Cell(cell_element, table)
                tc_properties = getattr(cell_element, "tcPr", None)
                grid_span = getattr(getattr(tc_properties, "gridSpan", None), "val", None)
                merge_node = getattr(tc_properties, "vMerge", None)
                vertical_merge = None
                if merge_node is not None:
                    vertical_merge = getattr(merge_node, "val", None) or "continue"
                cell_segments: list[SourceSegment] = []
                paragraph_index = 0
                nested_index = 0
                cell_part = {
                    "body_paragraph": "table_cell_paragraph",
                    "header_paragraph": "header_table_cell_paragraph",
                    "footer_paragraph": "footer_table_cell_paragraph",
                }[part]
                for child in cell_element.iterchildren():
                    if child.tag == qn("w:p"):
                        cell_segments.append(
                            self._extract_paragraph(
                                child,
                                cell_wrapper,
                                part=cell_part,
                                paragraph_index=paragraph_index,
                                table_index=table_index,
                                row_index=row_index,
                                cell_index=cell_index,
                                section_index=section_index,
                                nested_table_path=nested_table_path,
                                grid_span=int(grid_span) if grid_span is not None else None,
                                vertical_merge=vertical_merge,
                            )
                        )
                        paragraph_index += 1
                    elif child.tag == qn("w:tbl"):
                        self._extract_table(
                            child,
                            cell_wrapper,
                            part=part,
                            section_index=section_index,
                            nested_table_path=nested_table_path + (table_index, nested_index),
                        )
                        nested_index += 1
                if not cell_segments:
                    ref = SourceRef(
                        document_id=self.document_id,
                        part=cell_part,
                        order_index=self.order,
                        table_index=table_index,
                        row_index=row_index,
                        cell_index=cell_index,
                        section_index=section_index,
                        nested_table_path=nested_table_path,
                        grid_span=int(grid_span) if grid_span is not None else None,
                        vertical_merge=vertical_merge,
                        xml_path=f"{part}/table[{table_index}]/row[{row_index}]/cell[{cell_index}]",
                    )
                    cell_segments.append(self._add_segment("", "table_cell_paragraph", ref))
                row_record.cells.append(
                    _CellRecord(
                        text="\n".join(segment.text for segment in cell_segments),
                        refs=[segment.source_ref for segment in cell_segments],
                        segment_ids=[segment.segment_id for segment in cell_segments],
                    )
                )

    def _extract_container(self, container: Any, part: str, section_index: int | None = None) -> None:
        paragraph_index = 0
        for child in container._element.iterchildren():
            if child.tag == qn("w:p"):
                self._extract_paragraph(
                    child,
                    container,
                    part=part,
                    paragraph_index=paragraph_index,
                    section_index=section_index,
                )
                paragraph_index += 1
            elif child.tag == qn("w:tbl"):
                self._extract_table(
                    child,
                    container,
                    part=part,
                    section_index=section_index,
                )

    def _extract_source(self) -> None:
        filename_ref = SourceRef(
            document_id=self.document_id,
            part="filename",
            order_index=self.order,
            xml_path="original_filename",
        )
        filename_segment = self._add_segment(
            self.filename, "document_metadata", filename_ref
        )
        filename_segment.mapping_status = "metadata"
        self._extract_container(self.document._body, "body_paragraph")
        for section_index, section in enumerate(self.document.sections):
            self._extract_container(section.header, "header_paragraph", section_index)
            self._extract_container(section.footer, "footer_paragraph", section_index)
        self._extract_unsupported_structures()

    def _extract_unsupported_structures(self) -> None:
        textbox_tag = qn("w:txbxContent")
        for index, element in enumerate(self.document.element.iter(textbox_tag)):
            text = "".join(node.text or "" for node in element.iter(qn("w:t")))
            ref = SourceRef(
                document_id=self.document_id,
                part="unsupported_structure",
                order_index=self.order,
                xml_path=f"document/txbxContent[{index}]",
            )
            self._add_segment(
                text,
                "unsupported_structure",
                ref,
                warning="Text-box content was retained but needs explicit review for canonical mapping.",
            )
        alt_chunk_tag = qn("w:altChunk")
        for index, _element in enumerate(self.document.element.iter(alt_chunk_tag)):
            ref = SourceRef(
                document_id=self.document_id,
                part="unsupported_structure",
                order_index=self.order,
                xml_path=f"document/altChunk[{index}]",
            )
            self._add_segment(
                "",
                "unsupported_structure",
                ref,
                warning="External altChunk content cannot be read by python-docx and requires review.",
            )

    def _table_header(self, table: _TableRecord) -> tuple[int, dict[str, int], str] | None:
        for row_index, row in enumerate(table.rows):
            columns: dict[str, int] = {}
            for cell_index, cell in enumerate(row.cells):
                label, _inline_value = self._split_label_value(cell.text)
                field = self.field_labels.get(normalize_field_label(label or cell.text))
                if field in {"case_id", "title", "procedure", "expected", "step_id"}:
                    columns[field] = cell_index
            if {"case_id", "procedure", "expected"}.issubset(columns):
                return row_index, columns, "case_rows"
            if {"procedure", "expected"}.issubset(columns):
                has_case_metadata = any(
                    self._field_from_cell(meta_cell.text) in {"case_id", "title"}
                    for meta_row in table.rows[:row_index]
                    for meta_cell in meta_row.cells
                )
                if has_case_metadata:
                    return row_index, columns, "case_metadata_steps"
        return None

    @staticmethod
    def _split_label_value(text: str) -> tuple[str | None, str | None]:
        """Split only an explicit leading label delimiter; retain original segment elsewhere."""
        match = re.match(r"^\s*([^:\r\n]{1,100})\s*:\s*(.*)$", text, re.DOTALL)
        return (match.group(1), match.group(2)) if match else (None, None)

    def _field_from_cell(self, text: str) -> str | None:
        label, _value = self._split_label_value(text)
        return self.field_labels.get(normalize_field_label(label or text))

    @staticmethod
    def _identity_match_is_candidate(value: str) -> bool:
        parts = re.split(r"[-_./]", value)
        return len(parts) >= 3 and any(character.isdigit() for character in parts[-1])

    def _identity(self) -> tuple[list[DocumentIdentityCandidate], list[IdentityConflict], str | None, str | None]:
        candidates: list[DocumentIdentityCandidate] = []
        filename_ref = next(
            segment.source_ref for segment in self.segments
            if segment.source_ref.part == "filename"
        )
        for match in _IDENTIFIER_RE.finditer(Path(self.filename).stem):
            value = match.group(0)
            if self._identity_match_is_candidate(value):
                candidates.append(
                    DocumentIdentityCandidate(
                        identity_type="protocol_identifier",
                        raw_value=value,
                        normalized_value=value.casefold(),
                        source_ref=filename_ref,
                    )
                )
        for segment in self.segments:
            structural_identifier_matches: list[re.Match[str]] = []
            for match in _IDENTITY_LABEL_RE.finditer(segment.text):
                value = match.group(1).rstrip(".,;:")
                ref = segment.source_ref.model_copy(update={"order_index": segment.order_index})
                candidates.append(
                    DocumentIdentityCandidate(
                        identity_type="protocol_identifier",
                        raw_value=value,
                        normalized_value=value.casefold(),
                        source_ref=ref,
                    )
                )
            if segment.source_ref.part.startswith(("header_", "footer_")):
                for match in _IDENTIFIER_RE.finditer(segment.text):
                    value = match.group(0)
                    if self._identity_match_is_candidate(value):
                        structural_identifier_matches.append(match)
                        candidates.append(
                            DocumentIdentityCandidate(
                                identity_type="protocol_identifier",
                                raw_value=value,
                                normalized_value=value.casefold(),
                                source_ref=segment.source_ref.model_copy(
                                    update={"order_index": segment.order_index}
                                ),
                            )
                        )
            version_matches = list(_PROTOCOL_VERSION_RE.finditer(segment.text))
            if _IDENTITY_LABEL_RE.search(segment.text) or structural_identifier_matches:
                version_matches.extend(_BARE_VERSION_RE.finditer(segment.text))
            for match in version_matches:
                value = match.group(1)
                ref = segment.source_ref.model_copy(update={"order_index": segment.order_index})
                candidates.append(
                    DocumentIdentityCandidate(
                        identity_type="protocol_version",
                        raw_value=value,
                        normalized_value=value.casefold(),
                        source_ref=ref,
                    )
                )
        conflicts: list[IdentityConflict] = []
        for identity_type in ("protocol_identifier", "protocol_version"):
            values = [c for c in candidates if c.identity_type == identity_type]
            if len({candidate.normalized_value for candidate in values}) > 1:
                conflicts.append(
                    IdentityConflict(
                        identity_type=identity_type,
                        candidates=values,
                        description=(
                            f"Conflicting source-stated {identity_type.replace('_', ' ')} values were found; "
                            "no value was selected automatically."
                        ),
                    )
                )
        identifiers = {
            candidate.normalized_value: candidate.raw_value
            for candidate in candidates
            if candidate.identity_type == "protocol_identifier"
        }
        versions = {
            candidate.normalized_value: candidate.raw_value
            for candidate in candidates
            if candidate.identity_type == "protocol_version"
        }
        identifier = next(iter(identifiers.values())) if len(identifiers) == 1 else None
        version = next(iter(versions.values())) if len(versions) == 1 else None
        return candidates, conflicts, identifier, version

    def _set_heading_for_table(self, table: _TableRecord) -> tuple[str | None, str | None, SourceRef | None]:
        first_order = min(
            (ref.order_index for row in table.rows for cell in row.cells for ref in cell.refs),
            default=self.order,
        )
        headings: list[tuple[int, re.Match[str], SourceRef]] = []
        for segment in self.segments:
            if segment.source_ref.part != "body_paragraph" or segment.order_index >= first_order:
                continue
            match = self._test_set_heading_match(segment.text)
            if match:
                headings.append((segment.order_index, match, segment.source_ref))
        if not headings:
            return None, None, None
        _order, match, ref = headings[-1]
        return match.group(1), match.group(2) or None, ref

    def _test_set_heading_match(self, text: str) -> re.Match[str] | None:
        label, _value = self._split_label_value(text)
        if label and self.field_labels.get(normalize_field_label(label)) in {
            "test_set_id", "test_set_title"
        }:
            return None
        return _TEST_SET_RE.match(text)

    def _set_metadata_for_table(
        self, table: _TableRecord, header_row_index: int
    ) -> tuple[str | None, str | None, list[str]]:
        """Read explicitly labeled set metadata from any rows before the data header."""
        values: dict[str, str] = {}
        segment_ids: list[str] = []
        for row in table.rows[:header_row_index]:
            for cell_index, cell in enumerate(row.cells):
                label, inline_value = self._split_label_value(cell.text)
                field = self.field_labels.get(normalize_field_label(label or cell.text))
                if field not in {"test_set_id", "test_set_title"}:
                    continue
                value = inline_value
                if value is None and cell_index + 1 < len(row.cells):
                    value = row.cells[cell_index + 1].text
                    segment_ids.extend(row.cells[cell_index + 1].segment_ids)
                values[field] = value or ""
                segment_ids.extend(cell.segment_ids)
        return values.get("test_set_id") or None, values.get("test_set_title") or None, segment_ids

    def _map_test_cases(self) -> tuple[list[TestSet], list[UnmappedContent]]:
        segment_by_id = {segment.segment_id: segment for segment in self.segments}
        test_sets: list[TestSet] = []
        set_index: dict[str, TestSet] = {}
        unmapped: list[UnmappedContent] = []

        def get_set(stated_id: str | None, title: str | None, ref: SourceRef | None) -> TestSet:
            key = stated_id.casefold() if stated_id is not None else "__unclassified__"
            if key not in set_index:
                stable = sha256(f"{self.document_id}:test-set:{key}".encode()).hexdigest()[:16]
                test_set = TestSet(
                    internal_id=f"set-{stable}",
                    stated_identifier=stated_id,
                    title_original=title,
                    source_refs=[ref] if ref is not None else [],
                    ambiguities=(
                        [Ambiguity(code="missing_test_set_identity", description="No source-stated test-set identifier was found.")]
                        if stated_id is None
                        else []
                    ),
                )
                set_index[key] = test_set
                test_sets.append(test_set)
            elif ref is not None:
                set_index[key].source_refs.append(ref)
            return set_index[key]

        # Map only explicit field labels in body paragraphs. Other prose stays
        # source-backed and unmapped; no phrase or ambiguity keyword filtering.
        paragraph_set: TestSet | None = None
        paragraph_case: TestCase | None = None
        pending_step_id: str | None = None
        pending_set_id: str | None = None
        pending_set_title: str | None = None
        for segment in self.segments:
            if segment.source_ref.part != "body_paragraph":
                continue
            label, value = self._split_label_value(segment.text)
            field = self.field_labels.get(normalize_field_label(label)) if label else None
            set_heading = self._test_set_heading_match(segment.text)
            if set_heading:
                paragraph_set = get_set(
                    set_heading.group(1), set_heading.group(2) or None, segment.source_ref
                )
                pending_set_id = None
                pending_set_title = None
                segment.mapping_status = "metadata"
                continue
            if label is None:
                continue
            if field not in {"test_set_id", "test_set_title", "case_id", "title", "procedure", "expected", "step_id"}:
                continue
            value = value or ""
            if field in {"test_set_id", "test_set_title"}:
                if field == "test_set_id":
                    pending_set_id = value or None
                else:
                    pending_set_title = value or None
                segment.mapping_status = "metadata"
                continue
            if paragraph_case is None and field != "case_id":
                # An isolated label such as "Procedure:" in narrative prose is
                # not enough context to create a test case. Keep it unchanged
                # and unmapped until an explicit case identifier establishes
                # the paragraph-based case structure.
                continue
            if paragraph_set is None:
                paragraph_set = get_set(pending_set_id, pending_set_title, None)
            if field == "case_id":
                stable = sha256(
                    f"{self.document_id}:paragraph-case:{segment.order_index}:{value}".encode()
                ).hexdigest()[:16]
                paragraph_case = TestCase(
                    internal_id=f"case-{stable}",
                    stated_identifier=value or None,
                    source_refs=[segment.source_ref],
                    ambiguities=(
                        [Ambiguity(code="missing_test_case_identifier", description="The explicit case identifier field is blank.", source_refs=[segment.source_ref])]
                        if not value
                        else []
                    ),
                    interpretation_status="needs_review" if not value else "uninterpreted",
                )
                paragraph_set.test_cases.append(paragraph_case)
            else:
                if paragraph_case is None:
                    stable = sha256(
                        f"{self.document_id}:paragraph-case:{segment.order_index}:unidentified".encode()
                    ).hexdigest()[:16]
                    paragraph_case = TestCase(
                        internal_id=f"case-{stable}",
                        ambiguities=[Ambiguity(code="missing_test_case_identifier", description="No explicit case identifier precedes these labeled fields.", source_refs=[segment.source_ref])],
                        interpretation_status="needs_review",
                    )
                    paragraph_set.test_cases.append(paragraph_case)
                paragraph_case.source_refs.append(segment.source_ref)
                if field == "title":
                    paragraph_case.title_original = value or None
                elif field == "step_id":
                    pending_step_id = value or None
                elif field == "procedure":
                    paragraph_case.steps.append(
                        ProcedureStep(
                            sequence=len(paragraph_case.steps) + 1,
                            stated_identifier=pending_step_id,
                            original_text=value,
                            source_refs=[segment.source_ref],
                            ambiguities=(
                                [Ambiguity(code="blank_procedure", description="Explicit procedure field is blank.", source_refs=[segment.source_ref])]
                                if not value.strip()
                                else []
                            ),
                        )
                    )
                    pending_step_id = None
                elif field == "expected":
                    paragraph_case.expected_results.append(
                        ExpectedResultCheckpoint(
                            sequence=len(paragraph_case.expected_results) + 1,
                            original_text=value,
                            source_refs=[segment.source_ref],
                            ambiguities=(
                                [Ambiguity(code="blank_expected_result", description="Explicit expected-result field is blank.", source_refs=[segment.source_ref])]
                                if not value.strip()
                                else []
                            ),
                        )
                    )
            segment.mapping_status = "mapped"

        for table in self.tables:
            header = self._table_header(table)
            if header is None:
                continue
            header_row_index, columns, layout = header
            set_id, set_title, set_ref = self._set_heading_for_table(table)
            metadata_set_id, metadata_set_title, set_metadata_segment_ids = self._set_metadata_for_table(
                table, header_row_index
            )
            if set_id is None:
                set_id = metadata_set_id
            if set_title is None:
                set_title = metadata_set_title
            test_set = get_set(set_id, set_title, set_ref)
            for segment_id in set_metadata_segment_ids:
                segment_by_id[segment_id].mapping_status = "metadata"
            if layout == "case_metadata_steps":
                case, metadata_segment_ids = self._case_metadata(table, header_row_index)
                case_table_rows = table.rows[header_row_index]
                for segment_id in metadata_segment_ids:
                    segment_by_id[segment_id].mapping_status = "mapped"
                for cell in case_table_rows.cells:
                    for segment_id in cell.segment_ids:
                        segment_by_id[segment_id].mapping_status = "metadata"
                for row_index, row in enumerate(table.rows[header_row_index + 1 :], header_row_index + 1):
                    values = [cell.text for cell in row.cells]
                    if not any(value.strip() for value in values):
                        for cell in row.cells:
                            for segment_id in cell.segment_ids:
                                segment_by_id[segment_id].mapping_status = "metadata"
                        continue
                    row_refs = [ref for cell in row.cells for ref in cell.refs]
                    procedure_index = columns["procedure"]
                    expected_index = columns["expected"]
                    procedure_cell = row.cells[procedure_index] if procedure_index < len(row.cells) else _CellRecord("")
                    expected_cell = row.cells[expected_index] if expected_index < len(row.cells) else _CellRecord("")
                    step_id_index = columns.get("step_id")
                    step_id = values[step_id_index] if step_id_index is not None and step_id_index < len(values) else None
                    procedure = values[procedure_index] if procedure_index < len(values) else ""
                    expected = values[expected_index] if expected_index < len(values) else ""
                    case.steps.append(
                        ProcedureStep(
                            sequence=len(case.steps) + 1,
                            stated_identifier=step_id or None,
                            original_text=procedure,
                            source_refs=procedure_cell.refs,
                            ambiguities=(
                                [Ambiguity(code="blank_procedure", description="Procedure cell is blank in the source.", source_refs=procedure_cell.refs)]
                                if not procedure.strip()
                                else []
                            ),
                        )
                    )
                    case.expected_results.append(
                        ExpectedResultCheckpoint(
                            sequence=len(case.expected_results) + 1,
                            original_text=expected,
                            source_refs=expected_cell.refs,
                            ambiguities=(
                                [Ambiguity(code="blank_expected_result", description="Expected result cell is blank in the source.", source_refs=expected_cell.refs)]
                                if not expected.strip()
                                else []
                            ),
                        )
                    )
                    for column_name in ("procedure", "expected", "step_id"):
                        cell_index = columns.get(column_name)
                        if cell_index is not None and cell_index < len(row.cells):
                            for segment_id in row.cells[cell_index].segment_ids:
                                segment_by_id[segment_id].mapping_status = "mapped"
                    case.source_refs.extend(row_refs)
                if case.ambiguities or not case.steps:
                    case.interpretation_status = "needs_review"
                test_set.test_cases.append(case)
                continue

            for cell in table.rows[header_row_index].cells:
                for segment_id in cell.segment_ids:
                    segment_by_id[segment_id].mapping_status = "metadata"
            existing_cases = {
                case.stated_identifier.casefold(): case
                for case in test_set.test_cases
                if case.stated_identifier
            }
            current_case: TestCase | None = None
            metadata_case, metadata_segment_ids = self._case_metadata(table, header_row_index)
            for segment_id in metadata_segment_ids:
                segment_by_id[segment_id].mapping_status = "metadata"
            for row_index, row in enumerate(table.rows):
                if row_index <= header_row_index:
                    continue
                values = [cell.text for cell in row.cells]
                normalized_values = [" ".join(value.casefold().split()).strip(" :\t\r\n") for value in values]
                if normalized_values == [" ".join(row_cell.text.casefold().split()).strip(" :\t\r\n") for row_cell in table.rows[header_row_index].cells]:
                    for cell in row.cells:
                        for segment_id in cell.segment_ids:
                            segment_by_id[segment_id].mapping_status = "metadata"
                    continue
                case_index = columns["case_id"]
                raw_case_id = values[case_index] if case_index < len(values) else ""
                stated_case_id = raw_case_id if raw_case_id.strip() else None
                row_refs = [ref for cell in row.cells for ref in cell.refs]
                if not any(value.strip() for value in values):
                    for cell in row.cells:
                        for segment_id in cell.segment_ids:
                            segment_by_id[segment_id].mapping_status = "metadata"
                    continue
                if stated_case_id is None:
                    if current_case is None:
                        stable = sha256(f"{self.document_id}:table:{table.table_index}:row:{row_index}".encode()).hexdigest()[:16]
                        current_case = TestCase(
                            internal_id=f"case-{stable}",
                            ambiguities=[
                                Ambiguity(
                                    code="missing_test_case_identifier",
                                    description="A populated data row has no source-stated test-case identifier.",
                                    source_refs=row_refs,
                                )
                            ],
                            source_refs=row_refs,
                            interpretation_status="needs_review",
                        )
                        test_set.test_cases.append(current_case)
                    else:
                        current_case.ambiguities.append(
                            Ambiguity(
                                code="continuation_row_without_identifier",
                                description="A populated row without an identifier was retained as a continuation; grouping needs review.",
                                source_refs=row_refs,
                            )
                        )
                else:
                    key = stated_case_id.strip().casefold()
                    current_case = existing_cases.get(key)
                    if current_case is None:
                        stable = sha256(f"{self.document_id}:test-set:{set_id}:case:{key}".encode()).hexdigest()[:16]
                        current_case = TestCase(
                            internal_id=f"case-{stable}",
                            stated_identifier=stated_case_id,
                            source_refs=[],
                        )
                        test_set.test_cases.append(current_case)
                        existing_cases[key] = current_case
                assert current_case is not None
                current_case.source_refs.extend(row_refs)

                title_index = columns.get("title")
                if title_index is not None and title_index < len(values) and values[title_index]:
                    title_value = values[title_index]
                    if current_case.title_original is None:
                        current_case.title_original = title_value
                    elif current_case.title_original != title_value:
                        current_case.ambiguities.append(
                            Ambiguity(
                                code="conflicting_case_titles",
                                description="Different title text was associated with the same stated test-case identifier.",
                                source_refs=row_refs,
                            )
                        )
                elif (
                    metadata_case.title_original is not None
                    and metadata_case.stated_identifier
                    and stated_case_id
                    and metadata_case.stated_identifier.casefold() == stated_case_id.strip().casefold()
                ):
                    current_case.title_original = metadata_case.title_original

                step_id_index = columns.get("step_id")
                step_id = values[step_id_index] if step_id_index is not None and step_id_index < len(values) else None
                procedure_index = columns["procedure"]
                procedure = values[procedure_index] if procedure_index < len(values) else ""
                procedure_cell = row.cells[procedure_index] if procedure_index < len(row.cells) else _CellRecord("")
                current_case.steps.append(
                    ProcedureStep(
                        sequence=len(current_case.steps) + 1,
                        stated_identifier=step_id or None,
                        original_text=procedure,
                        source_refs=procedure_cell.refs,
                        ambiguities=(
                            [Ambiguity(code="blank_procedure", description="Procedure cell is blank in the source.", source_refs=procedure_cell.refs)]
                            if not procedure.strip()
                            else []
                        ),
                    )
                )
                expected_index = columns["expected"]
                expected = values[expected_index] if expected_index < len(values) else ""
                expected_cell = row.cells[expected_index] if expected_index < len(row.cells) else _CellRecord("")
                current_case.expected_results.append(
                    ExpectedResultCheckpoint(
                        sequence=len(current_case.expected_results) + 1,
                        original_text=expected,
                        source_refs=expected_cell.refs,
                        ambiguities=(
                            [Ambiguity(code="blank_expected_result", description="Expected result cell is blank in the source.", source_refs=expected_cell.refs)]
                            if not expected.strip()
                            else []
                        ),
                    )
                )
                for column_name in ("case_id", "title", "procedure", "expected", "step_id"):
                    cell_index = columns.get(column_name)
                    if cell_index is not None and cell_index < len(row.cells):
                        for segment_id in row.cells[cell_index].segment_ids:
                            segment_by_id[segment_id].mapping_status = "mapped"
                if not stated_case_id:
                    current_case.interpretation_status = "needs_review"

        mapped_refs = {
            segment.segment_id
            for segment in self.segments
            if segment.mapping_status in {"mapped", "metadata"}
        }
        for segment in self.segments:
            if segment.mapping_status in {"unmapped", "unsupported"}:
                reason = (
                    "Unsupported DOCX structure retained for review."
                    if segment.mapping_status == "unsupported"
                    else "Source segment is not mapped to an explicit test-case field."
                )
                unmapped.append(
                    UnmappedContent(
                        segment_id=segment.segment_id,
                        original_text=segment.text,
                        source_ref=segment.source_ref,
                        reason=reason,
                    )
                )
            elif segment.segment_id not in mapped_refs:
                continue
        return test_sets, unmapped

    def _case_metadata(self, table: _TableRecord, header_row_index: int) -> tuple[TestCase, list[str]]:
        case_identifier: str | None = None
        title: str | None = None
        case_identifier_candidates: list[str] = []
        title_candidates: list[str] = []
        source_refs: list[SourceRef] = []
        mapped_ids: list[str] = []
        for row in table.rows[:header_row_index]:
            for cell_index, cell in enumerate(row.cells):
                inline_label, inline_value = self._split_label_value(cell.text)
                field = self.field_labels.get(
                    normalize_field_label(inline_label or cell.text)
                )
                if field not in {"case_id", "title"}:
                    continue
                value_cell = cell
                value = inline_value
                if value is None or value == "":
                    value_cell = (
                        row.cells[cell_index + 1]
                        if cell_index + 1 < len(row.cells)
                        else _CellRecord("")
                    )
                    value = value_cell.text
                if field == "case_id":
                    case_identifier = value or None
                    if value:
                        case_identifier_candidates.append(value)
                else:
                    title = value or None
                    if value:
                        title_candidates.append(value)
                source_refs.extend(cell.refs + ([] if value_cell is cell else value_cell.refs))
                mapped_ids.extend(
                    cell.segment_ids
                    + ([] if value_cell is cell else value_cell.segment_ids)
                )
        ambiguity: list[Ambiguity] = []
        if len({value.strip().casefold() for value in case_identifier_candidates}) > 1:
            ambiguity.append(
                Ambiguity(
                    code="conflicting_test_case_identifiers",
                    description="Multiple different source-stated case identifiers occur in metadata; none was selected.",
                    source_refs=source_refs,
                )
            )
            case_identifier = None
        if len({value.strip().casefold() for value in title_candidates}) > 1:
            ambiguity.append(
                Ambiguity(
                    code="conflicting_test_case_titles",
                    description="Multiple different source-stated case titles occur in metadata; none was selected.",
                    source_refs=source_refs,
                )
            )
            title = None
        if not case_identifier or not case_identifier.strip():
            ambiguity.append(
                Ambiguity(
                    code="missing_test_case_identifier",
                    description="The source test-case identifier field is blank; no identifier was inferred.",
                    source_refs=source_refs,
                )
            )
        if title is None:
            ambiguity.append(
                Ambiguity(
                    code="missing_test_case_title",
                    description="No explicit test-case title was mapped from the metadata row.",
                    source_refs=source_refs,
                )
            )
        stable = sha256(
            f"{self.document_id}:table:{table.table_index}:case:{case_identifier or ''}".encode()
        ).hexdigest()[:16]
        return (
            TestCase(
                internal_id=f"case-{stable}",
                stated_identifier=case_identifier,
                title_original=title,
                source_refs=source_refs,
                ambiguities=ambiguity,
                interpretation_status="needs_review" if ambiguity else "uninterpreted",
            ),
            mapped_ids,
        )

    def build(self) -> IngestionResult:
        self._extract_source()
        candidates, conflicts, identifier, version = self._identity()
        test_sets, unmapped = self._map_test_cases()
        warnings = []
        if any(segment.kind == "unsupported_structure" for segment in self.segments):
            warnings.append("One or more unsupported OOXML structures require review.")
        document = ProtocolDocument(
            document_id=self.document_id,
            original_filename=self.filename,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            source_sha256=self.source_hash,
            hash_basis="provided_bytes",
            source_bytes=self.raw_bytes,
            protocol_identifier_as_stated=identifier,
            protocol_version_as_stated=version,
            source_segments=self.segments,
            provenance=ExtractionProvenance(
                parser_name="python-docx",
                parser_version=docx.__version__,
                method="ordered_ooxml_structure_and_explicit_table_headers",
                warnings=warnings,
            ),
        )
        protocol = CanonicalProtocol(
            document=document,
            test_sets=test_sets,
            identity_candidates=candidates,
            identity_conflicts=conflicts,
            unmapped_content=unmapped,
        )
        return IngestionResult(protocol=protocol, quality_report=evaluate_quality(protocol))


def extract_docx(
    raw_bytes: bytes,
    *,
    original_filename: str,
    label_aliases: Mapping[str, Iterable[str]] | None = None,
) -> IngestionResult:
    """Extract DOCX structure and explicit test-table fields without semantic inference."""
    if not isinstance(raw_bytes, bytes) or not raw_bytes:
        raise ValueError("DOCX source must be non-empty bytes.")
    try:
        document = docx.Document(BytesIO(raw_bytes))
    except Exception as exc:
        raise ValueError("Source is not a readable DOCX package.") from exc
    return _Extractor(document, raw_bytes, original_filename, label_aliases).build()

