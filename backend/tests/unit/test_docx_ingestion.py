from __future__ import annotations

from hashlib import sha256
from io import BytesIO

from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

from backend.app.services.ingestion.docx_extractor import extract_docx
from backend.tests.unit.test_support.docx_factory import make_protocol_docx


def test_extracts_distinct_test_sets_and_preserves_order_and_source_refs() -> None:
    raw = make_protocol_docx(
        [
            (
                "1",
                "First group",
                [(f"CASE-A-{index:03}", f"Procedure {index}", f"Expected {index}") for index in range(1, 43)],
            ),
            (
                "2",
                "Second group",
                [(f"CASE-B-{index:03}", f"Procedure B{index}", f"Expected B{index}") for index in range(1, 9)],
            ),
        ]
    )

    result = extract_docx(raw, original_filename="protocol.docx")

    assert [len(test_set.test_cases) for test_set in result.protocol.test_sets] == [42, 8]
    assert [test_set.stated_identifier for test_set in result.protocol.test_sets] == ["1", "2"]
    first = result.protocol.test_sets[0].test_cases[0]
    assert first.stated_identifier == "CASE-A-001"
    assert first.steps[0].original_text == "Procedure 1"
    assert first.expected_results[0].original_text == "Expected 1"
    assert first.steps[0].source_refs[0].table_index is not None
    assert first.expected_results[0].source_refs[0].cell_index is not None
    assert result.protocol.document.source_bytes == raw
    assert result.protocol.document.source_sha256 == sha256(raw).hexdigest()
    assert result.protocol.document.provenance.parser_name == "python-docx"


def test_extracts_eighteen_cases_from_single_test_set() -> None:
    raw = make_protocol_docx(
        [("1", "Qualification", [(f"CASE-{i:02}", f"Do {i}", f"See {i}") for i in range(1, 19)])]
    )

    result = extract_docx(raw, original_filename="qualification.docx")

    assert len(result.protocol.test_sets) == 1
    assert len(result.protocol.test_sets[0].test_cases) == 18


def test_identity_conflict_is_preserved_and_not_auto_resolved() -> None:
    raw = make_protocol_docx(
        [("1", "Group", [("CASE-1", "Step", "Result")])],
        document_id="QMS-PROTOCOL-036",
        conflicting_document_id="QMS-PROTOCOL-035",
    )

    result = extract_docx(raw, original_filename="QMS-PROTOCOL-036.docx")

    assert result.protocol.identity_conflicts
    assert result.protocol.document.protocol_identifier_as_stated is None
    assert {c.raw_value for c in result.protocol.identity_candidates} >= {
        "QMS-PROTOCOL-036",
        "QMS-PROTOCOL-035",
    }
    assert result.quality_report.status == "BLOCKED"


def test_unrecognized_text_is_retained_and_flagged_not_converted_to_actions() -> None:
    raw = make_protocol_docx(
        [("1", "Group", [("CASE-1", "Enter the data", "System responds")])]
    )

    result = extract_docx(raw, original_filename="source.docx")

    all_text = "\n".join(segment.text for segment in result.protocol.document.source_segments)
    assert "Enter the data" in all_text
    assert "System responds" in all_text
    assert result.protocol.test_sets[0].test_cases[0].interpretation_status == "uninterpreted"
    assert result.protocol.unmapped_content
    assert not hasattr(result.protocol.test_sets[0].test_cases[0], "actions")


def test_preserves_header_footer_merged_cells_and_nested_table_structure() -> None:
    document = Document()
    document.sections[0].header.paragraphs[0].text = "Header source marker"
    document.sections[0].footer.paragraphs[0].text = "Footer source marker"
    table = document.add_table(rows=1, cols=2)
    merged = table.cell(0, 0).merge(table.cell(0, 1))
    merged.text = "Merged source marker"
    nested = merged.add_table(rows=1, cols=1)
    nested.cell(0, 0).text = "Nested source marker"
    stream = BytesIO()
    document.save(stream)

    result = extract_docx(stream.getvalue(), original_filename="structure.docx")
    segments = result.protocol.document.source_segments

    assert {"Header source marker", "Footer source marker", "Merged source marker", "Nested source marker"}.issubset(
        {segment.text for segment in segments}
    )
    merged_segment = next(segment for segment in segments if segment.text == "Merged source marker")
    nested_segment = next(segment for segment in segments if segment.text == "Nested source marker")
    assert merged_segment.source_ref.grid_span == 2
    assert nested_segment.source_ref.nested_table_path
    assert any(segment.source_ref.part == "header_paragraph" for segment in segments)
    assert any(segment.source_ref.part == "footer_paragraph" for segment in segments)


def test_corrupt_docx_fails_without_partial_protocol() -> None:
    try:
        extract_docx(b"not a docx", original_filename="broken.docx")
    except ValueError as exc:
        assert "readable DOCX" in str(exc)
    else:
        raise AssertionError("Corrupt DOCX must fail ingestion")


