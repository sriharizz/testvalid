from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest

from backend.app.infrastructure.catalog_repository import JsonCatalogRepository
from backend.app.infrastructure.qwen_client import QwenClient, QwenSettings
from backend.app.schemas.data_generation import (
    ActionIntent,
    DataGenerationOutput,
    GeneratedFieldValue,
    GenerationInput,
    GenerationStep,
    NavigationTarget,
)
from backend.app.services.catalog.catalog_manager import CatalogManager
from backend.app.services.data_generation.generator import (
    QwenDataGenerator,
    _select_generation_cards,
)
from backend.app.services.data_generation.input_adapter import generation_input_from_case
from backend.app.services.data_generation.prompt_builder import (
    DataGenerationPromptBuilder,
    UnsafeGenerationInputError,
)
from backend.app.services.data_generation.validator import DataGenerationValidator
from backend.app.services.ingestion.author_input_adapter import adapt_authored_test_case
from backend.app.services.retrieval.section_first import SectionFirstRetriever
from backend.app.services.retrieval.ui_mini_rag import RetrievalScope, UIMiniRAG


ROOT = Path(__file__).resolve().parents[3]
CATALOG = ROOT / "catalog" / "ui" / "application_catalog.json"
MANIFEST = ROOT / "catalog" / "ui" / "discovery_manifest.json"


@pytest.fixture
def generation_runtime(tmp_path: Path):
    snapshot = CatalogManager(JsonCatalogRepository(tmp_path / "catalog")).import_file(
        CATALOG, MANIFEST
    )
    rag = UIMiniRAG([snapshot])
    scope = RetrievalScope(
        application=snapshot.scope.application,
        environment=snapshot.scope.environment,
        catalog_version=snapshot.catalog_version,
        snapshot_id=snapshot.snapshot_id,
        screen_id="manual_case_registration",
        variant="Adverse Event",
    )
    return snapshot, rag, scope


def _request(section: str, step: str = "In Reporter, enter First Name: Morgan Example.") -> GenerationInput:
    return GenerationInput(
        protocol_id="authored-synthetic-test",
        source_case_identifier_as_stated="HUMAN-1",
        application="OnePV",
        environment="development",
        scenario_ref="case-1",
        title=f"{section} data",
        steps=[GenerationStep(step_ref="case-1:step:1", original_text=step)],
    )


def _cards(request: GenerationInput, rag: UIMiniRAG, scope: RetrievalScope) -> tuple[list[dict], object]:
    context = SectionFirstRetriever(rag).retrieve(
        "\n".join(step.original_text for step in request.steps), scope
    )
    cards = [
        json.loads(unit.content)
        for unit in rag.context_units(context.retrieval)
    ]
    return cards, context


def _valid_output(request: GenerationInput, cards: list[dict], *, value="Morgan Example") -> DataGenerationOutput:
    screen = next(card for card in cards if card.get("record_type") == "screen")
    section = next(card for card in cards if card.get("record_type") == "section")
    field = next(
        card
        for card in cards
        if card.get("record_type") == "control" and card.get("label") == "First Name(English)"
    )
    return DataGenerationOutput(
        status="ready",
        navigation_targets=[
            NavigationTarget(
                screen_id=screen["screen"]["id"],
                screen_card_id=screen["card_id"],
                section_card_id=section["card_id"],
                section_path=tuple(section["section_path"]),
            )
        ],
        action_intents=[
            ActionIntent(kind="navigate_screen", target_ref=screen["card_id"], source_step_ref=request.steps[0].step_ref),
            ActionIntent(kind="open_section", target_ref=section["card_id"], source_step_ref=request.steps[0].step_ref),
            ActionIntent(kind="fill_section", target_ref=section["card_id"], source_step_ref=request.steps[0].step_ref),
        ],
        field_values=[
            GeneratedFieldValue(
                field_ref=field["card_id"],
                field_label=field["label"],
                value=value,
                provenance="protocol_explicit",
                source_step_ref=request.steps[0].step_ref,
            )
        ],
    )


