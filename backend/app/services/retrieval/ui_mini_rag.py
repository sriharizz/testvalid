from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Any, Iterable

from backend.app.domain.ui_catalog import CatalogRecord, CatalogSnapshot
from backend.app.services.retrieval.token_budget import (
    ContextBatch,
    ContextUnit,
    TokenBudgeter,
)


@dataclass(frozen=True)
class RetrievalScope:
    application: str
    environment: str
    application_build: str | None = None
    role_profile: str | None = None
    locale: str | None = None
    catalog_version: str | None = None
    snapshot_id: str | None = None
    screen_id: str | None = None
    section_path: tuple[str, ...] | None = None
    variant: str | None = None


@dataclass(frozen=True)
class ScoredRecord:
    record: CatalogRecord
    score: float
    selection_method: str = "lexical_rank"


@dataclass(frozen=True)
class OptionResolution:
    field_record_id: str
    option_set_ref: str
    status: str
    exact_value: str | None
    candidate_values: tuple[str, ...]
    full_option_count: int | None
    requires_runtime_lookup: bool
    search_input_label: str | None


@dataclass(frozen=True)
class RetrievalResult:
    status: str
    records: tuple[ScoredRecord, ...]
    option_resolutions: tuple[OptionResolution, ...]
    required_scope_dimensions: tuple[str, ...]
    duplicate_count_removed: int
    matching_scope_record_count: int


