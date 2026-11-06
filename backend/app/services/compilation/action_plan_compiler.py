from __future__ import annotations

from typing import Literal

from pydantic import Field

from backend.app.domain.protocol import StrictModel
from backend.app.domain.ui_catalog import CatalogRecord, CatalogSnapshot
from backend.app.schemas.data_generation import DataGenerationEnvelope


OperationKind = Literal[
    "navigate_screen",
    "open_section",
    "fill_field",
    "click_control",
    "capture_screenshot",
]

_MUTATING_LABELS = {
    "save",
    "submit",
    "save and submit",
    "delete",
    "approve",
    "sign",
    "send",
    "register",
    "reset",
}


class PlanOperation(StrictModel):
    kind: OperationKind
    source_step_ref: str
    target_ref: str | None = None
    target_label: str | None = None
    screen_path: tuple[str, ...] = ()
    value: str | bool | None = None
    value_mode: Literal["direct", "runtime_search"] = "direct"
    control_kind: str | None = None
    search_input_label: str | None = None
    mutation: bool = False


class CompiledActionPlan(StrictModel):
    application: str
    environment: str
    catalog_snapshot_id: str
    screen_id: str
    screen_title: str
    navigation_path: tuple[str, ...]
    operations: list[PlanOperation] = Field(min_length=1)


class ActionPlanCompilationError(ValueError):
    pass


