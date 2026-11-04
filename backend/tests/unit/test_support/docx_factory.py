from __future__ import annotations

from io import BytesIO
from typing import Iterable

from docx import Document


def make_protocol_docx(
    test_sets: Iterable[tuple[str, str, Iterable[tuple[str, str, str]]]],
    *,
    document_id: str = "QMS-PROTOCOL-036",
    conflicting_document_id: str | None = None,
) -> bytes:
    document = Document()
    document.add_paragraph(f"Protocol ID: {document_id}")
    if conflicting_document_id:
        document.sections[0].header.paragraphs[0].text = (
            f"Protocol ID: {conflicting_document_id}"
        )

    for set_id, set_title, cases in test_sets:
        document.add_paragraph(f"Test Set {set_id}: {set_title}")
        table = document.add_table(rows=1, cols=4)
        for cell, heading in zip(
            table.rows[0].cells,
            ("Test Case ID", "Test Case Title", "Procedure", "Expected Result"),
        ):
            cell.text = heading
        for case_id, procedure, expected_result in cases:
            row = table.add_row()
            row.cells[0].text = case_id
            row.cells[1].text = f"Title for {case_id}"
            row.cells[2].text = procedure
            row.cells[3].text = expected_result

    stream = BytesIO()
    document.save(stream)
    return stream.getvalue()
