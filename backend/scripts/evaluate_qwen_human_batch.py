from __future__ import annotations

import json
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from dotenv import load_dotenv

from backend.app.infrastructure.catalog_repository import JsonCatalogRepository
from backend.app.infrastructure.qwen_client import QwenClient, QwenSettings
from backend.app.schemas.data_generation import (
    ActionIntent,
    BatchDataGenerationOutput,
    CompactBatchDataGenerationOutput,
    DataGenerationOutput,
    GenerationInput,
    GenerationStep,
    GeneratedFieldValue,
    NavigationTarget,
)
from backend.app.services.catalog.catalog_manager import CatalogManager
from backend.app.services.data_generation.prompt_builder import project_ui_context
from backend.app.services.data_generation.validator import DataGenerationValidator
from backend.app.services.retrieval.section_first import SectionFirstRetriever
from backend.app.services.retrieval.ui_mini_rag import RetrievalScope, UIMiniRAG


ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
CATALOG = ROOT / "catalog" / "ui" / "application_catalog.json"
MANIFEST = ROOT / "catalog" / "ui" / "discovery_manifest.json"
ARTIFACTS = BACKEND / "artifacts" / "qwen_evaluations"
COMPLETION_CAP = 8192

CASES = (
    (
        "human-01-reporter-details",
        "Open Manual Case Registration, fill in the Reporter details, and click Save.",
    ),
    (
        "human-02-patient-no-dob",
        "Fill in the Patient details but leave out the date of birth, then save.",
    ),
    (
        "human-03-patient-no-first-name",
        "Enter the Patient details without a first name and save.",
    ),
    (
        "human-04-reporter-country",
        "Add the Reporter details, set Country Code to United States, and save.",
    ),
    (
        "human-05-adverse-event",
        "Create an adverse event case with Reporter, Patient, and event details. Mark it serious due to hospitalization, then save.",
    ),
)

OMISSIONS = {
    "human-02-patient-no-dob": "Date of Birth",
    "human-03-patient-no-first-name": "First Name(English)",
}

SYSTEM_PROMPT = """For each case, return one JSON object containing compact
source-grounded action intents and concise fictional values:
{cases:[{case_id,action_intents:[{kind,target_key OR
target_text,step_ref}],field_values:{short_field_key:value}}]}. Use step_ref
"1" for each listed case step. Allowed kinds:
navigate_screen, open_section, fill_section, click_control. Use screen/section
keys supplied in context. Include navigation/open/fill intents needed for each
requested section and preserve the order they appear in the source. Keep
intents within each source step in source order. Use click_control only when the source explicitly asks for
the click; its target_text must appear in that case's source text. Never invent
an action. Fill every supplied field in requested sections except source
omissions; preserve explicit values. Never use real patient data. Use supplied
dropdown choices, or the requested search term for runtime_search fields. Do
not return catalog IDs, locators, code, expected results, assertions, evidence
plans or verdicts. Python validates intents and restores catalog metadata."""


class CapturingClient:
    def __init__(self, inner: QwenClient) -> None:
        self.inner = inner
        self.settings = inner.settings
        self.request_payload: dict[str, Any] | None = None
        self.raw_completion: str | None = None

    def complete_json(self, *, system_prompt: str, user_prompt: str, schema: dict[str, Any]):
        response_format: dict[str, Any] = {"type": "json_object"}
        if self.settings.json_schema_mode:
            response_format = {
                "type": "json_schema",
                "json_schema": {
                    "name": "data_generation_batch",
                    "strict": True,
                    "schema": schema,
                },
            }
        self.request_payload = {
            "model": self.settings.model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0,
            "max_completion_tokens": self.settings.max_completion_tokens,
            "response_format": response_format,
        }
        completion = self.inner.complete_json(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            schema=schema,
        )
        self.raw_completion = completion.content
        return completion


