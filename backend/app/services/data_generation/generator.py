from __future__ import annotations

import json
from typing import Any

from backend.app.infrastructure.qwen_client import QwenClient
from backend.app.schemas.data_generation import (
    ActionIntent,
    CompactDataGenerationOutput,
    DataGenerationEnvelope,
    DataGenerationOutput,
    GeneratedFieldValue,
    GenerationInput,
    GenerationValidationIssue,
    GenerationValidationReport,
    TokenUsage,
    NavigationTarget,
)
from backend.app.services.data_generation.prompt_builder import (
    PROMPT_VERSION,
    DataGenerationPrompt,
    DataGenerationPromptBuilder,
    UnsafeGenerationInputError,
)
from backend.app.services.data_generation.validator import DataGenerationValidator
from backend.app.services.retrieval.token_budget import (
    ContextBudgetExceeded,
    ContextUnit,
    TokenBudgeter,
)
from backend.app.services.retrieval.section_first import SectionFirstRetriever
from backend.app.services.retrieval.ui_mini_rag import RetrievalScope


class QwenDataGenerator:
    """Generate compact source-grounded action intents and synthetic field data."""

    def __init__(
        self,
        client: QwenClient,
        context_retriever: SectionFirstRetriever,
        *,
        prompt_builder: DataGenerationPromptBuilder | None = None,
        validator: DataGenerationValidator | None = None,
        token_budgeter: TokenBudgeter | None = None,
        allow_provider_reported_only: bool = False,
    ) -> None:
        self.client = client
        self.context_retriever = context_retriever
        self.prompt_builder = prompt_builder or DataGenerationPromptBuilder()
        self.validator = validator or DataGenerationValidator()
        self.token_budgeter = token_budgeter
        self.allow_provider_reported_only = allow_provider_reported_only

    def generate(self, request: GenerationInput, scope: RetrievalScope) -> DataGenerationEnvelope:
        if request.sensitive_content_present:
            raise UnsafeGenerationInputError(
                "Sensitive content is classified; no model request was sent."
            )
        if request.source_status == "blocked":
            return self._not_sent(request, "blocked", "source_blocked", "Source quality blocks generation.")
        if self.token_budgeter is None and not self.allow_provider_reported_only:
            return self._not_sent(
                request,
                "needs_review",
                "tokenizer_unavailable",
                "A model-matched tokenizer is required before dispatch; provider-only measurement is evaluation-only.",
            )

        query = "\n".join(
            step.original_text for step in request.steps if not step.excluded_from_model
        )
        context = self.context_retriever.retrieve(query, scope)
        if context.retrieval.status != "retrieved" or not context.retrieval.records:
            return self._not_sent(
                request,
                "needs_review",
                f"retrieval_{context.retrieval.status}",
                "Scoped UI field context is unavailable; no model request was sent.",
            )

        retrieved = [
            json.loads(unit.content)
            for unit in self.context_retriever.mini_rag.context_units(context.retrieval)
        ]
        cards = _select_generation_cards(
            retrieved,
            request,
            context.selected_section_paths,
        )
        prepared = request.model_copy(
            update={
                "ui_context_cards": cards,
                "section_fill_paths": [
                    list(path) for path in context.selected_section_paths
                ],
            }
        )
        prompt = self.prompt_builder.build(prepared)
        preflight = self._preflight(prompt)
        if isinstance(preflight, str):
            return self._not_sent(
                prepared,
                "needs_review",
                "token_budget_exceeded",
                preflight,
                snapshot_id=_snapshot_id(retrieved),
                card_ids=_card_ids(cards),
            )

        completion = self.client.complete_json(
            system_prompt=prompt.system_prompt,
            user_prompt=prompt.user_prompt,
            schema=CompactDataGenerationOutput.model_json_schema(),
        )
        try:
            compact_output = CompactDataGenerationOutput.model_validate_json(completion.content)
            output = _hydrate_compact_output(
                compact_output,
                prompt.field_ref_map,
                prompt.target_ref_map,
                prompt.source_step_ref_map,
                prepared,
                context.selected_section_paths,
            )
            validation = self.validator.validate(output, prepared)
            if validation.status != "ready" and output.status == "ready":
                output = output.model_copy(update={"status": "needs_review"})
        except Exception:
            output = DataGenerationOutput(
                status="needs_review",
                unresolved=["Model output did not match the field-data schema."],
            )
            validation = GenerationValidationReport(
                status="needs_review",
                issues=[
                    GenerationValidationIssue(
                        code="invalid_model_output",
                        description="Qwen response failed JSON/schema validation; no repair call was sent.",
                        source_ref=request.scenario_ref,
                    )
                ],
            )

        return DataGenerationEnvelope(
            output=output,
            validation=validation,
            provider=self.client.settings.provider,
            model_name=completion.model_name,
            prompt_version=PROMPT_VERSION,
            catalog_snapshot_id=_snapshot_id(retrieved),
            retrieved_card_ids=_card_ids(cards),
            retrieval_selection_mode=context.selection_mode,
            selected_section_paths=[list(path) for path in context.selected_section_paths],
            token_usage=TokenUsage(
                prompt_tokens=completion.prompt_tokens,
                completion_tokens=completion.completion_tokens,
                total_tokens=completion.total_tokens,
            ),
            preflight_prompt_tokens=preflight if isinstance(preflight, int) else None,
            token_measurement=("preflight_and_provider" if isinstance(preflight, int) else "provider_reported_only"),
        )

    def _preflight(self, prompt: DataGenerationPrompt) -> int | str | None:
        if self.token_budgeter is None:
            return None
        try:
            batches = self.token_budgeter.pack(
                (
                    ContextUnit(
                        unit_id="field-data-generation",
                        boundary_type="scenario",
                        content=json.dumps(
                            [prompt.system_prompt, prompt.user_prompt],
                            ensure_ascii=False,
                            separators=(",", ":"),
                        ),
                    ),
                )
            )
        except ContextBudgetExceeded as exc:
            return str(exc)
        return batches[0].token_count if len(batches) == 1 else "Generation prompt exceeded one-batch budget."

    def _not_sent(
        self,
        request: GenerationInput,
        status: str,
        code: str,
        description: str,
        *,
        snapshot_id: str | None = None,
        card_ids: list[str] | None = None,
    ) -> DataGenerationEnvelope:
        issue = GenerationValidationIssue(
            code=code,
            description=description,
            source_ref=request.scenario_ref,
        )
        return DataGenerationEnvelope(
            output=DataGenerationOutput(status=status, unresolved=[description]),
            validation=GenerationValidationReport(status=status, issues=[issue]),
            provider=self.client.settings.provider,
            model_name=self.client.settings.model_name,
            prompt_version=PROMPT_VERSION,
            catalog_snapshot_id=snapshot_id,
            retrieved_card_ids=card_ids or [],
        )


