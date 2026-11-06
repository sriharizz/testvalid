from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from backend.app.schemas.data_generation import GenerationInput


PROMPT_VERSION = "synthetic-field-data-actions-v2"

SYSTEM_PROMPT = """Interpret each supplied test step into compact action intents and synthetic
form values. Return JSON: {action_intents:[{kind,target_key|target_text,step_ref}],
field_values:[{field_key,value,source_step_ref}]}. Allowed kinds: navigate_screen,
open_section, fill_section, click_control. Use only screen/section keys provided;
click_control.target_text must be text explicitly present in that source step.
For requested fields, include navigate_screen, open_section and fill_section as
needed, preserving the section order in the source. Keep intents in source
order. Include click_control only when the source asks for that click (for
example, save). Do not invent actions. Use every supplied field key to fill in
requested sections except fields omitted by the source. Preserve exact source
values; otherwise generate concise fictional values. Never use real patient
data. For searchable dropdowns use the requested term; for fixed dropdowns use
only a supplied option. No locators, browser code, assertions, evidence plans
or verdicts. Python validates intents and restores catalog metadata."""


@dataclass(frozen=True)
class DataGenerationPrompt:
    system_prompt: str
    user_prompt: str
    field_ref_map: dict[str, dict[str, Any]]
    target_ref_map: dict[str, dict[str, Any]]
    source_step_ref_map: dict[str, str]
    prompt_version: str = PROMPT_VERSION


class UnsafeGenerationInputError(ValueError):
    pass


class DataGenerationPromptBuilder:
    def build(self, request: GenerationInput) -> DataGenerationPrompt:
        if request.sensitive_content_present:
            raise UnsafeGenerationInputError(
                "Sensitive content is classified in the generation input; no model prompt was built."
            )
        if any(_sensitive_card(card) for card in request.ui_context_cards):
            raise UnsafeGenerationInputError(
                "Sensitive UI controls are present in catalog context; no model prompt was built."
            )

        source_steps = [
            {
                "step_ref": str(index),
                **(
                    {
                        "excluded_from_model": True,
                        "exclusion_reason": step.exclusion_reason,
                    }
                    if step.excluded_from_model
                    else {"original_text": step.original_text}
                ),
            }
            for index, step in enumerate(request.steps, start=1)
        ]
        compact_sections, field_ref_map = project_ui_context(request.ui_context_cards)
        target_ref_map: dict[str, dict[str, Any]] = {}
        screen_card = next(
            (card for card in request.ui_context_cards if card.get("record_type") == "screen"),
            None,
        )
        screen = None
        if screen_card is not None:
            screen = screen_card.get("screen") or {}
            target_ref_map["p1"] = screen_card
        section_cards = {
            tuple(card.get("section_path") or ()): card
            for card in request.ui_context_cards
            if card.get("record_type") == "section"
        }
        for index, section in enumerate(compact_sections, start=1):
            section_key = f"s{index}"
            section["key"] = section_key
            section_path = tuple(section.get("section_path") or ())
            if section_path in section_cards:
                target_ref_map[section_key] = section_cards[section_path]

        payload = {
            "screen": (
                {"key": "p1", "label": str(screen.get("title") or "")}
                if screen_card is not None
                else None
            ),
            "steps": source_steps,
            "sections": compact_sections,
            "output_contract": "{action_intents:[{kind,target_key|target_text,step_ref}],field_values:[{field_key,value,source_step_ref}]} (step refs are the compact refs above)",
        }
        return DataGenerationPrompt(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=json.dumps(payload, ensure_ascii=False, sort_keys=True),
            field_ref_map=field_ref_map,
            target_ref_map=target_ref_map,
            source_step_ref_map={str(index): step.step_ref for index, step in enumerate(request.steps, start=1)},
        )


def project_ui_context(
    cards: list[dict[str, object]],
) -> tuple[list[dict[str, object]], dict[str, dict[str, Any]]]:
    """Project retrieved UI cards to only the field semantics Qwen needs."""
    section_groups: dict[tuple[str, ...], dict[str, object]] = {}
    field_ref_map: dict[str, dict[str, Any]] = {}
    non_data_controls = {"button", "icon_button", "link", "tab", "navigation"}

    for card in cards:
        if card.get("record_type") != "control" or card.get("enabled") is False:
            continue
        control_type = str(card.get("control_type") or "").casefold()
        if not control_type or control_type in non_data_controls:
            continue
        section_path = tuple(str(part) for part in (card.get("section_path") or []))
        group = section_groups.setdefault(
            section_path,
            {
                "section": " > ".join(section_path) or "Form",
                "section_path": list(section_path),
                "fields": [],
            },
        )
        field_key = f"f{len(field_ref_map) + 1}"
        field: dict[str, object] = {
            "key": field_key,
            "label": str(card.get("label") or ""),
            "type": control_type,
        }
        if control_type in {"dropdown", "select", "combobox", "mat-select"}:
            option_resolution = card.get("option_resolution")
            runtime_search = card.get("option_mode") == "runtime_search" or (
                isinstance(option_resolution, dict)
                and option_resolution.get("requires_runtime_lookup") is True
            )
            if runtime_search:
                field["options"] = "runtime_search"
            else:
                allowed_options = card.get("allowed_options")
                if not isinstance(allowed_options, list) and isinstance(option_resolution, dict):
                    allowed_options = option_resolution.get("candidate_values")
                if isinstance(allowed_options, list):
                    field["options"] = list(allowed_options[:4])
        group["fields"].append(field)
        field_ref_map[field_key] = card

    return list(section_groups.values()), field_ref_map


def _compact_schema(value):
    if isinstance(value, dict):
        return {
            key: _compact_schema(item)
            for key, item in value.items()
            if key not in {"title", "description", "default", "examples"}
        }
    if isinstance(value, list):
        return [_compact_schema(item) for item in value]
    return value


def _sensitive_card(card: dict[str, object]) -> bool:
    if card.get("sensitive") is True or card.get("classification") in {
        "credential",
        "secret",
        "sensitive",
    }:
        return True
    label = str(card.get("label") or "").casefold().split()
    return any(term in label for term in ("password", "secret", "cookie", "token", "credential"))