def test_authored_source_step_is_preserved_without_expected_result(generation_runtime) -> None:
    _, rag, scope = generation_runtime
    authored = adapt_authored_test_case(
        {
            "test_set_id": "AUTHORED-1",
            "test_case_id": "HUMAN-1",
            "title": "Reporter details",
            "steps": [
                {
                    "step_id": "S1",
                    "procedure": "In Reporter, enter First Name: Morgan Example.",
                    "expected_result": "Reporter details are saved.",
                }
            ],
        }
    ).protocol
    case = authored.test_sets[0].test_cases[0]
    request = generation_input_from_case(
        authored, case, application="OnePV", environment="development"
    )
    cards, context = _cards(request, rag, scope)
    prepared = request.model_copy(update={"ui_context_cards": cards})
    prompt = DataGenerationPromptBuilder().build(prepared)
    payload = json.loads(prompt.user_prompt)

    assert request.steps[0].original_text == "In Reporter, enter First Name: Morgan Example."
    assert context.selected_section_paths == (("Reporter",),)
    assert "expected_result_checkpoints" not in payload
    assert "Reporter details are saved." not in prompt.user_prompt
    assert "actions" in prompt.system_prompt


def test_output_contains_typed_action_intents_and_field_value(generation_runtime) -> None:
    _, rag, scope = generation_runtime
    request = _request("Reporter")
    cards, _ = _cards(request, rag, scope)
    output = _valid_output(request, cards)
    report = DataGenerationValidator().validate(output, request.model_copy(update={"ui_context_cards": cards}))

    assert report.status == "ready"
    assert output.navigation_targets[0].screen_id == "manual_case_registration"
    assert output.navigation_targets[0].section_path == ("Reporter",)
    assert output.field_values[0].field_label == "First Name(English)"
    assert output.action_intents[0].kind == "navigate_screen"
    assert output.action_intents[2].kind == "fill_section"
    assert not hasattr(output, "checkpoints")


def test_model_output_schema_rejects_action_plans_and_verdicts() -> None:
    with pytest.raises(Exception):
        DataGenerationOutput.model_validate(
            {
                "status": "ready",
                "navigation_targets": [],
                "action_intents": [],
                "field_values": [],
                "actions": [{"type": "click"}],
                "verdict": "PASS",
            }
        )


def test_synthetic_value_is_allowed_but_unknown_field_is_rejected(generation_runtime) -> None:
    _, rag, scope = generation_runtime
    request = _request("Reporter", "Fill the Reporter section with dummy test data.")
    cards, _ = _cards(request, rag, scope)
    prepared = request.model_copy(update={"ui_context_cards": cards})
    output = _valid_output(request, cards, value="Synthetic Reporter")
    field = output.field_values[0].model_copy(update={"provenance": "qwen_synthetic"})
    output = output.model_copy(update={"field_values": [field]})
    assert DataGenerationValidator().validate(output, prepared).status == "ready"

    unknown = field.model_copy(update={"field_ref": "unretrieved-field"})
    output = output.model_copy(update={"field_values": [unknown]})
    assert any(
        issue.code == "unknown_field"
        for issue in DataGenerationValidator().validate(output, prepared).issues
    )


def test_click_action_target_must_be_present_in_cited_source(generation_runtime) -> None:
    _, rag, scope = generation_runtime
    request = _request("Reporter", "Fill the Reporter details and click Save.")
    cards, _ = _cards(request, rag, scope)
    prepared = request.model_copy(update={"ui_context_cards": cards})
    output = _valid_output(request, cards).model_copy(
        update={
            "action_intents": [
                *_valid_output(request, cards).action_intents,
                ActionIntent(
                    kind="click_control",
                    target_text="Delete",
                    source_step_ref=request.steps[0].step_ref,
                ),
            ]
        }
    )
    report = DataGenerationValidator().validate(output, prepared)
    assert any(issue.code == "unsupported_click_target" for issue in report.issues)