def main() -> int:
    load_dotenv(BACKEND / ".env")
    settings = replace(QwenSettings.from_environment(), max_completion_tokens=COMPLETION_CAP)
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    artifact_path = ARTIFACTS / f"phase4-human-batch-{stamp}.json"

    with TemporaryDirectory(prefix="qwen-batch-catalog-") as temp_dir:
        snapshot = CatalogManager(
            JsonCatalogRepository(Path(temp_dir) / "catalog")
        ).import_file(CATALOG, MANIFEST)
        rag = UIMiniRAG([snapshot])
        scope = RetrievalScope(
            application=snapshot.scope.application,
            environment=snapshot.scope.environment,
            catalog_version=snapshot.catalog_version,
            snapshot_id=snapshot.snapshot_id,
            screen_id="manual_case_registration",
            variant="Adverse Event",
        )
        retriever = SectionFirstRetriever(rag, option_candidate_limit=4)
        per_case: dict[str, dict[str, Any]] = {}
        shared_cards: dict[str, dict[str, Any]] = {}

        for case_id, source_text in CASES:
            step_ref = f"{case_id}:step:1"
            context = retriever.retrieve(source_text, scope)
            raw_cards = [
                json.loads(unit.content)
                for unit in rag.context_units(context.retrieval)
            ]
            for card in raw_cards:
                if card.get("card_id"):
                    shared_cards.setdefault(str(card["card_id"]), card)
            per_case[case_id] = {
                "case_id": case_id,
                "step_ref": step_ref,
                "test_text": source_text,
                "retrieval_status": context.retrieval.status,
                "selection_mode": context.selection_mode,
                "section_paths": [list(path) for path in context.selected_section_paths],
                "allowed_card_ids": [
                    str(card["card_id"])
                    for card in raw_cards
                    if card.get("card_id")
                ],
            }

        sections, field_key_to_card = project_ui_context(list(shared_cards.values()))
        path_to_section_key: dict[tuple[str, ...], str] = {}
        target_key_to_card: dict[str, dict[str, Any]] = {}
        screen_card = next(
            (card for card in shared_cards.values() if card.get("record_type") == "screen"),
            None,
        )
        if screen_card is None:
            raise RuntimeError("Retrieved UI context has no screen card.")
        target_key_to_card["p1"] = screen_card
        for index, section in enumerate(sections, start=1):
            section_key = f"s{index}"
            section["section_key"] = section_key
            section_path = tuple(section.get("section_path") or ())
            path_to_section_key[section_path] = section_key
            section_card = next(
                (
                    card for card in shared_cards.values()
                    if card.get("record_type") == "section"
                    and tuple(card.get("section_path") or ()) == section_path
                ),
                None,
            )
            if section_card is not None:
                target_key_to_card[section_key] = section_card

        case_key_to_case_id: dict[str, str] = {}
        compact_cases = []
        for index, (case_id, case_info) in enumerate(per_case.items(), start=1):
            case_key = f"c{index}"
            case_key_to_case_id[case_key] = case_id
            section_keys = [
                path_to_section_key[tuple(path)]
                for path in case_info["section_paths"]
                if tuple(path) in path_to_section_key
            ]
            compact_cases.append(
                {
                    "case_id": case_key,
                    "step_ref": "1",
                    "test_text": case_info["test_text"],
                    "sections": section_keys,
                }
            )
        payload = {
            "screen": {
                "key": "p1",
                "label": str((screen_card.get("screen") or {}).get("title") or ""),
            },
            "cases": compact_cases,
            "sections": sections,
            "output_contract": "cases[{case_id,action_intents:[{kind,target_key|target_text,step_ref}],field_values:{short_field_key:value}}]",
        }
        user_prompt = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))

        with QwenClient(settings) as client:
            capture = CapturingClient(client)
            completion = None
            error = None
            parsed = None
            normalized = None
            try:
                completion = capture.complete_json(
                    system_prompt=SYSTEM_PROMPT,
                    user_prompt=user_prompt,
                    schema=CompactBatchDataGenerationOutput.model_json_schema(),
                )
                parsed = CompactBatchDataGenerationOutput.model_validate_json(completion.content)
                normalized = _normalize_batch_output(
                    parsed,
                    per_case,
                    shared_cards,
                    case_key_to_case_id,
                    field_key_to_card,
                    target_key_to_card,
                )
            except Exception as exc:
                error = f"{type(exc).__name__}: {exc}"

        card_by_id = shared_cards
        per_case_validation: dict[str, Any] = {}
        if normalized is not None:
            results_by_case = {case.case_id: case for case in normalized.cases}
            for case_id, case_info in per_case.items():
                case_result = results_by_case.get(case_id)
                if case_result is None:
                    per_case_validation[case_id] = {"status": "needs_review", "issues": ["missing_case_output"]}
                    continue
                case_cards = [
                    card_by_id[card_id]
                    for card_id in case_info["allowed_card_ids"]
                    if card_id in card_by_id
                ]
                target_sections = [
                    card["section_path"]
                    for card in case_cards
                    if card.get("record_type") == "section"
                ]
                request = GenerationInput(
                    protocol_id="human-batch-evaluation",
                    source_case_identifier_as_stated=case_id,
                    application=snapshot.scope.application,
                    environment=snapshot.scope.environment,
                    scenario_ref=case_id,
                    title=case_id,
                    steps=[GenerationStep(step_ref=case_info["step_ref"], original_text=case_info["test_text"])],
                    ui_context_cards=case_cards,
                    section_fill_paths=target_sections,
                )
                output = DataGenerationOutput(
                    status=case_result.status,
                    navigation_targets=case_result.navigation_targets,
                    action_intents=case_result.action_intents,
                    field_values=case_result.field_values,
                    unresolved=case_result.unresolved,
                )
                validation = DataGenerationValidator().validate(output, request)
                omitted_label = OMISSIONS.get(case_id)
                omitted_present = (
                    any(value.field_label == omitted_label for value in case_result.field_values)
                    if omitted_label
                    else None
                )
                per_case_validation[case_id] = {
                    "status": validation.status,
                    "issues": [issue.model_dump(mode="json") for issue in validation.issues],
                    "action_intents": [
                        {
                            "kind": action.kind,
                            "target": (
                                action.target_text
                                if action.target_text is not None
                                else (
                                    card_by_id.get(action.target_ref or "", {}).get("label")
                                    or (
                                        card_by_id.get(action.target_ref or "", {}).get("screen") or {}
                                    ).get("title")
                                    or card_by_id.get(action.target_ref or "", {}).get("section_path")
                                )
                            ),
                            "source_step_ref": action.source_step_ref,
                        }
                        for action in case_result.action_intents
                    ],
                    "expected_omitted_label": omitted_label,
                    "omitted_field_was_returned": omitted_present,
                    "retrieved_cards": len(case_cards),
                    "retrieved_controls": [
                        card.get("label")
                        for card in case_cards
                        if card.get("record_type") == "control"
                    ],
                }

        record = {
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "provider": settings.provider,
            "model": settings.model_name,
            "prompt_version": "synthetic-field-data-actions-batch-v2",
            "configured_max_completion_tokens": settings.max_completion_tokens,
            "request_count": 1,
            "request_payload": capture.request_payload,
            "local_case_key_map": case_key_to_case_id,
            "local_field_key_map": {
                key: {
                    "card_id": card.get("card_id"),
                    "label": card.get("label"),
                    "section_path": card.get("section_path"),
                }
                for key, card in field_key_to_card.items()
            },
            "local_target_key_map": {
                key: {
                    "card_id": card.get("card_id"),
                    "record_type": card.get("record_type"),
                    "label": card.get("label"),
                    "section_path": card.get("section_path"),
                }
                for key, card in target_key_to_card.items()
            },
            "raw_completion": capture.raw_completion,
            "parsed_output": normalized.model_dump(mode="json") if normalized else None,
            "per_case_validation": per_case_validation,
            "token_usage": (
                {
                    "prompt_tokens": completion.prompt_tokens,
                    "completion_tokens": completion.completion_tokens,
                    "total_tokens": completion.total_tokens,
                }
                if completion
                else None
            ),
            "error": error,
        }
        artifact_path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"request_count=1; cases={len(CASES)}; output_cap={COMPLETION_CAP}")
    if completion:
        print(
            f"provider_tokens prompt={completion.prompt_tokens}; "
            f"completion={completion.completion_tokens}; total={completion.total_tokens}"
        )
    if normalized:
        for case_id, result in per_case_validation.items():
            print(f"{case_id}: validation={result['status']}; issues={len(result['issues'])}")
    else:
        print(f"request_error={error}")
    print(f"artifact={artifact_path}")
    return 0


