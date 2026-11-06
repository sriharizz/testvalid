from __future__ import annotations

import hashlib
import json
import re
from dataclasses import replace
from pathlib import Path
from typing import Any

from backend.app.domain.ui_catalog import (
    CatalogRecord,
    CatalogScope,
    CatalogSnapshot,
)
from backend.app.infrastructure.catalog_repository import (
    JsonCatalogRepository,
    make_snapshot_id,
)


class CatalogImportError(ValueError):
    pass


class CatalogManager:
    def __init__(self, repository: JsonCatalogRepository) -> None:
        self.repository = repository

    def import_file(
        self,
        catalog_path: Path | str,
        manifest_path: Path | str | None = None,
        *,
        application_build: str | None = None,
        role_profile: str | None = None,
        locale: str | None = None,
    ) -> CatalogSnapshot:
        catalog_file = Path(catalog_path)
        catalog_bytes = catalog_file.read_bytes()
        try:
            catalog = json.loads(catalog_bytes.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise CatalogImportError("Catalog source must be valid UTF-8 JSON.") from error
        if not isinstance(catalog, dict):
            raise CatalogImportError("Catalog source must be a JSON object.")

        manifest_bytes: bytes | None = None
        manifest: dict[str, Any] = {}
        if manifest_path is not None:
            manifest_file = Path(manifest_path)
            manifest_bytes = manifest_file.read_bytes()
            try:
                manifest = json.loads(manifest_bytes.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as error:
                raise CatalogImportError("Discovery manifest must be valid UTF-8 JSON.") from error
            if not isinstance(manifest, dict):
                raise CatalogImportError("Discovery manifest must be a JSON object.")

        app = catalog.get("application")
        if not isinstance(app, dict):
            raise CatalogImportError("Catalog is missing application metadata.")
        application = _text(app.get("name"))
        environment = _text(app.get("environment"))
        catalog_version = _text(catalog.get("catalog_version"))
        if not application or not environment or not catalog_version:
            raise CatalogImportError(
                "Catalog must identify application, environment, and catalog_version."
            )

        scope = CatalogScope(
            application=application,
            environment=environment,
            application_build=application_build or _optional_text(
                app.get("application_build") or app.get("build")
            ),
            role_profile=role_profile or _optional_text(
                catalog.get("role_profile") or app.get("role_profile")
            ),
            locale=locale or _optional_text(catalog.get("locale") or app.get("locale")),
        )
        catalog_sha256 = hashlib.sha256(catalog_bytes).hexdigest()
        manifest_sha256 = (
            hashlib.sha256(manifest_bytes).hexdigest() if manifest_bytes is not None else None
        )
        snapshot_id = make_snapshot_id(catalog_sha256, manifest_sha256, scope)
        snapshot = CatalogSnapshot(
            snapshot_id=snapshot_id,
            catalog_version=catalog_version,
            scope=scope,
            catalog_source_sha256=catalog_sha256,
            manifest_source_sha256=manifest_sha256,
            source_name=catalog_file.name,
            records=tuple(
                replace(record, snapshot_id=snapshot_id)
                for record in _extract_records(catalog, scope, catalog_version)
            ),
            navigation_graph=dict(catalog.get("navigation", {})),
            coverage=_coverage_summary(catalog, manifest),
            option_sets=dict(catalog.get("option_sets", {})),
            source_catalog=catalog,
            source_catalog_bytes=catalog_bytes,
            manifest_bytes=manifest_bytes,
        )
        self.repository.save(snapshot)
        return snapshot

    def load(
        self,
        scope: CatalogScope,
        catalog_version: str,
        snapshot_id: str,
    ) -> CatalogSnapshot:
        return self.repository.load(scope, catalog_version, snapshot_id)


def _extract_records(
    catalog: dict[str, Any],
    scope: CatalogScope,
    catalog_version: str,
) -> list[CatalogRecord]:
    records: dict[str, CatalogRecord] = {}
    screens = catalog.get("screens", [])
    if not isinstance(screens, list):
        raise CatalogImportError("Catalog screens must be a JSON array.")
    for screen_index, screen in enumerate(screens):
        if not isinstance(screen, dict):
            continue
        screen_id = _text(screen.get("id")) or f"screen-{screen_index}"
        screen_title = _text(screen.get("name") or screen.get("page_heading")) or screen_id
        screen_path = _optional_text(screen.get("url_path"))
        default_variant = _optional_text(
            (screen.get("variants") or {}).get("selected")
            if isinstance(screen.get("variants"), dict)
            else None
        )
        screen_ref = f"/screens/{screen_index}"
        records_by_id = records
        _add_record(
            records_by_id,
            _make_record(
                scope=scope,
                catalog_version=catalog_version,
                record_type="screen",
                screen_id=screen_id,
                screen_title=screen_title,
                screen_path=screen_path,
                section_path=(),
                variant=default_variant,
                label=screen_title,
                control=None,
                source_ref=screen_ref,
                metadata={
                    "coverage_status": screen.get("coverage_status"),
                    "lifecycle_status": "candidate",
                    "source_observation_status": "observed",
                },
            ),
        )

        top_level_fields = screen.get("top_level_fields", [])
        if isinstance(top_level_fields, list):
            for field_index, control in enumerate(top_level_fields):
                if isinstance(control, dict):
                    _add_control(
                        records_by_id,
                        control=control,
                        scope=scope,
                        catalog_version=catalog_version,
                        screen_id=screen_id,
                        screen_title=screen_title,
                        screen_path=screen_path,
                        section_path=(),
                        variant=default_variant,
                        source_ref=f"{screen_ref}/top_level_fields/{field_index}",
                    )

        for section_index, section in enumerate(screen.get("sections", [])):
            if isinstance(section, dict):
                _walk_section(
                    records_by_id,
                    section=section,
                    scope=scope,
                    catalog_version=catalog_version,
                    screen_id=screen_id,
                    screen_title=screen_title,
                    screen_path=screen_path,
                    parent_path=(),
                    variant=default_variant,
                    source_ref=f"{screen_ref}/sections/{section_index}",
                )

        variant_maps = screen.get("variant_dropdown_maps", [])
        if isinstance(variant_maps, list):
            for map_index, variant_map in enumerate(variant_maps):
                if not isinstance(variant_map, dict):
                    continue
                variant = _optional_text(variant_map.get("variant"))
                for field_index, control in enumerate(variant_map.get("fields", [])):
                    if not isinstance(control, dict):
                        continue
                    section_name = _optional_text(control.get("section"))
                    section_path = _section_names(section_name)
                    _add_control(
                        records_by_id,
                        control=control,
                        scope=scope,
                        catalog_version=catalog_version,
                        screen_id=screen_id,
                        screen_title=screen_title,
                        screen_path=screen_path,
                        section_path=section_path,
                        variant=variant,
                        source_ref=(
                            f"{screen_ref}/variant_dropdown_maps/{map_index}/fields/{field_index}"
                        ),
                    )

    return sorted(
        records.values(),
        key=lambda item: (
            item.screen_title.casefold(),
            item.section_path,
            item.variant or "",
            item.label.casefold(),
            item.record_type,
            item.record_id,
        ),
    )


def _walk_section(
    records: dict[str, CatalogRecord],
    *,
    section: dict[str, Any],
    scope: CatalogScope,
    catalog_version: str,
    screen_id: str,
    screen_title: str,
    screen_path: str | None,
    parent_path: tuple[str, ...],
    variant: str | None,
    source_ref: str,
) -> None:
    name = _optional_text(section.get("name") or section.get("title"))
    current_path = parent_path + ((name,) if name else ())
    if name:
        section_ref = _make_record(
            scope=scope,
            catalog_version=catalog_version,
            record_type="section",
            screen_id=screen_id,
            screen_title=screen_title,
            screen_path=screen_path,
            section_path=current_path,
            variant=variant,
            label=name,
            control=None,
            source_ref=source_ref,
            metadata={
                "section_id": section.get("id"),
                "lifecycle_status": "candidate",
                "source_observation_status": "observed",
            },
        )
        _add_record(records, section_ref)

    for key in ("fields", "controls"):
        controls = section.get(key, [])
        if not isinstance(controls, list):
            continue
        for index, control in enumerate(controls):
            if isinstance(control, dict):
                _add_control(
                    records,
                    control=control,
                    scope=scope,
                    catalog_version=catalog_version,
                    screen_id=screen_id,
                    screen_title=screen_title,
                    screen_path=screen_path,
                    section_path=current_path,
                    variant=variant,
                    source_ref=f"{source_ref}/{key}/{index}",
                )

    for collection_name in ("sections", "subsections"):
        children = section.get(collection_name, [])
        if not isinstance(children, list):
            continue
        for index, child in enumerate(children):
            if isinstance(child, dict):
                _walk_section(
                    records,
                    section=child,
                    scope=scope,
                    catalog_version=catalog_version,
                    screen_id=screen_id,
                    screen_title=screen_title,
                    screen_path=screen_path,
                    parent_path=current_path,
                    variant=variant,
                    source_ref=f"{source_ref}/{collection_name}/{index}",
                )


def _add_control(
    records: dict[str, CatalogRecord],
    *,
    control: dict[str, Any],
    scope: CatalogScope,
    catalog_version: str,
    screen_id: str,
    screen_title: str,
    screen_path: str | None,
    section_path: tuple[str, ...],
    variant: str | None,
    source_ref: str,
) -> None:
    label = _optional_text(control.get("label") or control.get("accessible_name"))
    kind = _optional_text(control.get("kind") or control.get("control_type"))
    if not label or not kind:
        return
    metadata_keys = (
        "placeholder",
        "searchable",
        "search_input_label",
        "visible_option_count",
        "inventory_status",
        "values_embedded",
        "locator_recipe",
        "metadata_status",
        "discovery_status",
    )
    metadata = {key: control[key] for key in metadata_keys if key in control}
    selection_strategy = control.get("selection_strategy")
    if (
        "search_input_label" not in metadata
        and isinstance(selection_strategy, dict)
        and isinstance(selection_strategy.get("search_input_label"), str)
    ):
        metadata["search_input_label"] = selection_strategy["search_input_label"]
    metadata["source_control_id"] = _optional_text(control.get("id"))
    metadata["lifecycle_status"] = "candidate"
    metadata["source_observation_status"] = "observed"
    metadata["status_reason"] = (
        "Catalog mapping imported from browser observations; deterministic locator "
        "uniqueness and behavior have not been validated."
    )
    metadata["locator_recipe_status"] = (
        "recorded" if control.get("locator_recipe") else "not_recorded"
    )
    _add_record(
        records,
        _make_record(
            scope=scope,
            catalog_version=catalog_version,
            record_type="control",
            screen_id=screen_id,
            screen_title=screen_title,
            screen_path=screen_path,
            section_path=section_path,
            variant=variant,
            label=label,
            control=control,
            source_ref=source_ref,
            metadata=metadata,
        ),
    )


def _make_record(
    *,
    scope: CatalogScope,
    catalog_version: str,
    record_type: str,
    screen_id: str,
    screen_title: str,
    screen_path: str | None,
    section_path: tuple[str, ...],
    variant: str | None,
    label: str,
    control: dict[str, Any] | None,
    source_ref: str,
    metadata: dict[str, Any],
) -> CatalogRecord:
    control_kind = (
        _optional_text(control.get("kind") or control.get("control_type"))
        if control is not None
        else None
    )
    option_set_ref = (
        _optional_text(control.get("option_set_ref")) if control is not None else None
    )
    required = (
        control.get("required_marker_observed") if control is not None else None
    )
    enabled = control.get("enabled") if control is not None else None
    identity = "\x1f".join(
        (
            scope.application.casefold(),
            scope.environment.casefold(),
            (scope.application_build or "").casefold(),
            (scope.role_profile or "").casefold(),
            (scope.locale or "").casefold(),
            screen_id.casefold(),
            "/".join(section_path).casefold(),
            (variant or "").casefold(),
            record_type,
            control_kind or "",
            label.casefold(),
            str(control.get("id") or "") if control is not None else "",
        )
    )
    record_id = "ui-" + hashlib.sha256(identity.encode("utf-8")).hexdigest()[:24]
    searchable_text = " ".join(
        part
        for part in (
            screen_title,
            " ".join(section_path),
            variant or "",
            label,
            control_kind or "",
            option_set_ref or "",
        )
        if part
    )
    return CatalogRecord(
        record_id=record_id,
        snapshot_id="",
        record_type=record_type,
        application=scope.application,
        environment=scope.environment,
        catalog_version=catalog_version,
        application_build=scope.application_build,
        role_profile=scope.role_profile,
        locale=scope.locale,
        screen_id=screen_id,
        screen_title=screen_title,
        screen_path=screen_path,
        section_path=section_path,
        variant=variant,
        label=label,
        control_kind=control_kind,
        required=required if isinstance(required, bool) else None,
        enabled=enabled if isinstance(enabled, bool) else None,
        option_set_ref=option_set_ref,
        source_ref=source_ref,
        search_text=searchable_text,
        metadata=metadata,
    )


def _add_record(records: dict[str, CatalogRecord], record: CatalogRecord) -> None:
    existing = records.get(record.record_id)
    if existing is None:
        records[record.record_id] = record
        return
    if existing != record:
        # Preserve both observations if the same canonical identity has conflicting metadata.
        conflict_material = json.dumps(record.to_dict(), ensure_ascii=False, sort_keys=True)
        conflict_suffix = hashlib.sha256(conflict_material.encode("utf-8")).hexdigest()[:8]
        records[f"{record.record_id}-{conflict_suffix}"] = replace(
            record,
            record_id=f"{record.record_id}-{conflict_suffix}",
            metadata={**record.metadata, "identity_conflict": True},
        )


def _coverage_summary(
    catalog: dict[str, Any], manifest: dict[str, Any]
) -> dict[str, Any]:
    screen_statuses = [
        {
            "screen_id": screen.get("id"),
            "screen_title": screen.get("name"),
            "status": screen.get("coverage_status"),
            "variants": screen.get("variants"),
        }
        for screen in catalog.get("screens", [])
        if isinstance(screen, dict)
    ]
    return {
        "manifest_present": bool(manifest),
        "manifest_scope": manifest.get("scope"),
        "manifest_pages": manifest.get("pages", []),
        "manifest_acceptance": manifest.get("acceptance", {}),
        "screen_statuses": screen_statuses,
    }


def _section_names(value: str | None) -> tuple[str, ...]:
    if not value:
        return ()
    return tuple(part.strip() for part in re.split(r"\s*>\s*", value) if part.strip())


def _text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _optional_text(value: Any) -> str | None:
    text = _text(value)
    return text or None