def test_disabled_field_cannot_receive_generated_value(generation_runtime) -> None:
    _, rag, scope = generation_runtime
    request = _request("Product", "In Product enter Product Name: Sample Medicine.")
    cards, _ = _cards(request, rag, scope)
    product_field = next(
        card
        for card in cards
        if card.get("record_type") == "control" and card.get("label") == "Product Name(English)"
    )
    assert product_field["enabled"] is False
    prepared = request.model_copy(update={"ui_context_cards": cards})
    screen = next(card for card in cards if card.get("record_type") == "screen")
    section = next(card for card in cards if card.get("record_type") == "section")
    output = DataGenerationOutput(
        status="ready",
        navigation_targets=[NavigationTarget(
            screen_id=screen["screen"]["id"],
            screen_card_id=screen["card_id"],
            section_card_id=section["card_id"],
            section_path=tuple(section["section_path"]),
        )],
        field_values=[GeneratedFieldValue(
            field_ref=product_field["card_id"],
            field_label=product_field["label"],
            value="Sample Medicine",
            provenance="protocol_explicit",
            source_step_ref=request.steps[0].step_ref,
        )],
    )
    assert any(
        issue.code == "field_disabled"
        for issue in DataGenerationValidator().validate(output, prepared).issues
    )


def test_dynamic_dropdown_requires_runtime_search_mode(generation_runtime) -> None:
    _, rag, scope = generation_runtime
    request = _request("Reporter", "In Reporter, choose Country Code: United States.")
    cards, _ = _cards(request, rag, scope)
    prepared = request.model_copy(update={"ui_context_cards": cards})
    screen = next(card for card in cards if card.get("record_type") == "screen")
    section = next(card for card in cards if card.get("record_type") == "section")
    country = next(card for card in cards if card.get("label") == "Country Code")
    base = DataGenerationOutput(
        status="ready",
        navigation_targets=[NavigationTarget(
            screen_id=screen["screen"]["id"],
            screen_card_id=screen["card_id"],
            section_card_id=section["card_id"],
            section_path=tuple(section["section_path"]),
        )],
        action_intents=[
            ActionIntent(kind="navigate_screen", target_ref=screen["card_id"], source_step_ref=request.steps[0].step_ref),
            ActionIntent(kind="open_section", target_ref=section["card_id"], source_step_ref=request.steps[0].step_ref),
            ActionIntent(kind="fill_section", target_ref=section["card_id"], source_step_ref=request.steps[0].step_ref),
        ],
        field_values=[GeneratedFieldValue(
            field_ref=country["card_id"], field_label=country["label"],
            value="United States", value_mode="direct", provenance="protocol_explicit",
            source_step_ref=request.steps[0].step_ref,
        )],
    )
    report = DataGenerationValidator().validate(base, prepared)
    assert any(issue.code == "runtime_search_required" for issue in report.issues)

    search = base.field_values[0].model_copy(update={"value_mode": "runtime_search"})
    valid = base.model_copy(update={"field_values": [search]})
    assert DataGenerationValidator().validate(valid, prepared).status == "ready"


def test_unrequested_optional_field_is_marked_for_review(generation_runtime) -> None:
    _, rag, scope = generation_runtime
    request = _request("Reporter", "Fill enabled required Reporter fields with dummy data.")
    cards, _ = _cards(request, rag, scope)
    prepared = request.model_copy(update={"ui_context_cards": cards})
    screen = next(card for card in cards if card.get("record_type") == "screen")
    section = next(card for card in cards if card.get("record_type") == "section")
    optional = next(
        card
        for card in cards
        if card.get("record_type") == "control"
        and card.get("required") is False
        and card.get("control_type") not in {"button", "icon_button", "link"}
    )
    output = DataGenerationOutput(
        status="ready",
        navigation_targets=[NavigationTarget(
            screen_id=screen["screen"]["id"],
            screen_card_id=screen["card_id"],
            section_card_id=section["card_id"],
            section_path=tuple(section["section_path"]),
        )],
        field_values=[GeneratedFieldValue(
            field_ref=optional["card_id"],
            field_label=optional["label"],
            value="Synthetic optional",
            provenance="qwen_synthetic",
            source_step_ref=request.steps[0].step_ref,
        )],
    )
    assert any(
        issue.code == "unrequested_optional_field"
        for issue in DataGenerationValidator().validate(output, prepared).issues
    )