def _select_generation_cards(
    cards: list[dict[str, Any]],
    request: GenerationInput,
    selected_section_paths: tuple[tuple[str, ...], ...] = (),
) -> list[dict[str, Any]]:
    """Keep navigation anchors and data controls from selected sections."""
    source_text = " ".join(
        step.original_text for step in request.steps if not step.excluded_from_model
    )
    normalized_source = _normalize_field_text(source_text)
    selected_paths = tuple(tuple(path) for path in selected_section_paths)
    selected: list[dict[str, Any]] = []
    for card in cards:
        record_type = card.get("record_type")
        if record_type == "screen":
            selected.append(_generation_card(card))
        elif record_type == "section":
            selected.append(_generation_card(card))
        elif record_type == "control" and card.get("enabled") is not False:
            label = str(card.get("label") or "")
            required = card.get("required") is True
            explicitly_named = _label_is_named(label, normalized_source)
            path = tuple(card.get("section_path") or ())
            selected_by_section = any(path[: len(target)] == target for target in selected_paths)
            if required or explicitly_named or selected_by_section:
                selected.append(_generation_card(card))
    return selected


def _generation_card(card: dict[str, Any]) -> dict[str, Any]:
    record_type = card.get("record_type")
    if record_type == "screen":
        screen = card.get("screen") or {}
        return {
            "card_id": card.get("card_id"),
            "record_type": "screen",
            "screen": {
                "id": screen.get("id"),
                "title": screen.get("title"),
            },
        }
    if record_type == "section":
        return {
            "card_id": card.get("card_id"),
            "record_type": "section",
            "screen_id": (card.get("screen") or {}).get("id"),
            "section_path": card.get("section_path") or [],
            "label": card.get("label"),
        }

    result: dict[str, Any] = {
        "card_id": card.get("card_id"),
        "record_type": "control",
        "screen_id": (card.get("screen") or {}).get("id"),
        "section_path": card.get("section_path") or [],
        "label": card.get("label"),
        "control_type": card.get("control_type"),
        "required": card.get("required"),
        "enabled": card.get("enabled"),
    }
    option = card.get("option_resolution")
    if isinstance(option, dict):
        if option.get("requires_runtime_lookup"):
            result["option_mode"] = "runtime_search"
        else:
            candidates = option.get("candidate_values") or []
            result["allowed_options"] = candidates[:10]
            if option.get("full_option_count") is not None:
                result["option_count"] = option["full_option_count"]
    return result


