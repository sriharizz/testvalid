from __future__ import annotations

from typing import Literal

from pydantic import Field, field_validator, model_validator

from backend.app.domain.protocol import StrictModel


GenerationStatus = Literal["ready", "needs_review", "blocked"]
GeneratedValueProvenance = Literal[
    "protocol_explicit",
    "qwen_synthetic",
    "intentionally_blank",
]
ValueMode = Literal["direct", "runtime_search"]
ActionIntentKind = Literal["navigate_screen", "open_section", "fill_section", "click_control"]


class GenerationStep(StrictModel):
    step_ref: str
    original_text: str
    source_refs: list[str] = Field(default_factory=list)
    excluded_from_model: bool = False
    exclusion_reason: str | None = None

    @model_validator(mode="after")
    def validate_exclusion(self) -> GenerationStep:
        if self.excluded_from_model and not self.exclusion_reason:
            raise ValueError("Excluded source text requires an explicit reason.")
        if not self.excluded_from_model and self.exclusion_reason is not None:
            raise ValueError("exclusion_reason is only valid for excluded source text.")
        return self


class GenerationInput(StrictModel):
    protocol_id: str
    source_case_identifier_as_stated: str | None = None
    application: str
    environment: str
    scenario_ref: str
    title: str | None = None
    steps: list[GenerationStep]
    source_status: Literal["pass", "needs_review", "blocked"] = "pass"
    source_ambiguities: list[str] = Field(default_factory=list)
    ui_context_cards: list[dict[str, object]] = Field(default_factory=list)
    section_fill_paths: list[list[str]] = Field(default_factory=list)
    sensitive_content_present: bool = False

    @model_validator(mode="after")
    def unique_steps(self) -> GenerationInput:
        refs = [step.step_ref for step in self.steps]
        if len(set(refs)) != len(refs):
            raise ValueError("step_ref values must be unique within a generation request.")
        return self


class NavigationTarget(StrictModel):
    screen_id: str
    screen_card_id: str
    section_card_id: str | None = None
    section_path: tuple[str, ...] = ()


class ActionIntent(StrictModel):
    """Source-grounded intent for the compiler; never executable browser code."""

    kind: ActionIntentKind
    target_ref: str | None = None
    target_text: str | None = None
    source_step_ref: str


class GeneratedFieldValue(StrictModel):
    field_ref: str
    field_label: str
    value: str | bool | None
    value_mode: ValueMode = "direct"
    provenance: GeneratedValueProvenance
    source_step_ref: str

    @field_validator("value_mode", mode="before")
    @classmethod
    def normalize_value_mode(cls, value: object) -> object:
        # Accept common model wording at the boundary, while keeping one
        # canonical value for the rest of the application.
        return {"static": "direct", "search": "runtime_search"}.get(value, value) if isinstance(value, str) else value

    @field_validator("provenance", mode="before")
    @classmethod
    def normalize_provenance(cls, value: object) -> object:
        return {"synthetic": "qwen_synthetic", "explicit": "protocol_explicit", "blank": "intentionally_blank"}.get(value, value) if isinstance(value, str) else value

    @model_validator(mode="after")
    def validate_value(self) -> GeneratedFieldValue:
        if self.provenance == "intentionally_blank":
            if self.value not in (None, ""):
                raise ValueError("intentionally_blank values must be empty.")
        elif self.value in (None, ""):
            raise ValueError("Nonblank provenance requires an explicit value.")
        if self.value_mode == "runtime_search" and not isinstance(self.value, str):
            raise ValueError("runtime_search values must be text search terms.")
        return self


class DataGenerationOutput(StrictModel):
    status: GenerationStatus
    navigation_targets: list[NavigationTarget] = Field(default_factory=list)
    action_intents: list[ActionIntent] = Field(default_factory=list)
    field_values: list[GeneratedFieldValue] = Field(default_factory=list)
    unresolved: list[str] = Field(default_factory=list)

    @field_validator("status", mode="before")
    @classmethod
    def normalize_status(cls, value: object) -> object:
        return {"success": "ready"}.get(value, value) if isinstance(value, str) else value


class CaseGenerationOutput(StrictModel):
    case_id: str
    status: GenerationStatus
    navigation_targets: list[NavigationTarget] = Field(default_factory=list)
    action_intents: list[ActionIntent] = Field(default_factory=list)
    field_values: list[GeneratedFieldValue] = Field(default_factory=list)
    unresolved: list[str] = Field(default_factory=list)

    @field_validator("status", mode="before")
    @classmethod
    def normalize_status(cls, value: object) -> object:
        return {"success": "ready"}.get(value, value) if isinstance(value, str) else value


class BatchDataGenerationOutput(StrictModel):
    cases: list[CaseGenerationOutput]


class CompactActionIntent(StrictModel):
    kind: ActionIntentKind
    target_key: str | None = None
    target_text: str | None = None
    step_ref: str

    @model_validator(mode="after")
    def validate_target_shape(self) -> CompactActionIntent:
        if self.kind == "click_control":
            if not self.target_text or self.target_key is not None:
                raise ValueError("click_control requires target_text only.")
        elif not self.target_key or self.target_text is not None:
            raise ValueError("Navigation and section intents require target_key only.")
        return self


class CompactCaseDataOutput(StrictModel):
    """Token-light model response; catalog metadata is restored locally."""

    case_id: str
    action_intents: list[CompactActionIntent] = Field(default_factory=list)
    field_values: dict[str, str | bool | None] = Field(default_factory=dict)


class CompactBatchDataGenerationOutput(StrictModel):
    cases: list[CompactCaseDataOutput]


class CompactGeneratedValue(StrictModel):
    field_key: str
    value: str | bool | None
    source_step_ref: str


class CompactDataGenerationOutput(StrictModel):
    """Compact Qwen response hydrated with catalog metadata by Python."""

    field_values: list[CompactGeneratedValue] = Field(default_factory=list)
    action_intents: list[CompactActionIntent] = Field(default_factory=list)


class GenerationValidationIssue(StrictModel):
    code: str
    description: str
    field_ref: str | None = None
    source_ref: str | None = None


class GenerationValidationReport(StrictModel):
    status: GenerationStatus
    issues: list[GenerationValidationIssue] = Field(default_factory=list)


class TokenUsage(StrictModel):
    prompt_tokens: int | None = Field(default=None, ge=0)
    completion_tokens: int | None = Field(default=None, ge=0)
    total_tokens: int | None = Field(default=None, ge=0)


class DataGenerationEnvelope(StrictModel):
    output: DataGenerationOutput
    validation: GenerationValidationReport
    provider: str
    model_name: str
    prompt_version: str
    catalog_snapshot_id: str | None = None
    retrieved_card_ids: list[str] = Field(default_factory=list)
    retrieval_selection_mode: str | None = None
    selected_section_paths: list[list[str]] = Field(default_factory=list)
    token_usage: TokenUsage = Field(default_factory=TokenUsage)
    preflight_prompt_tokens: int | None = Field(default=None, ge=0)
    token_measurement: Literal[
        "preflight_and_provider",
        "provider_reported_only",
        "unavailable",
    ] = "unavailable"