class UIMiniRAG:
    """Small CPU-only lexical retriever over scoped, structured UI catalog cards."""

    def __init__(
        self,
        snapshots: Iterable[CatalogSnapshot],
        *,
        relevance_threshold: float = 0.12,
    ) -> None:
        self.snapshots = tuple(snapshots)
        self.records = tuple(record for snapshot in self.snapshots for record in snapshot.records)
        self.relevance_threshold = relevance_threshold

    def context_units(self, result: RetrievalResult) -> tuple[ContextUnit, ...]:
        resolutions = {
            item.field_record_id: item for item in result.option_resolutions
        }
        units: list[ContextUnit] = []
        for scored in result.records:
            record = scored.record
            payload: dict[str, Any] = {
                "card_id": record.record_id,
                "record_type": record.record_type,
                "application": record.application,
                "environment": record.environment,
                "application_build": record.application_build,
                "role_profile": record.role_profile,
                "locale": record.locale,
                "catalog_version": record.catalog_version,
                "snapshot_id": record.snapshot_id,
                "screen": {
                    "id": record.screen_id,
                    "title": record.screen_title,
                    "path": record.screen_path,
                },
                "section_path": list(record.section_path),
                "variant": record.variant,
                "label": record.label,
                "control_type": record.control_kind,
                "required": record.required,
                "enabled": record.enabled,
                "option_set_ref": record.option_set_ref,
                "locator_recipe_status": record.metadata.get("locator_recipe_status"),
                "lifecycle_status": record.metadata.get("lifecycle_status", "candidate"),
                "source_ref": record.source_ref,
                "selection_method": scored.selection_method,
            }
            if scored.selection_method == "lexical_rank":
                payload["relevance_score"] = round(scored.score, 6)
            option = resolutions.get(record.record_id)
            if option is not None:
                payload["option_resolution"] = {
                    "status": option.status,
                    "exact_value": option.exact_value,
                    "candidate_values": list(option.candidate_values),
                    "full_option_count": option.full_option_count,
                    "requires_runtime_lookup": option.requires_runtime_lookup,
                    "search_input_label": option.search_input_label,
                }
            import json

            units.append(
                ContextUnit(
                    unit_id=record.record_id,
                    boundary_type="catalog_card",
                    content=json.dumps(payload, ensure_ascii=False, sort_keys=True),
                )
            )
        return tuple(units)

    def pack_context(
        self,
        result: RetrievalResult,
        budgeter: TokenBudgeter,
    ) -> tuple[ContextBatch, ...]:
        return budgeter.pack(self.context_units(result))

    def retrieve(
        self,
        query: str,
        scope: RetrievalScope,
        *,
        top_k: int = 10,
        desired_option: str | None = None,
        option_candidate_limit: int = 10,
    ) -> RetrievalResult:
        if top_k < 1 or option_candidate_limit < 1:
            raise ValueError("top_k and option_candidate_limit must be positive.")
        query = query.strip()
        if not query:
            return RetrievalResult("needs_review", (), (), (), 0, 0)

        app_env_records = [
            record
            for record in self.records
            if _same(record.application, scope.application)
            and _same(record.environment, scope.environment)
        ]
        if not app_env_records:
            return RetrievalResult("scope_mismatch", (), (), (), 0, 0)

        required_scope = self._required_scope_dimensions(app_env_records, scope)
        if required_scope:
            return RetrievalResult(
                "scope_required", (), (), required_scope, 0, len(app_env_records)
            )

        scoped_records = [
            record for record in app_env_records if _matches_scope(record, scope)
        ]
        if not scoped_records:
            return RetrievalResult("scope_mismatch", (), (), (), 0, 0)

        unique_records: dict[str, CatalogRecord] = {}
        duplicates_removed = 0
        for record in scoped_records:
            if record.record_id in unique_records:
                duplicates_removed += 1
            else:
                unique_records[record.record_id] = record
        unique = list(unique_records.values())
        scored = _rank_records(query, unique)
        relevant = [
            item for item in scored if item.score >= self.relevance_threshold
        ][:top_k]
        if not relevant:
            return RetrievalResult(
                "needs_review", (), (), (), duplicates_removed, len(scoped_records)
            )
        options = tuple(
            resolution
            for item in relevant
            if item.record.record_type == "control" and item.record.option_set_ref
            for resolution in [
                self._resolve_option(
                    item.record,
                    scope,
                    desired_option,
                    option_candidate_limit,
                )
            ]
            if resolution is not None
        )
        return RetrievalResult(
            "retrieved",
            tuple(relevant),
            options,
            (),
            duplicates_removed,
            len(scoped_records),
        )

    def retrieve_sections(
        self,
        section_paths: Iterable[tuple[str, ...]],
        scope: RetrievalScope,
        *,
        include_descendants: bool = True,
        option_candidate_limit: int = 10,
    ) -> RetrievalResult:
        """Return selected section cards and their scoped child controls.

        Section selection is explicit and structural; child expansion is bounded to the
        requested section paths and deduplicated by stable catalog record ID.
        """
        requested = tuple(
            tuple(part.strip().casefold() for part in path if part.strip())
            for path in section_paths
        )
        requested = tuple(path for path in requested if path)
        if not requested:
            return RetrievalResult("needs_review", (), (), (), 0, 0)
        if option_candidate_limit < 1:
            raise ValueError("option_candidate_limit must be positive.")

        app_env_records = [
            record
            for record in self.records
            if _same(record.application, scope.application)
            and _same(record.environment, scope.environment)
        ]
        if not app_env_records:
            return RetrievalResult("scope_mismatch", (), (), (), 0, 0)
        required_scope = self._required_scope_dimensions(app_env_records, scope)
        if required_scope:
            return RetrievalResult(
                "scope_required", (), (), required_scope, 0, len(app_env_records)
            )
        scoped_records = [record for record in app_env_records if _matches_scope(record, scope)]
        if not scoped_records:
            return RetrievalResult("scope_mismatch", (), (), (), 0, 0)

        unique: dict[str, CatalogRecord] = {}
        duplicates_removed = 0
        for record in scoped_records:
            if record.record_id in unique:
                duplicates_removed += 1
            else:
                unique[record.record_id] = record

        section_records = [record for record in unique.values() if record.record_type == "section"]
        matched_paths = {
            tuple(part.casefold() for part in record.section_path)
            for record in section_records
            if tuple(part.casefold() for part in record.section_path) in requested
        }
        if not matched_paths or matched_paths != set(requested):
            return RetrievalResult(
                "needs_review", (), (), (), duplicates_removed, len(scoped_records)
            )

        selected: dict[str, CatalogRecord] = {}
        if scope.screen_id is not None:
            for record in unique.values():
                if record.record_type == "screen" and _same(record.screen_id, scope.screen_id):
                    selected[record.record_id] = record
        for record in unique.values():
            if record.record_type == "screen":
                continue
            record_path = tuple(part.casefold() for part in record.section_path)
            for path in matched_paths:
                in_section = (
                    record_path[: len(path)] == path
                    if include_descendants
                    else record_path == path
                )
                if in_section:
                    selected[record.record_id] = record
                    break

        ordered = sorted(
            selected.values(),
            key=lambda record: (
                record.screen_title.casefold(),
                record.section_path,
                0 if record.record_type == "section" else 1,
                record.label.casefold(),
                record.record_id,
            ),
        )
        scored = tuple(
            ScoredRecord(record, 0.0, "section_expansion") for record in ordered
        )
        options = tuple(
            resolution
            for item in scored
            if item.record.record_type == "control" and item.record.option_set_ref
            for resolution in [
                self._resolve_option(item.record, scope, None, option_candidate_limit)
            ]
            if resolution is not None
        )
        return RetrievalResult(
            "retrieved",
            scored,
            options,
            (),
            duplicates_removed,
            len(scoped_records),
        )

    def _required_scope_dimensions(
        self,
        records: list[CatalogRecord],
        scope: RetrievalScope,
    ) -> tuple[str, ...]:
        required: list[str] = []
        for name in (
            "application_build",
            "role_profile",
            "locale",
            "catalog_version",
            "snapshot_id",
        ):
            requested = getattr(scope, name)
            observed = {getattr(record, name) for record in records}
            if requested is None and len(observed) > 1:
                required.append(name)
        return tuple(required)

    def _resolve_option(
        self,
        record: CatalogRecord,
        scope: RetrievalScope,
        desired_option: str | None,
        candidate_limit: int,
    ) -> OptionResolution | None:
        if not record.option_set_ref:
            return None
        snapshot = next(
            (item for item in self.snapshots if item.snapshot_id == record.snapshot_id),
            None,
        )
        if snapshot is None:
            return None
        option_set = snapshot.option_sets.get(record.option_set_ref)
        if not isinstance(option_set, dict):
            return OptionResolution(
                record.record_id,
                record.option_set_ref,
                "needs_review",
                None,
                (),
                None,
                False,
                None,
            )

        raw_values = option_set.get("values")
        values = (
            [_option_text(value) for value in raw_values]
            if isinstance(raw_values, list)
            else []
        )
        values = [value for value in values if value]
        count = option_set.get("visible_option_count")
        count = count if isinstance(count, int) else None
        search_label = _optional_text(
            option_set.get("search_input_label")
            or record.metadata.get("search_input_label")
        )
        searchable = bool(option_set.get("searchable"))
        embedded = bool(option_set.get("values_embedded", values))

        if searchable and not embedded:
            return OptionResolution(
                record.record_id,
                record.option_set_ref,
                "runtime_search_required",
                None,
                (),
                count,
                True,
                search_label,
            )
        if not values:
            return OptionResolution(
                record.record_id,
                record.option_set_ref,
                "needs_review",
                None,
                (),
                count,
                False,
                search_label,
            )
        if desired_option is None or not desired_option.strip():
            if values and len(values) <= candidate_limit:
                return OptionResolution(
                    record.record_id,
                    record.option_set_ref,
                    "candidate_values",
                    None,
                    tuple(values),
                    count or len(values),
                    False,
                    search_label,
                )
            if searchable:
                return OptionResolution(
                    record.record_id,
                    record.option_set_ref,
                    "runtime_search_required",
                    None,
                    (),
                    count or len(values) or None,
                    True,
                    search_label,
                )
            return OptionResolution(
                record.record_id,
                record.option_set_ref,
                "target_value_required",
                None,
                (),
                count or len(values) or None,
                False,
                search_label,
            )

        target = desired_option.strip()
        exact = [value for value in values if _same(value, target)]
        if len(exact) == 1:
            return OptionResolution(
                record.record_id,
                record.option_set_ref,
                "exact_match",
                exact[0],
                (exact[0],),
                count or len(values),
                False,
                search_label,
            )
        if len(exact) > 1:
            return OptionResolution(
                record.record_id,
                record.option_set_ref,
                "ambiguous",
                None,
                tuple(exact[:candidate_limit]),
                count or len(values),
                False,
                search_label,
            )

        suggestions = sorted(
            values,
            key=lambda value: (
                _candidate_score(target, value),
                value.casefold(),
            ),
            reverse=True,
        )[:candidate_limit]
        return OptionResolution(
            record.record_id,
            record.option_set_ref,
            "candidates_only",
            None,
            tuple(suggestions),
            count or len(values),
            False,
            search_label,
        )