def _hydrate_compact_output(
    compact: CompactDataGenerationOutput,
    field_ref_map: dict[str, dict[str, Any]],
    target_ref_map: dict[str, dict[str, Any]],
    source_step_ref_map: dict[str, str],
    request: GenerationInput,
    selected_section_paths: tuple[tuple[str, ...], ...],
) -> DataGenerationOutput:
    cards_by_id = {
        str(card.get("card_id")): card
        for card in request.ui_context_cards
        if card.get("card_id")
    }
    screen = next(
        (card for card in request.ui_context_cards if card.get("record_type") == "screen"),
        None,
    )
    navigation_targets: list[NavigationTarget] = []
    if screen is not None:
        sections_by_path = {
            tuple(card.get("section_path") or ()): card
            for card in request.ui_context_cards
            if card.get("record_type") == "section"
        }
        for path in selected_section_paths:
            section = sections_by_path.get(tuple(path))
            if section is not None:
                navigation_targets.append(
                    NavigationTarget(
                        screen_id=str((screen.get("screen") or {}).get("id") or ""),
                        screen_card_id=str(screen.get("card_id") or ""),
                        section_card_id=str(section.get("card_id") or ""),
                        section_path=tuple(path),
                    )
                )
        if not navigation_targets:
            navigation_targets.append(
                NavigationTarget(
                    screen_id=str((screen.get("screen") or {}).get("id") or ""),
                    screen_card_id=str(screen.get("card_id") or ""),
                )
            )

    steps = {step.step_ref: step for step in request.steps}
    compact_step_ref_map = {str(index): step.step_ref for index, step in enumerate(request.steps, start=1)}
    action_intents: list[ActionIntent] = []
    for intent in compact.action_intents:
        source_step_ref = source_step_ref_map.get(intent.step_ref)
        if source_step_ref is None or source_step_ref not in steps:
            raise ValueError("Model output cited an unknown action source step.")
        target_ref = None
        if intent.target_key is not None:
            target_card = target_ref_map.get(intent.target_key)
            if target_card is None:
                raise ValueError("Model output included an unknown compact action target.")
            target_ref = str(target_card.get("card_id") or "")
            if not target_ref:
                raise ValueError("Compact action target is missing its catalog card reference.")
        action_intents.append(
            ActionIntent(
                kind=intent.kind,
                target_ref=target_ref,
                target_text=intent.target_text,
                source_step_ref=source_step_ref,
            )
        )

    field_values: list[GeneratedFieldValue] = []
    for generated in compact.field_values:
        card = field_ref_map.get(generated.field_key)
        if card is None:
            raise ValueError("Model output included an unknown compact field key.")
        field_ref = str(card.get("card_id") or "")
        if field_ref not in cards_by_id:
            raise ValueError("Compact field key does not map to retrieved UI context.")
        source_step_ref = compact_step_ref_map.get(generated.source_step_ref)
        if source_step_ref is None or source_step_ref not in steps:
            raise ValueError("Model output cited an unknown source step.")
        if generated.value in (None, ""):
            # An intentionally omitted field remains absent from the fill map.
            continue

        step = steps[source_step_ref]
        provenance = (
            "protocol_explicit"
            if isinstance(generated.value, str) and generated.value in step.original_text
            else "qwen_synthetic"
        )
        control_type = str(card.get("control_type") or "").casefold()
        value_mode = (
            "runtime_search"
            if control_type in {"dropdown", "select", "combobox", "mat-select"}
            and card.get("option_mode") == "runtime_search"
            else "direct"
        )
        field_values.append(
            GeneratedFieldValue(
                field_ref=field_ref,
                field_label=str(card.get("label") or ""),
                value=generated.value,
                value_mode=value_mode,
                provenance=provenance,
                source_step_ref=source_step_ref,
            )
        )
    return DataGenerationOutput(
        status="ready",
        navigation_targets=navigation_targets,
        action_intents=action_intents,
        field_values=field_values,
    )


def _label_is_named(label: str, normalized_source: str) -> bool:
    normalized_label = _normalize_field_text(label)
    if not normalized_label:
        return False
    return f" {normalized_label} " in f" {normalized_source} "


def _normalize_field_text(value: str) -> str:
    import re

    value = re.sub(r"\([^)]*\)", " ", value.casefold())
    return " ".join(re.findall(r"[a-z0-9]+", value))


def _card_ids(cards: list[dict[str, Any]]) -> list[str]:
    return [str(card["card_id"]) for card in cards if card.get("card_id")]


def _snapshot_id(cards: list[dict[str, Any]]) -> str | None:
    values = {str(card["snapshot_id"]) for card in cards if card.get("snapshot_id")}
    return next(iter(values)) if len(values) == 1 else None
