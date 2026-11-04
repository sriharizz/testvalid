from __future__ import annotations

from typing import Literal

from pydantic import Field

from backend.app.domain.protocol import StrictModel


DiscoveryLifecycle = Literal["observed", "unsupported"]
EvidenceKind = Literal["dom_metadata", "navigation_link", "safe_interaction", "frame_metadata"]


class DiscoveryEvidence(StrictModel):
    kind: EvidenceKind
    observed_at_utc: str
    screen_url: str
    locator_recipe: str
    fact: str


class UIOptionObservation(StrictModel):
    label: str
    disabled: bool = False
    selected: bool = False


class UIControlObservation(StrictModel):
    control_id: str
    role: str | None = None
    control_type: str
    accessible_name: str | None = None
    label: str | None = None
    placeholder: str | None = None
    input_type: str | None = None
    required: bool | None = None
    required_evidence: str | None = None
    readonly: bool | None = None
    disabled: bool = False
    section_id: str | None = None
    locator_recipe: str
    lifecycle: DiscoveryLifecycle = "observed"
    options: list[UIOptionObservation] = Field(default_factory=list)
    observed_option_count: int = Field(default=0, ge=0)
    option_coverage: Literal[
        "not_applicable", "complete", "partial", "withheld_for_data_safety"
    ] = "not_applicable"
    evidence: list[DiscoveryEvidence] = Field(default_factory=list)


class UISectionObservation(StrictModel):
    section_id: str
    label: str | None = None
    role: str | None = None
    locator_recipe: str
    lifecycle: DiscoveryLifecycle = "observed"
    evidence: list[DiscoveryEvidence] = Field(default_factory=list)


class UITableObservation(StrictModel):
    table_id: str
    role: str
    headers: list[str] = Field(default_factory=list)
    visible_row_count: int = Field(ge=0)
    locator_recipe: str
    evidence: list[DiscoveryEvidence] = Field(default_factory=list)


class UIRelationshipObservation(StrictModel):
    relationship_type: Literal[
        "navigation", "containment", "reveals", "tab_controls", "dialog_trigger"
    ]
    source_id: str
    target_id: str | None = None
    target_path: str | None = None
    label: str | None = None
    status: Literal["observed", "candidate", "blocked", "unsupported"] = "observed"
    evidence: list[DiscoveryEvidence] = Field(default_factory=list)


class UIScreenObservation(StrictModel):
    screen_id: str
    url: str
    title: str | None = None
    fingerprint: str
    lifecycle: DiscoveryLifecycle = "observed"
    sections: list[UISectionObservation] = Field(default_factory=list)
    controls: list[UIControlObservation] = Field(default_factory=list)
    tables: list[UITableObservation] = Field(default_factory=list)
    relationships: list[UIRelationshipObservation] = Field(default_factory=list)
    dialog_labels: list[str] = Field(default_factory=list)
    evidence: list[DiscoveryEvidence] = Field(default_factory=list)


class DiscoveryIssue(StrictModel):
    code: str
    status: Literal["inaccessible", "not_safely_discoverable", "partial", "unsupported"]
    summary: str
    source_url: str | None = None
    evidence: list[DiscoveryEvidence] = Field(default_factory=list)


class DiscoveryCoverage(StrictModel):
    screens_observed: int = Field(ge=0)
    navigation_links_observed: int = Field(ge=0)
    navigation_links_visited: int = Field(ge=0)
    safe_interactions_explored: int = Field(ge=0)
    controls_observed: int = Field(ge=0)
    options_observed: int = Field(ge=0)
    issues: list[DiscoveryIssue] = Field(default_factory=list)


class UIDiscoveryResult(StrictModel):
    discovery_id: str
    started_at_utc: str
    completed_at_utc: str
    live_discovery: bool
    browser_channel: str
    environment_label: str
    screens: list[UIScreenObservation] = Field(default_factory=list)
    coverage: DiscoveryCoverage