def _rank_records(query: str, records: list[CatalogRecord]) -> list[ScoredRecord]:
    if not records:
        return []
    documents = [_features(record.search_text + " " + record.record_type) for record in records]
    query_features = _features(query)
    document_frequency: Counter[str] = Counter()
    for document in documents:
        document_frequency.update(document.keys())
    document_count = len(documents)
    idf = {
        term: math.log(1.0 + (document_count + 1) / (frequency + 1))
        for term, frequency in document_frequency.items()
    }
    query_vector = _tfidf(query_features, idf)
    scored: list[ScoredRecord] = []
    for record, features in zip(records, documents):
        document_vector = _tfidf(features, idf)
        score = _cosine(query_vector, document_vector)
        scored.append(ScoredRecord(record, score))
    return sorted(
        scored,
        key=lambda item: (
            -item.score,
            item.record.screen_title.casefold(),
            item.record.section_path,
            item.record.label.casefold(),
            item.record.record_id,
        ),
    )


def _features(text: str) -> Counter[str]:
    words = [item.casefold() for item in re.findall(r"[^\W_]+", text, flags=re.UNICODE)]
    stop_words = {"a", "an", "and", "for", "from", "is", "of", "the", "to", "what", "where"}
    features: Counter[str] = Counter(
        f"w:{word}" for word in words if word not in stop_words
    )
    normalized_words = [word for word in words if word not in stop_words]
    for word in normalized_words:
        if len(word) >= 3:
            padded = f"^{word}$"
            for size in (3, 4, 5):
                features.update(
                    f"c:{padded[index:index + size]}"
                    for index in range(max(0, len(padded) - size + 1))
                )
    return features


