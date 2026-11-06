from __future__ import annotations

import argparse
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from dotenv import load_dotenv

from backend.app.infrastructure.catalog_repository import JsonCatalogRepository
from backend.app.infrastructure.qwen_client import QwenClient, QwenSettings
from backend.app.schemas.data_generation import GenerationInput, GenerationStep
from backend.app.services.catalog.catalog_manager import CatalogManager
from backend.app.services.data_generation.generator import QwenDataGenerator
from backend.app.services.retrieval.section_first import SectionFirstRetriever
from backend.app.services.retrieval.ui_mini_rag import RetrievalScope, UIMiniRAG


ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
CATALOG = ROOT / "catalog" / "ui" / "application_catalog.json"
MANIFEST = ROOT / "catalog" / "ui" / "discovery_manifest.json"
ARTIFACTS = BACKEND / "artifacts" / "qwen_evaluations"


HUMAN_CASES = (
    (
        "human-01-reporter-required",
        "In Reporter, generate fictional values for enabled required fields only.",
    ),
    (
        "human-02-reporter-contact",
        "For Reporter, create fictional City(English), Email Address, and Country Code values.",
    ),
    (
        "human-03-patient-details",
        "In Patient, generate a fictional First Name(English), Last Name(English), and Date of Birth.",
    ),
    (
        "human-04-general-info",
        "In General Info, generate a Company Receipt Date and select valid values for Case Classifications Code and Case Intake Source Code.",
    ),
    (
        "human-05-seriousness",
        "In Seriousness, generate fictional values for Death and Hospitalization.",
    ),
)


class CapturingClient:
    """Capture the exact sanitized request body and raw completion for local evaluation."""

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
                    "name": "data_generation_output",
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
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--case-id",
        action="append",
        help="Run only this case ID; repeat to select multiple cases.",
    )
    parser.add_argument(
        "--artifact",
        type=Path,
        help="Append traces to an existing evaluation JSONL file.",
    )
    args = parser.parse_args()
    load_dotenv(BACKEND / ".env")
    settings = QwenSettings.from_environment()
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    artifact_path = args.artifact or ARTIFACTS / f"phase4-human-five-{timestamp}.jsonl"
    selected_cases = [
        item for item in HUMAN_CASES
        if not args.case_id or item[0] in args.case_id
    ]
    unknown_case_ids = set(args.case_id or ()) - {item[0] for item in HUMAN_CASES}
    if unknown_case_ids:
        parser.error(f"Unknown case ID(s): {', '.join(sorted(unknown_case_ids))}")
    tokens_per_minute = int(os.getenv("EVAL_TOKEN_RATE_LIMIT_PER_MINUTE", "8000"))

    with TemporaryDirectory(prefix="qwen-eval-catalog-") as temp_dir:
        snapshot = CatalogManager(
            JsonCatalogRepository(Path(temp_dir) / "catalog")
        ).import_file(CATALOG, MANIFEST)
        mini_rag = UIMiniRAG([snapshot])
        scope = RetrievalScope(
            application=snapshot.scope.application,
            environment=snapshot.scope.environment,
            catalog_version=snapshot.catalog_version,
            snapshot_id=snapshot.snapshot_id,
            screen_id="manual_case_registration",
            variant="Adverse Event",
        )

        with QwenClient(settings) as client, artifact_path.open("a", encoding="utf-8") as output_file:
            capture = CapturingClient(client)
            generator = QwenDataGenerator(
                capture,
                SectionFirstRetriever(mini_rag),
                allow_provider_reported_only=True,
            )

            for index, (case_id, source_text) in enumerate(selected_cases):
                request = GenerationInput(
                    protocol_id="synthetic-human-evaluation",
                    source_case_identifier_as_stated=case_id,
                    application=snapshot.scope.application,
                    environment=snapshot.scope.environment,
                    scenario_ref=case_id,
                    title=case_id,
                    steps=[
                        GenerationStep(
                            step_ref=f"{case_id}:step:1",
                            original_text=source_text,
                        )
                    ],
                )
                capture.request_payload = None
                capture.raw_completion = None
                envelope = None
                error = None
                try:
                    envelope = generator.generate(request, scope)
                except Exception as exc:  # errors are sanitized by QwenClient
                    error = f"{type(exc).__name__}: {exc}"

                record = {
                    "case_id": case_id,
                    "source_input": source_text,
                    "provider": settings.provider,
                    "model": settings.model_name,
                    "prompt_version": "synthetic-field-data-v1",
                    "configured_max_completion_tokens": settings.max_completion_tokens,
                    "evaluation_rate_limit_tokens_per_minute": tokens_per_minute,
                    "retrieved_request_body": capture.request_payload,
                    "raw_completion": capture.raw_completion,
                    "validated_output": envelope.output.model_dump(mode="json") if envelope else None,
                    "validation": envelope.validation.model_dump(mode="json") if envelope else None,
                    "retrieved_card_ids": envelope.retrieved_card_ids if envelope else [],
                    "selected_section_paths": envelope.selected_section_paths if envelope else [],
                    "token_usage": envelope.token_usage.model_dump(mode="json") if envelope else None,
                    "token_measurement": envelope.token_measurement if envelope else "unavailable",
                    "error": error,
                }
                output_file.write(json.dumps(record, ensure_ascii=False) + "\n")
                output_file.flush()
                status = envelope.validation.status if envelope else "error"
                total = envelope.token_usage.total_tokens if envelope else None
                print(f"{case_id}: status={status}; provider_tokens={total}; artifact_saved=true")

                if index < len(selected_cases) - 1:
                    used_tokens = (
                        envelope.token_usage.total_tokens
                        if envelope and envelope.token_usage.total_tokens is not None
                        else 0
                    )
                    wait_seconds = max(10, int(60 * used_tokens / tokens_per_minute) + 3)
                    if error and "HTTP 429" in error:
                        wait_seconds = 60
                    time.sleep(wait_seconds)

    print(f"Evaluation artifact: {artifact_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
