from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from backend.app.domain.ui_catalog import CatalogScope
from backend.app.infrastructure.catalog_repository import (
    CatalogIntegrityError,
    JsonCatalogRepository,
)
from backend.app.services.catalog.catalog_manager import CatalogManager
from backend.app.services.retrieval.token_budget import (
    ContextBudgetExceeded,
    ContextUnit,
    TokenBudgetConfig,
    TokenBudgeter,
)
from backend.app.services.retrieval.ui_mini_rag import RetrievalScope, UIMiniRAG


ROOT = Path(__file__).resolve().parents[3]
CATALOG_PATH = ROOT / "catalog" / "ui" / "application_catalog.json"
MANIFEST_PATH = ROOT / "catalog" / "ui" / "discovery_manifest.json"


@pytest.fixture
def imported_catalog(tmp_path: Path):
    repository = JsonCatalogRepository(tmp_path / "catalog-store")
    manager = CatalogManager(repository)
    snapshot = manager.import_file(CATALOG_PATH, MANIFEST_PATH)
    return repository, manager, snapshot


def test_import_preserves_sources_and_maps_controls_to_section_paths(
    imported_catalog,
) -> None:
    _, _, snapshot = imported_catalog
    assert snapshot.source_catalog_bytes == CATALOG_PATH.read_bytes()
    assert snapshot.manifest_bytes == MANIFEST_PATH.read_bytes()
    assert snapshot.scope == CatalogScope("OnePV", "development")
    assert len(
        [
            record
            for record in snapshot.records
            if record.record_type == "screen"
        ]
    ) == 7

    first_name = next(
        record
        for record in snapshot.records
        if record.label == "First Name(English)"
        and record.section_path == ("Reporter",)
        and record.variant == "Adverse Event"
    )
    assert first_name.record_type == "control"
    assert first_name.screen_title == "Manual Case Registration"
    assert first_name.control_kind == "text"
    assert first_name.source_ref.endswith("/fields/1")
    assert first_name.metadata["locator_recipe_status"] == "not_recorded"

    assessment_field = next(
        record
        for record in snapshot.records
        if record.label == "Outcome Code"
    )
    assert assessment_field.section_path == ("Event Information", "Assesment")

    uninspected_variants = {
        variant
        for screen in snapshot.coverage["screen_statuses"]
        for variant in (screen.get("variants") or {}).get("not_inspected", [])
    }
    assert {"PQC with AE", "PQC with MI"} <= uninspected_variants
    assert not any(
        record.variant in uninspected_variants and record.record_type == "control"
        for record in snapshot.records
    )


def test_repository_is_versioned_idempotent_and_detects_source_tampering(
    imported_catalog,
) -> None:
    repository, manager, snapshot = imported_catalog
    saved_path = repository.snapshot_path(snapshot)
    assert (saved_path / "source_catalog.json").read_bytes() == CATALOG_PATH.read_bytes()
    assert (saved_path / "discovery_manifest.json").read_bytes() == MANIFEST_PATH.read_bytes()

    loaded = manager.load(snapshot.scope, snapshot.catalog_version, snapshot.snapshot_id)
    assert loaded.snapshot_id == snapshot.snapshot_id
    assert [record.record_id for record in loaded.records] == [
        record.record_id for record in snapshot.records
    ]
    manager.import_file(CATALOG_PATH, MANIFEST_PATH)
    assert len(repository.list_snapshots()) == 1

    source_path = saved_path / "source_catalog.json"
    source_path.write_bytes(source_path.read_bytes() + b" ")
    with pytest.raises(CatalogIntegrityError):
        repository.load(snapshot.scope, snapshot.catalog_version, snapshot.snapshot_id)


def test_new_catalog_version_is_persisted_as_a_separate_snapshot(
    tmp_path: Path,
) -> None:
    source = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    second_path = tmp_path / "catalog-v2.json"
    source["catalog_version"] = "0.1.1"
    second_path.write_text(json.dumps(source, ensure_ascii=False), encoding="utf-8")

    repository = JsonCatalogRepository(tmp_path / "store")
    manager = CatalogManager(repository)
    first = manager.import_file(CATALOG_PATH, MANIFEST_PATH)
    second = manager.import_file(second_path, MANIFEST_PATH)

    assert first.catalog_version == "0.1.0"
    assert second.catalog_version == "0.1.1"
    assert first.snapshot_id != second.snapshot_id
    assert {item["catalog_version"] for item in repository.list_snapshots()} == {
        "0.1.0",
        "0.1.1",
    }