def _tfidf(features: Counter[str], idf: dict[str, float]) -> dict[str, float]:
    return {term: frequency * idf.get(term, 1.0) for term, frequency in features.items()}


def _cosine(left: dict[str, float], right: dict[str, float]) -> float:
    left_norm = math.sqrt(sum(value * value for value in left.values()))
    right_norm = math.sqrt(sum(value * value for value in right.values()))
    if not left_norm or not right_norm:
        return 0.0
    shared = left.keys() & right.keys()
    return sum(left[key] * right[key] for key in shared) / (left_norm * right_norm)


def _matches_scope(record: CatalogRecord, scope: RetrievalScope) -> bool:
    for attribute in (
        "application_build",
        "role_profile",
        "locale",
        "catalog_version",
        "snapshot_id",
    ):
        requested = getattr(scope, attribute)
        if requested is not None and not _same(getattr(record, attribute), requested):
            return False
    if scope.screen_id is not None and not _same(record.screen_id, scope.screen_id):
        return False
    if scope.variant is not None and not _same(record.variant, scope.variant):
        return False
    if scope.section_path is not None and tuple(
        part.casefold() for part in record.section_path
    ) != tuple(part.casefold() for part in scope.section_path):
        return False
    return True


def _option_text(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, dict):
        for key in ("label", "name", "text", "value"):
            if isinstance(value.get(key), str):
                return value[key].strip()
    return ""


def _candidate_score(target: str, candidate: str) -> float:
    target_tokens = set(_features(target))
    candidate_tokens = set(_features(candidate))
    overlap = len(target_tokens & candidate_tokens) / max(1, len(target_tokens | candidate_tokens))
    return overlap * 0.7 + SequenceMatcher(None, target.casefold(), candidate.casefold()).ratio() * 0.3


def _same(left: str | None, right: str | None) -> bool:
    return bool(left is not None and right is not None and left.strip().casefold() == right.strip().casefold())


def _optional_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


