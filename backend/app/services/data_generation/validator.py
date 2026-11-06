from __future__ import annotations

from collections.abc import Mapping

from backend.app.schemas.data_generation import (
    DataGenerationOutput,
    GenerationInput,
    GenerationValidationIssue,
    GenerationValidationReport,
)


NON_DATA_CONTROLS = {"button", "icon_button", "link", "tab", "navigation"}


class DataGenerationValidator:
    def validate(
        self,
        output: DataGenerationOutput,
        request: GenerationInput,
    ) -> GenerationValidationReport:
        issues: list[GenerationValidationIssue] = []
        if request.source_status == "blocked":
            issues.append(_issue("source_blocked", "Source quality blocks generation."))
        elif request.source_status == "needs_review":
            issues.append(_issue("source_needs_review", "Source extraction requires review."))
        if request.source_ambiguities:
            issues.append(_issue("source_ambiguity", "Source contains unresolved ambiguity."))

        cards = request.ui_context_cards
        screens = {
            str(card.get("screen", {}).get("id")): card
            for card in cards
            if card.get("record_type") == "screen"
            and isinstance(card.get("screen"), Mapping)
            and card.get("screen", {}).get("id")
        }
        sections = {
            str(card.get("card_id")): tuple(card.get("section_path") or ())
            for card in cards
            if card.get("record_type") == "section" and card.get("card_id")
        }
        screen_card_ids = {
            str(card.get("card_id"))
            for card in cards
            if card.get("record_type") == "screen" and card.get("card_id")
        }
        controls = {
            str(card.get("card_id")): card
            for card in cards
            if card.get("record_type") == "control" and card.get("card_id")
        }
        steps = {step.step_ref: step for step in request.steps}

        for section_path in request.section_fill_paths:
            path = tuple(section_path)
            has_data_control = any(
                card.get("record_type") == "control"
                and card.get("enabled") is not False
                and str(card.get("control_type") or "").casefold() not in NON_DATA_CONTROLS
                and tuple(card.get("section_path") or ())[: len(path)] == path
                for card in cards
            )
            if not has_data_control:
                issues.append(
                    _issue(
                        "section_controls_missing",
                        "A selected section has no retrieved enabled data-entry controls.",
                    )
                )

        target_keys: set[tuple[str, tuple[str, ...]]] = set()
        for target in output.navigation_targets:
            if target.screen_id not in screens:
                issues.append(_issue("unknown_screen", "Navigation target screen is not in retrieved UI context."))
            screen = screens.get(target.screen_id)
            if screen is not None and target.screen_card_id != str(screen.get("card_id")):
                issues.append(_issue("screen_card_mismatch", "Screen card ID does not match the target screen."))
            path = tuple(target.section_path)
            if target.section_card_id is not None and sections.get(target.section_card_id) != path:
                issues.append(_issue("section_card_mismatch", "Section card ID does not match the target section path."))
            elif path and path not in set(sections.values()) and not any(
                tuple(card.get("section_path") or ()) == path for card in cards
            ):
                issues.append(_issue("unknown_section", "Navigation target section is not present in retrieved UI context."))
            target_keys.add((target.screen_id, path))

        action_keys: set[tuple[str, str | None, str | None, str]] = set()
        fill_section_targets: set[str] = set()
        for action in output.action_intents:
            step = steps.get(action.source_step_ref)
            if step is None or step.excluded_from_model:
                issues.append(_issue("unknown_action_source_step", "Action intent must cite an included source step.", source_ref=action.source_step_ref))
                continue
            key = (action.kind, action.target_ref, action.target_text, action.source_step_ref)
            if key in action_keys:
                issues.append(_issue("duplicate_action_intent", "Action intent is duplicated.", source_ref=action.source_step_ref))
            action_keys.add(key)
            if action.kind == "navigate_screen":
                if action.target_ref not in screen_card_ids or action.target_text is not None:
                    issues.append(_issue("invalid_action_screen_target", "navigate_screen must target a retrieved screen card."))
            elif action.kind in {"open_section", "fill_section"}:
                if action.target_ref not in sections or action.target_text is not None:
                    issues.append(_issue("invalid_action_section_target", f"{action.kind} must target a retrieved section card."))
                if action.kind == "fill_section" and action.target_ref is not None:
                    fill_section_targets.add(action.target_ref)
            elif action.kind == "click_control":
                source = step.original_text.casefold()
                if (
                    not action.target_text
                    or action.target_ref is not None
                    or action.target_text.casefold() not in source
                ):
                    issues.append(_issue("unsupported_click_target", "click_control target text must appear in its cited source step."))

        if not output.action_intents:
            issues.append(_issue("action_intents_missing", "Output contains no source-grounded action intents."))

        seen_fields: set[str] = set()
        for value in output.field_values:
            if value.field_ref in seen_fields:
                issues.append(_issue("duplicate_field", "A field has more than one generated value.", value.field_ref))
            seen_fields.add(value.field_ref)
            card = controls.get(value.field_ref)
            if card is None:
                issues.append(_issue("unknown_field", "Field ID is absent from retrieved UI context.", value.field_ref))
                continue
            if str(card.get("label")) != value.field_label:
                issues.append(_issue("field_label_mismatch", "Field label does not match its catalog card.", value.field_ref))
            control_type = str(card.get("control_type") or "").casefold()
            if control_type in NON_DATA_CONTROLS or not control_type:
                issues.append(_issue("not_data_entry_control", "Target is not a data-entry control.", value.field_ref))
            if card.get("enabled") is False:
                issues.append(_issue("field_disabled", "Catalog marks the target field disabled.", value.field_ref))
            step = steps.get(value.source_step_ref)
            if step is None or step.excluded_from_model:
                issues.append(_issue("unknown_source_step", "Value must cite an included source step.", value.field_ref, value.source_step_ref))
            elif (
                card.get("required") is False
                and tuple(card.get("section_path") or ())
                not in {tuple(path) for path in request.section_fill_paths}
                and str(card.get("label") or "").casefold() not in step.original_text.casefold()
            ):
                issues.append(_issue("unrequested_optional_field", "Optional field is not explicitly named in the source step.", value.field_ref, value.source_step_ref))
            elif value.provenance == "protocol_explicit" and isinstance(value.value, str):
                if value.value and value.value not in step.original_text:
                    issues.append(_issue("unsupported_explicit_value", "Explicit value is not present in its cited source step.", value.field_ref, value.source_step_ref))
            if value.provenance == "intentionally_blank":
                source = step.original_text.casefold() if step is not None else ""
                if "blank" not in source and "empty" not in source:
                    issues.append(_issue("unsupported_blank", "Intentional blank is not explicitly stated in the source step.", value.field_ref, value.source_step_ref))
            option = card.get("option_resolution")
            compact_option_mode = card.get("option_mode")
            if control_type in {"dropdown", "select", "combobox", "mat-select"}:
                if (
                    compact_option_mode == "runtime_search"
                    or isinstance(option, Mapping) and option.get("requires_runtime_lookup")
                ):
                    if value.value_mode != "runtime_search":
                        issues.append(_issue("runtime_search_required", "Searchable option field requires a runtime search value.", value.field_ref))
                elif isinstance(option, Mapping):
                    candidates = option.get("candidate_values") or []
                    if value.value_mode == "runtime_search" or (
                        candidates and value.value not in candidates
                    ):
                        issues.append(_issue("unsupported_option", "Dropdown value is not an available catalog option.", value.field_ref))
                elif isinstance(card.get("allowed_options"), list):
                    candidates = card.get("allowed_options") or []
                    if value.value_mode == "runtime_search" or value.value not in candidates:
                        issues.append(_issue("unsupported_option", "Dropdown value is not an available catalog option.", value.field_ref))
                else:
                    issues.append(_issue("option_metadata_missing", "Dropdown options are unavailable in retrieved context.", value.field_ref))
            field_path = tuple(card.get("section_path") or ())
            field_screen_id = card.get("screen_id") or (card.get("screen") or {}).get("id")
            if (str(field_screen_id or ""), field_path) not in target_keys:
                issues.append(_issue("field_target_missing", "Generated field is not covered by a returned screen/section target.", value.field_ref))
            section_card_id = next(
                (card_id for card_id, path in sections.items() if path == field_path),
                None,
            )
            if section_card_id is not None and section_card_id not in fill_section_targets:
                issues.append(_issue("field_fill_intent_missing", "Generated field's section is not covered by a fill_section intent.", value.field_ref))

        if not output.navigation_targets:
            issues.append(_issue("navigation_target_missing", "Output contains no validated screen/section target."))
        if not output.field_values:
            issues.append(_issue("field_values_missing", "Output contains no field values."))

        status = "needs_review" if issues or output.status != "ready" or output.unresolved else "ready"
        return GenerationValidationReport(status=status, issues=issues)


def _issue(
    code: str,
    description: str,
    field_ref: str | None = None,
    source_ref: str | None = None,
) -> GenerationValidationIssue:
    return GenerationValidationIssue(
        code=code,
        description=description,
        field_ref=field_ref,
        source_ref=source_ref,
    )