def test_retrieval_finds_section_mapped_fields_for_representative_queries(
    imported_catalog,
) -> None:
    _, _, snapshot = imported_catalog
    rag = UIMiniRAG([snapshot])
    cases = (
        (
            "reporter first name",
            RetrievalScope("OnePV", "development", variant="Adverse Event"),
            "First Name(English)",
            ("Reporter",),
        ),
        (
            "case deletion case number",
            RetrievalScope("OnePV", "development", screen_id="case_deletion"),
            "Case Number",
            ("Case Intake Delete Search",),
        ),
        (
            "audit history case number",
            RetrievalScope("OnePV", "development", screen_id="audit_history"),
            "Case Number",
            ("Audit History",),
        ),
        (
            "product quality complaint status code",
            RetrievalScope(
                "OnePV", "development", variant="Product Quality Complaint"
            ),
            "Status Code",
            ("Product Complaint Details",),
        ),
        (
            "medical inquiry found answer",
            RetrievalScope("OnePV", "development", variant="Medical Inquiry"),
            "Found Answer",
            ("Medical Information",),
        ),
    )
    reciprocal_ranks: list[float] = []
    for query, scope, expected_label, expected_section in cases:
        result = rag.retrieve(query, scope, top_k=5)
        assert result.status == "retrieved", (query, result)
        rank = next(
            (
                index
                for index, item in enumerate(result.records, start=1)
                if item.record.label == expected_label
                and item.record.section_path == expected_section
            ),
            None,
        )
        assert rank is not None, query
        reciprocal_ranks.append(1 / rank)
    mean_reciprocal_rank = sum(reciprocal_ranks) / len(reciprocal_ranks)
    print(
        f"UI catalog evaluation: hit@5={len(reciprocal_ranks)}/{len(cases)}, "
        f"MRR={mean_reciprocal_rank:.3f}"
    )


def test_scope_rejects_wrong_environment_and_unknown_requested_build(
    imported_catalog,
) -> None:
    _, _, snapshot = imported_catalog
    rag = UIMiniRAG([snapshot])

    wrong_environment = rag.retrieve(
        "reporter first name",
        RetrievalScope("OnePV", "production"),
    )
    wrong_build = rag.retrieve(
        "reporter first name",
        RetrievalScope("OnePV", "development", application_build="build-42"),
    )

    assert wrong_environment.status == "scope_mismatch"
    assert wrong_build.status == "scope_mismatch"
    assert not wrong_environment.records
    assert not wrong_build.records


def test_retrieval_requires_build_when_catalogs_for_multiple_builds_are_loaded(
    tmp_path: Path,
) -> None:
    repository = JsonCatalogRepository(tmp_path / "store")
    manager = CatalogManager(repository)
    build_one = manager.import_file(CATALOG_PATH, MANIFEST_PATH, application_build="build-1")
    build_two = manager.import_file(CATALOG_PATH, MANIFEST_PATH, application_build="build-2")
    rag = UIMiniRAG([build_one, build_two])

    result = rag.retrieve(
        "reporter first name",
        RetrievalScope("OnePV", "development"),
    )

    assert result.status == "scope_required"
    assert "application_build" in result.required_scope_dimensions
    assert not result.records


def test_duplicate_catalog_cards_do_not_repeat_in_retrieved_context(
    imported_catalog,
) -> None:
    _, _, snapshot = imported_catalog
    result = UIMiniRAG([snapshot, snapshot]).retrieve(
        "reporter first name",
        RetrievalScope("OnePV", "development", variant="Adverse Event"),
        top_k=8,
    )

    record_ids = [item.record.record_id for item in result.records]
    assert result.status == "retrieved"
    assert len(record_ids) == len(set(record_ids))
    assert result.duplicate_count_removed > 0


def test_runtime_search_lists_keep_values_out_of_prompt_but_preserve_exact_target(
    imported_catalog,
) -> None:
    _, _, snapshot = imported_catalog
    rag = UIMiniRAG([snapshot])
    country = rag.retrieve(
        "reporter country code",
        RetrievalScope("OnePV", "development", variant="Adverse Event"),
        desired_option="India",
    )
    form_type = rag.retrieve(
        "manual case registration form type",
        RetrievalScope(
            "OnePV", "development", screen_id="manual_case_registration"
        ),
        desired_option="Medical Inquiry",
        top_k=4,
    )

    country_resolution = next(
        item for item in country.option_resolutions if item.option_set_ref == "country_code"
    )
    form_resolution = next(
        item for item in form_type.option_resolutions if item.option_set_ref == "form_type"
    )
    assert country_resolution.status == "runtime_search_required"
    assert country_resolution.requires_runtime_lookup
    assert country_resolution.full_option_count == 258
    assert country_resolution.search_input_label == "Search"
    assert not country_resolution.candidate_values
    assert form_resolution.status == "exact_match"
    assert form_resolution.exact_value == "Medical Inquiry"


