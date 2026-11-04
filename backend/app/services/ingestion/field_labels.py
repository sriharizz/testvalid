"""Extensible labels for explicit, structural DOCX field mapping.

Aliases are normalized only for matching a field label. Source text is never
normalized or replaced. Callers can extend the defaults through
``extract_docx(label_aliases=...)`` for additional controlled document formats.
Unknown labels remain in source segments and are reported as unmapped.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping


DEFAULT_DOCX_FIELD_LABELS: dict[str, tuple[str, ...]] = {
    "case_id": (
        "test case id", "test case identifier", "test case number", "test case #",
        "case id", "case identifier", "scenario id", "scenario identifier",
        "scenario number", "scenario #", "test id",
    ),
    "title": ("test case title", "test case name", "case title", "scenario title", "title"),
    "procedure": (
        "procedure", "test procedure", "procedure steps", "test steps", "instructions",
        "step description", "action", "actions", "activity", "activities",
    ),
    "expected": (
        "expected result", "expected results", "expected outcome", "expected behavior",
        "expected behaviour", "acceptance criteria", "expected state",
    ),
    "step_id": ("step id", "step identifier", "step number", "step no", "step #", "step"),
    "test_set_id": ("test set id", "test set number", "test set #", "suite id", "group id"),
    "test_set_title": ("test set name", "test set title", "suite name", "group name"),
}


def normalize_field_label(label: str) -> str:
    """Normalize a candidate label for lookup without changing its source text."""
    return " ".join(re.sub(r"[^\w]+", " ", label.casefold()).split())


def build_field_label_map(
    extensions: Mapping[str, Iterable[str]] | None = None,
) -> dict[str, str]:
    """Build alias-to-field lookup; configured aliases extend the defaults."""
    mapping = {
        normalize_field_label(alias): field
        for field, aliases in DEFAULT_DOCX_FIELD_LABELS.items()
        for alias in aliases
    }
    for field, aliases in (extensions or {}).items():
        if field not in DEFAULT_DOCX_FIELD_LABELS:
            raise ValueError(f"Unsupported canonical field for DOCX label mapping: {field}")
        for alias in aliases:
            mapping[normalize_field_label(alias)] = field
    return mapping
