from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from pathlib import Path
from backend.app.domain.ui_catalog import (
    CATALOG_SCHEMA_VERSION,
    CatalogScope,
    CatalogSnapshot,
)


class CatalogIntegrityError(ValueError):
    pass


class CatalogNotFoundError(FileNotFoundError):
    pass


def make_snapshot_id(
    catalog_sha256: str,
    manifest_sha256: str | None,
    scope: CatalogScope,
) -> str:
    scope_bytes = json.dumps(scope.to_dict(), ensure_ascii=False, sort_keys=True).encode("utf-8")
    material = (
        f"{catalog_sha256}:{manifest_sha256 or ''}:".encode("ascii")
        + scope_bytes
    )
    return hashlib.sha256(material).hexdigest()


class JsonCatalogRepository:
    """Append-only, filesystem-backed catalog snapshots with source byte preservation."""

    def __init__(self, root: Path | str) -> None:
        self.root = Path(root).resolve()

    def snapshot_path(self, snapshot: CatalogSnapshot) -> Path:
        return (
            self.root
            / _path_component(snapshot.scope.application)
            / _path_component(snapshot.scope.environment)
            / _path_component(snapshot.catalog_version)
            / _validate_snapshot_id(snapshot.snapshot_id)[:24]
        )

    def save(self, snapshot: CatalogSnapshot) -> Path:
        destination = self.snapshot_path(snapshot)
        destination.mkdir(parents=True, exist_ok=True)
        source_path = destination / "source_catalog.json"
        index_path = destination / "index.json"
        manifest_path = destination / "discovery_manifest.json"

        self._write_or_check(source_path, snapshot.source_catalog_bytes)
        if snapshot.manifest_bytes is not None:
            self._write_or_check(manifest_path, snapshot.manifest_bytes)
        elif manifest_path.exists():
            raise CatalogIntegrityError("Snapshot identity conflicts with a stored manifest.")
        index_bytes = (
            json.dumps(snapshot.to_index_dict(), ensure_ascii=False, indent=2, sort_keys=True)
            + "\n"
        ).encode("utf-8")
        self._write_or_check(index_path, index_bytes)
        return destination

    def load(
        self,
        scope: CatalogScope,
        catalog_version: str,
        snapshot_id: str,
    ) -> CatalogSnapshot:
        directory = (
            self.root
            / _path_component(scope.application)
            / _path_component(scope.environment)
            / _path_component(catalog_version)
            / _validate_snapshot_id(snapshot_id)[:24]
        )
        index_path = directory / "index.json"
        source_path = directory / "source_catalog.json"
        manifest_path = directory / "discovery_manifest.json"
        if not index_path.is_file() or not source_path.is_file():
            raise CatalogNotFoundError(f"Catalog snapshot not found: {snapshot_id}")

        index = json.loads(index_path.read_text(encoding="utf-8"))
        if index.get("schema_version") != CATALOG_SCHEMA_VERSION:
            raise CatalogIntegrityError("Stored catalog schema version is unsupported.")
        source_bytes = source_path.read_bytes()
        manifest_bytes = manifest_path.read_bytes() if manifest_path.is_file() else None
        actual_catalog_hash = hashlib.sha256(source_bytes).hexdigest()
        actual_manifest_hash = (
            hashlib.sha256(manifest_bytes).hexdigest() if manifest_bytes is not None else None
        )
        if index.get("catalog_source_sha256") != actual_catalog_hash:
            raise CatalogIntegrityError("Stored catalog source hash does not match its bytes.")
        if index.get("manifest_source_sha256") != actual_manifest_hash:
            raise CatalogIntegrityError("Stored manifest hash does not match its bytes.")
        stored_scope = CatalogScope.from_dict(index["scope"])
        if index.get("snapshot_id") != make_snapshot_id(
            actual_catalog_hash, actual_manifest_hash, stored_scope
        ):
            raise CatalogIntegrityError("Stored snapshot identity does not match its source.")
        if stored_scope != scope or index.get("catalog_version") != catalog_version:
            raise CatalogIntegrityError("Requested scope does not match the stored snapshot.")
        return CatalogSnapshot.from_index_dict(index, source_bytes, manifest_bytes)

    def list_snapshots(self) -> list[dict[str, str]]:
        if not self.root.exists():
            return []
        snapshots: list[dict[str, str]] = []
        for index_path in self.root.glob("*/*/*/*/index.json"):
            try:
                index = json.loads(index_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            scope = CatalogScope.from_dict(index["scope"])
            snapshots.append(
                {
                    **scope.to_dict(),  # type: ignore[arg-type]
                    "catalog_version": str(index["catalog_version"]),
                    "snapshot_id": str(index["snapshot_id"]),
                }
            )
        return sorted(
            snapshots,
            key=lambda item: (
                item["application"].casefold(),
                item["environment"].casefold(),
                item["catalog_version"],
                item["snapshot_id"],
            ),
        )

    @staticmethod
    def _write_or_check(path: Path, content: bytes) -> None:
        if path.exists():
            if path.read_bytes() != content:
                raise CatalogIntegrityError(f"Immutable catalog artifact changed: {path.name}")
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        handle, temporary_name = tempfile.mkstemp(
            prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
        )
        try:
            with os.fdopen(handle, "wb") as temporary_file:
                temporary_file.write(content)
                temporary_file.flush()
                os.fsync(temporary_file.fileno())
            os.replace(temporary_name, path)
        finally:
            if os.path.exists(temporary_name):
                os.unlink(temporary_name)


def _path_component(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip()).strip(".-")
    if not cleaned:
        cleaned = "unnamed"
    suffix = hashlib.sha256(value.encode("utf-8")).hexdigest()[:8]
    return f"{cleaned[:64]}-{suffix}"


def _validate_snapshot_id(value: str) -> str:
    if not re.fullmatch(r"[a-f0-9]{64}", value):
        raise ValueError("snapshot_id must be a 64-character lowercase SHA-256 digest")
    return value