def test_small_static_dropdown_values_are_available_when_generation_has_no_target_value(
    imported_catalog,
) -> None:
    _, _, snapshot = imported_catalog
    rag = UIMiniRAG([snapshot])
    result = rag.retrieve_sections(
        [("General Info",)],
        RetrievalScope(
            "OnePV",
            "development",
            screen_id="manual_case_registration",
            variant="Adverse Event",
        ),
    )

    classifications = next(
        item.record
        for item in result.records
        if item.record.record_type == "control"
        and item.record.label == "Case Classifications Code"
    )
    resolution = next(
        item
        for item in result.option_resolutions
        if item.field_record_id == classifications.record_id
    )

    assert resolution.status == "candidate_values"
    assert resolution.candidate_values
    assert len(resolution.candidate_values) <= 10


def test_missing_or_ambiguous_retrieval_does_not_invent_a_field(
    imported_catalog,
) -> None:
    _, _, snapshot = imported_catalog
    result = UIMiniRAG([snapshot]).retrieve(
        "synthetic quantum widget",
        RetrievalScope("OnePV", "development"),
    )
    assert result.status == "needs_review"
    assert not result.records


def test_retrieved_context_is_bounded_and_keeps_card_source_references(
    imported_catalog,
) -> None:
    _, _, snapshot = imported_catalog
    rag = UIMiniRAG([snapshot])
    result = rag.retrieve(
        "reporter first name",
        RetrievalScope("OnePV", "development", variant="Adverse Event"),
        top_k=5,
    )
    budgeter = TokenBudgeter(
        TokenBudgetConfig(10000, 100, 100, 500, 100),
        lambda value: len(value.split()),
    )

    batches = rag.pack_context(result, budgeter)

    serialized_ids = [
        json.loads(unit.content)["card_id"]
        for batch in batches
        for unit in batch.units
    ]
    assert serialized_ids == [item.record.record_id for item in result.records]
    assert all(batch.token_count <= budgeter.config.available_input_tokens for batch in batches)
    assert all(
        "source_ref" in json.loads(unit.content)
        for batch in batches
        for unit in batch.units
    )


def test_token_budgeter_splits_only_complete_units_without_truncating_text() -> None:
    # This deterministic fake tokenizer is test-only; runtime must inject the model tokenizer.
    counter = lambda value: len(value.split())
    budgeter = TokenBudgeter(
        TokenBudgetConfig(
            model_context_limit=8,
            system_prompt_tokens=1,
            schema_and_tool_tokens=1,
            reserved_output_tokens=1,
            runtime_margin=1,
        ),
        counter,
    )
    units = (
        ContextUnit("case-1", "scenario", "  Procedure one\n"),
        ContextUnit("checkpoint-1", "checkpoint", "Expected result  "),
        ContextUnit("case-2", "scenario", "Procedure two expected two"),
    )

    batches = budgeter.pack(units)

    assert len(batches) == 2
    assert [unit for batch in batches for unit in batch.units] == list(units)
    assert batches[0].content == units[0].content + "\n\n" + units[1].content
    assert batches[1].content == units[2].content
    assert all(batch.token_count <= budgeter.config.available_input_tokens for batch in batches)


def test_token_budgeter_reports_oversize_unit_instead_of_truncating() -> None:
    seen: list[str] = []

    def counter(value: str) -> int:
        seen.append(value)
        return len(value.split())

    budgeter = TokenBudgeter(
        TokenBudgetConfig(4, 0, 0, 1, 1),
        counter,
    )
    source_text = "Do not remove any of this source text."
    unit = ContextUnit("scenario-9", "scenario", source_text)

    with pytest.raises(ContextBudgetExceeded) as error:
        budgeter.pack([unit])

    assert error.value.unit_ids == ("scenario-9",)
    assert source_text in seen
    assert source_text not in str(error.value)


def test_token_budgeter_requires_explicit_model_token_counter() -> None:
    with pytest.raises(TypeError):
        TokenBudgeter(TokenBudgetConfig(100, 1, 1, 10, 5))  # type: ignore[call-arg]


def test_token_budgeter_rejects_unapproved_split_boundaries() -> None:
    budgeter = TokenBudgeter(
        TokenBudgetConfig(100, 1, 1, 10, 5),
        lambda value: len(value.split()),
    )
    with pytest.raises(ValueError, match="scenario, checkpoint, or catalog-card"):
        budgeter.pack([ContextUnit("partial-step", "paragraph", "Keep whole")])