class ActionPlanCompiler:
    """Resolve Qwen's compact intents to version-scoped catalog operations."""

    def compile(
        self,
        envelope: DataGenerationEnvelope,
        snapshot: CatalogSnapshot,
    ) -> CompiledActionPlan:
        if envelope.validation.status != "ready" or envelope.output.status != "ready":
            raise ActionPlanCompilationError("Qwen data is not validated and ready for compilation.")
        if envelope.catalog_snapshot_id != snapshot.snapshot_id:
            raise ActionPlanCompilationError("Generation output and UI catalog snapshot do not match.")
        if snapshot.scope.environment.casefold() in {"production", "prod"}:
            raise ActionPlanCompilationError("Production execution is blocked by the runner preflight.")
        retrieved = set(envelope.retrieved_card_ids)
        records = {record.record_id: record for record in snapshot.records}
        actions = envelope.output.action_intents
        screen_actions = [action for action in actions if action.kind == "navigate_screen"]
        if len(screen_actions) != 1:
            raise ActionPlanCompilationError("Exactly one retrieved screen navigation intent is required.")

        screen_action = screen_actions[0]
        screen = _require_record(
            screen_action.target_ref,
            records,
            retrieved,
            expected_type="screen",
        )
        navigation_path = _navigation_breadcrumb(snapshot, screen)
        if not navigation_path:
            raise ActionPlanCompilationError("The catalog has no observed navigation breadcrumb for this screen.")

        section_actions = [
            action
            for action in actions
            if action.kind in {"open_section", "fill_section"}
        ]
        sections: dict[str, CatalogRecord] = {}
        for action in section_actions:
            section = _require_record(
                action.target_ref,
                records,
                retrieved,
                expected_type="section",
            )
            if section.screen_id != screen.screen_id:
                raise ActionPlanCompilationError("Section target belongs to a different screen.")
            sections[section.record_id] = section

        control_values: dict[str, object] = {}
        for value in envelope.output.field_values:
            if value.field_ref not in retrieved:
                raise ActionPlanCompilationError("A generated field is outside the retrieved UI context.")
            control = _require_record(
                value.field_ref,
                records,
                retrieved,
                expected_type="control",
            )
            if control.enabled is False or control.screen_id != screen.screen_id:
                raise ActionPlanCompilationError("Generated field is disabled or belongs to another screen.")
            if value.field_ref in control_values:
                raise ActionPlanCompilationError("Generated field has duplicate values.")
            control_values[value.field_ref] = (value, control)

        operations: list[PlanOperation] = [
            PlanOperation(
                kind="navigate_screen",
                source_step_ref=screen_action.source_step_ref,
                target_ref=screen.record_id,
                target_label=screen.screen_title,
                screen_path=navigation_path,
            ),
            PlanOperation(
                kind="capture_screenshot",
                source_step_ref=screen_action.source_step_ref,
                target_ref=screen.record_id,
                target_label=f"screen:{screen.screen_title}",
            ),
        ]
        consumed_fields: set[str] = set()

        for action in actions:
            if action.kind == "navigate_screen":
                continue
            if action.kind == "open_section":
                section = sections[action.target_ref or ""]
                operations.append(
                    PlanOperation(
                        kind="open_section",
                        source_step_ref=action.source_step_ref,
                        target_ref=section.record_id,
                        target_label=section.label,
                        screen_path=section.section_path,
                    )
                )
            elif action.kind == "fill_section":
                section = sections[action.target_ref or ""]
                fields = [
                    (ref, pair)
                    for ref, pair in control_values.items()
                    if pair[1].section_path == section.section_path
                ]
                if not fields:
                    raise ActionPlanCompilationError(
                        f"No validated values were returned for section {section.label!r}."
                    )
                for field_ref, (value, control) in fields:
                    operations.append(
                        PlanOperation(
                            kind="fill_field",
                            source_step_ref=value.source_step_ref,
                            target_ref=field_ref,
                            target_label=control.label,
                            screen_path=control.section_path,
                            value=value.value,
                            value_mode=value.value_mode,
                            control_kind=control.control_kind,
                            search_input_label=(
                                control.metadata.get("search_input_label")
                                if isinstance(control.metadata.get("search_input_label"), str)
                                else None
                            ),
                        )
                    )
                    consumed_fields.add(field_ref)
                operations.append(
                    PlanOperation(
                        kind="capture_screenshot",
                        source_step_ref=action.source_step_ref,
                        target_ref=section.record_id,
                        target_label=f"filled:{section.label}",
                    )
                )
            elif action.kind == "click_control":
                label = action.target_text or ""
                operations.append(
                    PlanOperation(
                        kind="click_control",
                        source_step_ref=action.source_step_ref,
                        target_label=label,
                        mutation=_is_mutating_label(label),
                    )
                )
                operations.append(
                    PlanOperation(
                        kind="capture_screenshot",
                        source_step_ref=action.source_step_ref,
                        target_label=f"after-click:{label}",
                    )
                )

        if consumed_fields != set(control_values):
            raise ActionPlanCompilationError("Some generated fields are not covered by a fill_section intent.")

        return CompiledActionPlan(
            application=snapshot.scope.application,
            environment=snapshot.scope.environment,
            catalog_snapshot_id=snapshot.snapshot_id,
            screen_id=screen.screen_id,
            screen_title=screen.screen_title,
            navigation_path=navigation_path,
            operations=operations,
        )


def _require_record(
    record_id: str | None,
    records: dict[str, CatalogRecord],
    retrieved: set[str],
    *,
    expected_type: str,
) -> CatalogRecord:
    if not record_id or record_id not in retrieved:
        raise ActionPlanCompilationError("Action target is not in the retrieved catalog context.")
    record = records.get(record_id)
    if record is None or record.record_type != expected_type:
        raise ActionPlanCompilationError(f"Action target is not a retrieved {expected_type} record.")
    return record


def _navigation_breadcrumb(snapshot: CatalogSnapshot, screen_record: CatalogRecord) -> tuple[str, ...]:
    for screen in snapshot.source_catalog.get("screens", []):
        if isinstance(screen, dict) and str(screen.get("id")) == screen_record.screen_id:
            breadcrumb = screen.get("breadcrumb")
            if isinstance(breadcrumb, str):
                path = tuple(part.strip() for part in breadcrumb.split(">") if part.strip())
                if path:
                    return path
            module = screen.get("module")
            title = screen.get("name") or screen.get("page_heading")
            return tuple(str(item) for item in (module, title) if item)
    return ()


def _is_mutating_label(label: str) -> bool:
    normalized = " ".join(label.casefold().split())
    return normalized in _MUTATING_LABELS
