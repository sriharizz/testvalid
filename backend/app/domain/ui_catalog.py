from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


CATALOG_SCHEMA_VERSION = "1.0.0"


@dataclass(frozen=True)
class CatalogScope:
    application: str
    environment: str
    application_build: str | None = None
    role_profile: str | None = None
    locale: str | None = None

    def to_dict(self) -> dict[str, str | None]:
        return {
            "application": self.application,
            "environment": self.environment,
            "application_build": self.application_build,
            "role_profile": self.role_profile,
            "locale": self.locale,
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> CatalogScope:
        return cls(
            application=str(value["application"]),
            environment=str(value["environment"]),
            application_build=_optional_text(value.get("application_build")),
            role_profile=_optional_text(value.get("role_profile")),
            locale=_optional_text(value.get("locale")),
        )


@dataclass(frozen=True)
class CatalogRecord:
    record_id: str
    snapshot_id: str
    record_type: str
    application: str
    environment: str
    catalog_version: str
    application_build: str | None
    role_profile: str | None
    locale: str | None
    screen_id: str
    screen_title: str
    screen_path: str | None
    section_path: tuple[str, ...]
    variant: str | None
    label: str
    control_kind: str | None
    required: bool | None
    enabled: bool | None
    option_set_ref: str | None
    source_ref: str
    search_text: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "record_id": self.record_id,
            "snapshot_id": self.snapshot_id,
            "record_type": self.record_type,
            "application": self.application,
            "environment": self.environment,
            "catalog_version": self.catalog_version,
            "application_build": self.application_build,
            "role_profile": self.role_profile,
            "locale": self.locale,
            "screen_id": self.screen_id,
            "screen_title": self.screen_title,
            "screen_path": self.screen_path,
            "section_path": list(self.section_path),
            "variant": self.variant,
            "label": self.label,
            "control_kind": self.control_kind,
            "required": self.required,
            "enabled": self.enabled,
            "option_set_ref": self.option_set_ref,
            "source_ref": self.source_ref,
            "search_text": self.search_text,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> CatalogRecord:
        return cls(
            record_id=str(value["record_id"]),
            snapshot_id=str(value["snapshot_id"]),
            record_type=str(value["record_type"]),
            application=str(value["application"]),
            environment=str(value["environment"]),
            catalog_version=str(value["catalog_version"]),
            application_build=_optional_text(value.get("application_build")),
            role_profile=_optional_text(value.get("role_profile")),
            locale=_optional_text(value.get("locale")),
            screen_id=str(value["screen_id"]),
            screen_title=str(value["screen_title"]),
            screen_path=_optional_text(value.get("screen_path")),
            section_path=tuple(str(item) for item in value.get("section_path", [])),
            variant=_optional_text(value.get("variant")),
            label=str(value["label"]),
            control_kind=_optional_text(value.get("control_kind")),
            required=value.get("required"),
            enabled=value.get("enabled"),
            option_set_ref=_optional_text(value.get("option_set_ref")),
            source_ref=str(value["source_ref"]),
            search_text=str(value["search_text"]),
            metadata=dict(value.get("metadata", {})),
        )


@dataclass(frozen=True)
class CatalogSnapshot:
    snapshot_id: str
    catalog_version: str
    scope: CatalogScope
    catalog_source_sha256: str
    manifest_source_sha256: str | None
    source_name: str
    records: tuple[CatalogRecord, ...]
    navigation_graph: dict[str, Any]
    coverage: dict[str, Any]
    option_sets: dict[str, Any]
    source_catalog: dict[str, Any] = field(repr=False, compare=False)
    source_catalog_bytes: bytes = field(repr=False, compare=False)
    manifest_bytes: bytes | None = field(default=None, repr=False, compare=False)

    def to_index_dict(self) -> dict[str, Any]:
        return {
            "schema_version": CATALOG_SCHEMA_VERSION,
            "snapshot_id": self.snapshot_id,
            "catalog_version": self.catalog_version,
            "scope": self.scope.to_dict(),
            "catalog_source_sha256": self.catalog_source_sha256,
            "manifest_source_sha256": self.manifest_source_sha256,
            "source_name": self.source_name,
            "records": [record.to_dict() for record in self.records],
            "navigation_graph": self.navigation_graph,
            "coverage": self.coverage,
            "option_sets": self.option_sets,
        }

    @classmethod
    def from_index_dict(
        cls,
        value: dict[str, Any],
        source_catalog_bytes: bytes,
        manifest_bytes: bytes | None,
    ) -> CatalogSnapshot:
        import json

        return cls(
            snapshot_id=str(value["snapshot_id"]),
            catalog_version=str(value["catalog_version"]),
            scope=CatalogScope.from_dict(value["scope"]),
            catalog_source_sha256=str(value["catalog_source_sha256"]),
            manifest_source_sha256=_optional_text(value.get("manifest_source_sha256")),
            source_name=str(value["source_name"]),
            records=tuple(CatalogRecord.from_dict(item) for item in value.get("records", [])),
            navigation_graph=dict(value.get("navigation_graph", {})),
            coverage=dict(value.get("coverage", {})),
            option_sets=dict(value.get("option_sets", {})),
            source_catalog=json.loads(source_catalog_bytes.decode("utf-8")),
            source_catalog_bytes=source_catalog_bytes,
            manifest_bytes=manifest_bytes,
        )


def _optional_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