def test_sensitive_source_blocks_prompt_creation(generation_runtime) -> None:
    _, rag, scope = generation_runtime
    request = _request("Reporter").model_copy(update={"sensitive_content_present": True})
    cards, _ = _cards(request, rag, scope)
    with pytest.raises(UnsafeGenerationInputError):
        DataGenerationPromptBuilder().build(request.model_copy(update={"ui_context_cards": cards}))


def test_generator_sends_one_compact_request_and_captures_usage(generation_runtime) -> None:
    _, rag, scope = generation_runtime
    request = _request("Reporter")
    cards, context = _cards(request, rag, scope)
    response = json.dumps({
        "action_intents": [
            {"kind": "navigate_screen", "target_key": "p1", "step_ref": "1"},
            {"kind": "open_section", "target_key": "s1", "step_ref": "1"},
            {"kind": "fill_section", "target_key": "s1", "step_ref": "1"},
        ],
        "field_values": [
            {"field_key": "f1", "value": "Morgan Example", "source_step_ref": "1"}
        ],
    })
    seen: list[dict] = []

    def handler(http_request: httpx.Request) -> httpx.Response:
        body = json.loads(http_request.content)
        seen.append(body)
        prompt = json.loads(body["messages"][1]["content"])
        assert "expected_result_checkpoints" not in prompt
        assert "action_intents" in prompt["output_contract"]
        cards_sent = prompt["sections"]
        assert len(cards_sent) >= 1
        labels_sent = {section["section"] for section in cards_sent}
        labels_sent.update(
            field["label"]
            for section in cards_sent
            for field in section["fields"]
        )
        labels_sent.add(prompt["screen"]["label"])
        assert {"Manual Case Registration", "Reporter", "First Name(English)", "Country Code"} <= labels_sent
        assert all(
            set(field) <= {"key", "label", "type", "options"}
            for section in cards_sent
            for field in section["fields"]
        )
        assert all("source_ref" not in card and "locator_recipe_status" not in card for card in cards_sent)
        assert all("source_refs" not in step for step in prompt["steps"])
        return httpx.Response(
            200,
            json={
                "model": "qwen-test",
                "choices": [{"message": {"content": response}}],
                "usage": {"prompt_tokens": 301, "completion_tokens": 71, "total_tokens": 372},
            },
        )

    settings = QwenSettings("groq", "https://provider.invalid/openai/v1", "test-key", "qwen-test")
    with QwenClient(settings, transport=httpx.MockTransport(handler)) as client:
        result = QwenDataGenerator(
            client,
            SectionFirstRetriever(rag),
            allow_provider_reported_only=True,
        ).generate(request, scope)

    assert len(seen) == 1
    assert result.validation.status == "ready", result.validation.issues
    assert result.output.field_values[0].value == "Morgan Example"
    assert [action.kind for action in result.output.action_intents] == [
        "navigate_screen", "open_section", "fill_section"
    ]
    assert result.selected_section_paths == [list(path) for path in context.selected_section_paths]
    assert result.token_usage.model_dump(mode="json") == {
        "prompt_tokens": 301,
        "completion_tokens": 71,
        "total_tokens": 372,
    }


def test_compact_context_keeps_required_and_explicitly_named_optional_controls(generation_runtime) -> None:
    _, rag, scope = generation_runtime
    request = _request(
        "Reporter",
        "In Reporter enter First Name(English), Email Address and City(English).",
    )
    cards, _ = _cards(request, rag, scope)

    compact = _select_generation_cards(cards, request)
    labels = {
        card.get("label") or (card.get("screen") or {}).get("title")
        for card in compact
    }

    assert labels == {
        "Manual Case Registration",
        "Reporter",
        "First Name(English)",
        "Country Code",
        "Email Address",
        "City(English)",
    }
    assert len(compact) == 6