def test_preserves_compound_step_and_checkpoint_trajectory() -> None:
    document = Document()
    table = document.add_table(rows=1, cols=4)
    for cell, heading in zip(
        table.rows[0].cells,
        ("Test Case ID", "Test Case Title", "Procedure", "Expected Result"),
    ):
        cell.text = heading
    for case_id, procedure, expected in (
        ("TC-1", "First procedure", "First checkpoint"),
        ("TC-1", "Second procedure", "Second checkpoint"),
        ("", "Continuation procedure", "Final checkpoint"),
    ):
        row = table.add_row()
        row.cells[0].text = case_id
        row.cells[2].text = procedure
        row.cells[3].text = expected
    stream = BytesIO()
    document.save(stream)

    result = extract_docx(stream.getvalue(), original_filename="compound.docx")
    case = result.protocol.test_sets[0].test_cases[0]

    assert [step.original_text for step in case.steps] == [
        "First procedure",
        "Second procedure",
        "Continuation procedure",
    ]
    assert [step.sequence for step in case.steps] == [1, 2, 3]
    assert [checkpoint.original_text for checkpoint in case.expected_results] == [
        "First checkpoint",
        "Second checkpoint",
        "Final checkpoint",
    ]
    assert "continuation_row_without_identifier" in {
        ambiguity.code for ambiguity in case.ambiguities
    }


def test_preserves_explicit_numbering_provenance() -> None:
    document = Document()
    paragraph = document.add_paragraph("Numbered source instruction")
    number_properties = OxmlElement("w:numPr")
    level = OxmlElement("w:ilvl")
    level.set(qn("w:val"), "0")
    number_id = OxmlElement("w:numId")
    number_id.set(qn("w:val"), "17")
    number_properties.append(level)
    number_properties.append(number_id)
    paragraph._p.get_or_add_pPr().append(number_properties)
    stream = BytesIO()
    document.save(stream)

    result = extract_docx(stream.getvalue(), original_filename="numbered.docx")
    segment = next(
        item for item in result.protocol.document.source_segments
        if item.text == "Numbered source instruction"
    )

    assert segment.source_ref.numbering_id == 17
    assert segment.source_ref.numbering_level == 0


def test_detects_header_identifier_conflict_and_metadata_step_layout() -> None:
    document = Document()
    document.sections[0].header.paragraphs[0].text = (
        "CLIN-EU-PAT-OPV-1-1-OQ-035, V1.0"
    )
    document.add_paragraph("Test Set# 1: Explicit Scenario Group")
    table = document.add_table(rows=2, cols=4)
    for cell, label in zip(
        table.rows[0].cells,
        ("Test Case #:", "", "Test Case Name:", "Explicit Case Title"),
    ):
        cell.text = label
    for cell, label in zip(
        table.rows[1].cells,
        ("Step #", "Procedure", "", "Expected Results"),
    ):
        cell.text = label
    for step_id, procedure, expected in (
        ("1", "First source instruction", "First source checkpoint"),
        ("2", "Second source instruction", "Second source checkpoint"),
    ):
        row = table.add_row()
        row.cells[0].text = step_id
        row.cells[1].text = procedure
        row.cells[3].text = expected
    stream = BytesIO()
    document.save(stream)

    result = extract_docx(
        stream.getvalue(), original_filename="EU-VAL-OPV-1-1-OQ-036.docx"
    )

    assert result.quality_report.status == "BLOCKED"
    assert result.protocol.document.protocol_identifier_as_stated is None
    assert any(
        conflict.identity_type == "protocol_identifier"
        for conflict in result.protocol.identity_conflicts
    )
    case = result.protocol.test_sets[0].test_cases[0]
    assert case.stated_identifier is None
    assert case.title_original == "Explicit Case Title"
    assert [step.stated_identifier for step in case.steps] == ["1", "2"]
    assert [step.original_text for step in case.steps] == [
        "First source instruction",
        "Second source instruction",
    ]
    assert [result.original_text for result in case.expected_results] == [
        "First source checkpoint",
        "Second source checkpoint",
    ]
    assert "missing_test_case_identifier" in {
        ambiguity.code for ambiguity in case.ambiguities
    }


