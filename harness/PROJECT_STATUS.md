# Project Status

**Project:** Clinevo OnePV Test & Validation Automation
**Architecture baseline:** `CLINEVO_TEST_VALIDATION_AUTOMATION_MASTER_SPEC.md`
**Current status:** Phase 4 follow-up partial — compact source-grounded action intents implemented and evaluated on five human cases; all schema checks passed, but one multi-section action-order mismatch remains
**Current authorised phase:** Phase 4 only
**Last updated:** 2026-11-05 12:13 IST

> This tracker records observed phase activity. Update only from observed work and explicit human approvals.

## Phase approvals

| Phase | Name | Status | Human approval | Evidence / handoff |
|---:|---|---|---|---|
| 0 | Bounded repository contract inspection and clean-slate plan | Approved with documentation amendments | Explicitly approved after amendments 2026-11-03 | `docs/legacy-contract-map.md`; `docs/target-package-layout.md`; `docs/phase-plan.md`; `harness/BUILD_LOG.md`; D-013–D-017 |
| 1 | Canonical schemas and source-preserving DOCX/authoring ingestion | Provisionally accepted for Phase 2 | User provisionally accepted verification results 2026-11-04 | D-018; `harness/BUILD_LOG.md`; `harness/context/phase-01-canonical-schemas-docx-extraction-context.md` |
| 2 | Playwright UI Discovery and Inventory Engine | Incomplete and unapproved — user identified the changed discovery run as unreliable; its live artifact is excluded as a Phase 3 seed | Explicitly authorized 2026-11-04; not approved | `harness/context/phase-02-playwright-ui-discovery-context.md`; `backend/artifacts/ui_discovery_live.json` |
| 3 | UI Catalog persistence and one primary Mini-RAG | Approved | Explicitly authorized 2026-11-05; explicitly approved 2026-11-05 09:05 IST | D-019, D-020; `harness/BUILD_LOG.md`; `harness/context/phase-03-ui-catalog-mini-rag-context.md` |
| 4 | Qwen synthetic field-data generation and target validation | Partial — action-intent follow-up; human review pending | Explicitly authorized 2026-11-05 09:05 IST; action-intent follow-up explicitly authorized 2026-11-05 | D-022; latest evaluation in `harness/BUILD_LOG.md` and Phase 4 context |
| 5 | Plan compiler and deterministic Python Playwright runner | Not started | Not authorised | — |
| 6 | On-demand Qwen Healer and controlled write-back | Not started | Not authorised | — |
| 7 | Evidence capture, manifests and audit integrity | Not started | Not authorised | — |
| 8 | Deterministic verifier and outcome state machine | Not started | Not authorised | — |
| 9 | Reporting, template preservation and frontend/API integration | Not started | Not authorised | — |
| 10 | End-to-end OQ pilot, security and operational hardening | Not started | Not authorised | — |

## Current blockers / decisions

- Phase 4's earlier planner design is superseded by D-022. Compact prompt projection retains only screen/section labels, enabled data-entry field labels/types, up to four fixed dropdown candidates, and runtime-search markers; full catalog IDs stay in Python. The five-case action-intent batch used one provider request per successful evaluation: latest provider usage was 1,431 prompt + 2,324 completion = 3,755 total tokens (about 751 per case). All five outputs passed schema, target, source-reference and omission checks. Manual review found the adverse-event case ordered Patient before Reporter although the source names Reporter first; the model repeated that order after a prompt instruction to preserve source order. Treat that case as needing review; do not claim full semantic reliability. Exact request/response records are under ignored `backend/artifacts/qwen_evaluations/`. No Playwright action or screenshot was run. No model-matched tokenizer is configured.
- Available PQ-022 source material contains one canonical case with 18 ordered steps and 18 expected-result checkpoints, not five independent source cases. It has no source-stated case ID and its source environment conflicts with the available development-only catalog. Preserve the single source case intact and mark it for review; do not split it to satisfy the sample count.
- Resolve source-document identity discrepancy before any controlled OQ execution: uploaded OQ filename contains `OQ-036`, while the document header identifies `CLIN-EU-PAT-OPV-1-1-OQ-035, V1.0`. Do not guess.
- Confirm production PQ execution authority, test data and cleanup approach before any production mutation.
- Confirm approved Word template(s), version/hash and permitted report changes; no standalone approved template was identified in the repository.
- Select approved persistence and binary evidence storage; current session state is process-local and files are stored under backend-local folders.
- Define authentication/authorization, secret injection, CORS and credential handling; no provider interface was found, and credential defaults exist in frontend/API source (values intentionally omitted from all records).
- Establish documented test and verification-script commands, supported runtime versions and deployment topology; no test script/configuration or runtime/deployment pin was found.
- Confirm which existing HTTP and WebSocket contracts require long-term compatibility.
- Phase 1 source-shape limitation: supplied OQ/PQ DOCX files organize 42, 8 and 18 ordered step/checkpoint rows in three metadata-bearing tables, each with a blank test-case identifier. The extractor preserves these as one case per table and flags missing identity. Confirm with the document owner whether the scenario grouping stated in the Master Spec is represented elsewhere; do not split rows into cases by inference.
- Compatibility limitation: existing `backend/main.py` still calls legacy `backend/extractor.py` for the served upload workflow. Phase 1 canonical ingestion is not wired into that contract. The legacy parser has template-specific defaults and text transformations; replacing/bridging it requires an explicitly authorized compatibility phase. Do not use it for new canonical ingestion.
- Phase 2 live discovery reached the selected Manual Case Registration workflow in the development environment and recorded PARTIAL coverage (12 screens, 954 controls, 546 option counts, 63 issues). Safe UI interactions timed out on some controls and several current-page navigation candidates did not activate. See the live artifact and Phase 2 context; no user values or credentials were captured. The referenced `harness/build/phase-02-playwright-ui-discovery.md` is absent from this worktree.
- Phase 2 emits a deduplicated `form_fields` inventory with label-match status and nested section path. The latest supervised development run reached Manual Case Registration and reported 58 distinct fields (57 labels associated; the Log search field has only a placeholder), zero dropdown options opened, and 20 coverage issues (11 safe dialog/expand/tab timeouts; 9 navigation candidates point to the current page). Overall report is PARTIAL. No current field values were recorded.

## Phase 3 input exception and current limits

- Phase 2 is not approved and its engine output is not used by Phase 3. Per D-019, Phase 3 imports the separate manually curated browser catalog at `catalog/ui/application_catalog.json` and its manifest. Imported cards remain candidates; this exception does not claim Phase 2 acceptance.
- The curated seed is OnePV development-only; build/role/locale are unknown; screenshots and locator recipes are absent; and two form variants remain uninspected.
- No Qwen tokenizer is configured; runtime context packing requires an injected model-specific tokenizer. The legacy upload serving workflow remains disconnected from canonical ingestion.

## Update rules

- `Complete — awaiting approval` is not the same as `Approved`.
- Only the human can set a phase to Approved.
- Record date/time with timezone when adding an execution event.