def _normalize_batch_output(
    parsed,
    per_case,
    shared_cards,
    case_key_to_case_id,
    field_key_to_card,
    target_key_to_card,
):
    """Rehydrate catalog metadata omitted from Qwen's compact output."""
    normalized_cases = []
    screen = next(
        (card for card in shared_cards.values() if card.get("record_type") == "screen"),
        None,
    )
    if screen is None:
        raise ValueError("Retrieved context is missing its screen card.")
    screen_id = str((screen.get("screen") or {}).get("id") or "")
    if not screen_id:
        raise ValueError("Retrieved screen card is missing its screen ID.")

    for result in parsed.cases:
        case_id = case_key_to_case_id.get(result.case_id)
        if case_id is None:
            raise ValueError(f"Model returned unknown case key: {result.case_id}")
        case_info = per_case.get(case_id)
        if case_info is None:
            raise ValueError(f"Local case map is missing: {case_id}")
        case_cards = [
            shared_cards[card_id]
            for card_id in case_info["allowed_card_ids"]
            if card_id in shared_cards
        ]
        section_cards = {
            tuple(card.get("section_path") or ()): card
            for card in case_cards
            if card.get("record_type") == "section"
        }
        navigation_targets = []
        for path in case_info["section_paths"]:
            section = section_cards.get(tuple(path))
            if section is None:
                raise ValueError(f"Retrieved section card is missing for {path!r}")
            navigation_targets.append(
                NavigationTarget(
                    screen_id=screen_id,
                    screen_card_id=str(screen["card_id"]),
                    section_card_id=str(section["card_id"]),
                    section_path=tuple(path),
                )
            )

        action_intents = []
        for intent in result.action_intents:
            source_step_ref = case_info["step_ref"] if intent.step_ref == "1" else None
            if source_step_ref is None:
                raise ValueError(f"Model returned unknown source step key: {intent.step_ref}")
            target_ref = None
            if intent.target_key is not None:
                target_card = target_key_to_card.get(intent.target_key)
                if target_card is None:
                    raise ValueError(f"Model returned unknown action target key: {intent.target_key}")
                target_ref = str(target_card.get("card_id") or "")
            action_intents.append(
                ActionIntent(
                    kind=intent.kind,
                    target_ref=target_ref,
                    target_text=intent.target_text,
                    source_step_ref=source_step_ref,
                )
            )

        source_text = case_info["test_text"]
        values = []
        allowed_card_ids = set(case_info["allowed_card_ids"])
        for field_key, value in result.field_values.items():
            card = field_key_to_card.get(field_key)
            if card is None:
                raise ValueError(f"Model returned unknown field key: {field_key}")
            if value in (None, ""):
                # Empty values mean leave the control untouched; preserve the
                # exact model response in the raw artifact for auditability.
                continue
            field_ref = str(card.get("card_id") or "")
            if field_ref not in allowed_card_ids:
                # Preserve the unexpected field reference so the validator
                # reports it as outside this case's retrieved context.
                label = "<unknown field>"
                card = {}
            else:
                label = str(card.get("label") or "")
            control_type = str(card.get("control_type") or "").casefold()
            option_mode = card.get("option_mode")
            option_resolution = card.get("option_resolution") or {}
            value_mode = (
                "runtime_search"
                if control_type in {"dropdown", "select", "combobox", "mat-select"}
                and (
                    option_mode == "runtime_search"
                    or option_resolution.get("requires_runtime_lookup") is True
                )
                else "direct"
            )
            provenance = "protocol_explicit" if isinstance(value, str) and value and value in source_text else "qwen_synthetic"
            values.append(
                GeneratedFieldValue(
                    field_ref=field_ref,
                    field_label=label,
                    value=value,
                    value_mode=value_mode,
                    provenance=provenance,
                    source_step_ref=case_info["step_ref"],
                )
            )

        normalized_cases.append(
            {
                "case_id": case_id,
                "status": "ready",
                "navigation_targets": navigation_targets,
                "action_intents": action_intents,
                "field_values": values,
                "unresolved": [],
            }
        )
    return BatchDataGenerationOutput.model_validate({"cases": normalized_cases})


if __name__ == "__main__":
    raise SystemExit(main())
