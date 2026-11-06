from __future__ import annotations

import json
from typing import Literal

from backend.app.domain.protocol import CanonicalProtocol, TestCase
from backend.app.schemas.data_generation import GenerationInput, GenerationStep


def generation_input_from_case(
    protocol: CanonicalProtocol,
    case: TestCase,
    *,
    application: str,
    environment: str,
    source_status: Literal["pass", "needs_review", "blocked"] = "pass",
    source_ambiguities: list[str] | None = None,
    excluded_step_sequences: dict[int, str] | None = None,
) -> GenerationInput:
    """Adapt canonical source steps verbatim for field-data generation."""
    exclusions = excluded_step_sequences or {}
    steps = [
        GenerationStep(
            step_ref=f"{case.internal_id}:step:{step.sequence}",
            original_text=step.original_text,
            source_refs=[
                json.dumps(
                    ref.model_dump(mode="json", exclude_none=True),
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                )
                for ref in step.source_refs
            ],
            excluded_from_model=step.sequence in exclusions,
            exclusion_reason=exclusions.get(step.sequence),
        )
        for step in case.steps
    ]
    ambiguities = list(source_ambiguities or [])
    ambiguities.extend(item.description for item in case.ambiguities)
    ambiguities.extend(item.description for item in protocol.identity_conflicts)
    document = protocol.document
    return GenerationInput(
        protocol_id=document.protocol_identifier_as_stated or document.document_id,
        source_case_identifier_as_stated=case.stated_identifier,
        application=application,
        environment=environment,
        scenario_ref=case.internal_id,
        title=case.title_original,
        steps=steps,
        source_status=source_status,
        source_ambiguities=ambiguities,
    )