def test_extensible_labels_metadata_rows_late_header_and_unseen_identifier_format() -> None:
    document = Document()
    document.sections[0].header.paragraphs[0].text = "Document ID: VAL.CASE.77.R1"
    table = document.add_table(rows=12, cols=4)
    table.cell(1, 0).text = "Test Set ID: Group-2046"
    table.cell(3, 0).text = "Scenario Code"
    table.cell(3, 1).text = "FLOW.R9.2046"
    table.cell(7, 0).text = "Scenario Heading"
    table.cell(7, 1).text = "A future layout title"
    for cell, label in zip(
        table.rows[10].cells,
        ("Scenario Code", "Action Ref", "User Activity", "Observed State"),
    ):
        cell.text = label
    row = table.add_row()
    row.cells[0].text = "FLOW.R9.2046"
    row.cells[1].text = "ACT-4"
    row.cells[2].text = "Preserve the future-facing instruction exactly."
    row.cells[3].text = "Observe the stated outcome."
    stream = BytesIO()
    document.save(stream)

    result = extract_docx(
        stream.getvalue(),
        original_filename="unfamiliar-source.docx",
        label_aliases={
            "case_id": ("Scenario Code",),
            "title": ("Scenario Heading",),
            "procedure": ("User Activity",),
            "expected": ("Observed State",),
            "step_id": ("Action Ref",),
        },
    )

    assert result.protocol.document.protocol_identifier_as_stated == "VAL.CASE.77.R1"
    assert result.protocol.test_sets[0].stated_identifier == "Group-2046"
    case = result.protocol.test_sets[0].test_cases[0]
    assert case.stated_identifier == "FLOW.R9.2046"
    assert case.title_original == "A future layout title"
    assert case.steps[0].stated_identifier == "ACT-4"
    assert case.steps[0].original_text == "Preserve the future-facing instruction exactly."
    assert case.expected_results[0].original_text == "Observe the stated outcome."


def test_paragraph_fields_map_explicit_labels_and_keep_unrecognized_directives() -> None:
    document = Document()
    source_lines = [
        "Test Set ID: PAR-7",
        "Test Set Name: Paragraph workflow",
        "Test Case ID: CASE.2046.X",
        "Title: Paragraph authored case",
        "Step Number: 004",
        "Procedure: Keep unfamiliar wording and punctuation?!",
        "Expected Outcome: A specific response is shown.",
        "Section Directive: Continue using the source-defined section context.",
        "Note: Repeat the prior instruction exactly.",
    ]
    for line in source_lines:
        document.add_paragraph(line)
    stream = BytesIO()
    document.save(stream)

    result = extract_docx(stream.getvalue(), original_filename="paragraphs.docx")

    case = result.protocol.test_sets[0].test_cases[0]
    assert result.protocol.test_sets[0].stated_identifier == "PAR-7"
    assert case.stated_identifier == "CASE.2046.X"
    assert case.steps[0].stated_identifier == "004"
    assert case.steps[0].original_text == "Keep unfamiliar wording and punctuation?!"
    assert case.expected_results[0].original_text == "A specific response is shown."
    preserved = {item.original_text for item in result.protocol.unmapped_content}
    assert source_lines[7] in preserved
    assert source_lines[8] in preserved


def test_unknown_docx_structure_is_preserved_and_flagged_without_mapping() -> None:
    document = Document()
    text = "Section directive: keep the surrounding context."
    document.add_paragraph(text)
    table = document.add_table(rows=2, cols=2)
    table.cell(0, 0).text = "Future Control"
    table.cell(0, 1).text = "Interpretation Hint"
    table.cell(1, 0).text = "Unknown source value A"
    table.cell(1, 1).text = "Unknown source value B"
    stream = BytesIO()
    document.save(stream)
    raw = stream.getvalue()

    result = extract_docx(raw, original_filename="future-layout.docx")

    assert result.protocol.document.source_bytes == raw
    source_text = {segment.text for segment in result.protocol.document.source_segments}
    assert {text, "Future Control", "Interpretation Hint", "Unknown source value A", "Unknown source value B"}.issubset(source_text)
    assert not result.protocol.test_sets
    assert result.quality_report.status == "NEEDS_REVIEW"
    accounted = {
        segment.segment_id
        for segment in result.protocol.document.source_segments
        if segment.mapping_status in {"mapped", "metadata"}
    }
    accounted.update(item.segment_id for item in result.protocol.unmapped_content)
    assert accounted == {segment.segment_id for segment in result.protocol.document.source_segments}


def test_conflicting_metadata_identifiers_are_not_silently_selected() -> None:
    document = Document()
    table = document.add_table(rows=4, cols=3)
    table.cell(0, 0).text = "Test Case ID"
    table.cell(0, 1).text = "CASE-A-2046"
    table.cell(1, 0).text = "Test Case ID"
    table.cell(1, 1).text = "CASE-B-2046"
    for cell, label in zip(
        table.rows[2].cells,
        ("Step #", "Procedure", "Expected Result"),
    ):
        cell.text = label
    table.cell(3, 0).text = "1"
    table.cell(3, 1).text = "Preserve this instruction."
    table.cell(3, 2).text = "Preserve this expectation."
    stream = BytesIO()
    document.save(stream)

    result = extract_docx(stream.getvalue(), original_filename="conflicting-meta.docx")
    case = result.protocol.test_sets[0].test_cases[0]

    assert case.stated_identifier is None
    assert "conflicting_test_case_identifiers" in {
        ambiguity.code for ambiguity in case.ambiguities
    }
    assert {segment.text for segment in result.protocol.document.source_segments}.issuperset(
        {"CASE-A-2046", "CASE-B-2046"}
    )
