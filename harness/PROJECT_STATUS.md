# Project Status

**Project:** Clinevo OnePV Test & Validation Automation
**Architecture baseline:** `CLINEVO_TEST_VALIDATION_AUTOMATION_MASTER_SPEC.md`
**Current status:** Phase 2 implementation in progress (explicitly authorized)
**Current authorised phase:** Phase 2 only; Phase 3 is not authorized
**Last updated:** 2026-11-04

> This tracker records observed phase activity. Update only from observed work and explicit human approvals.

## Phase approvals

| Phase | Name | Status | Human approval | Evidence / handoff |
|---:|---|---|---|---|
| 0 | Bounded repository contract inspection and clean-slate plan | Approved with documentation amendments | Explicitly approved after amendments 2026-11-03 | `docs/legacy-contract-map.md`; `docs/target-package-layout.md`; `docs/phase-plan.md`; `harness/BUILD_LOG.md`; D-013–D-017 |
| 1 | Canonical schemas and source-preserving DOCX/authoring ingestion | Provisionally accepted for Phase 2 | User provisionally accepted verification results 2026-11-04 | D-018; `harness/BUILD_LOG.md`; `harness/context/phase-01-canonical-schemas-docx-extraction-context.md` |
| 2 | Playwright UI Discovery and Inventory Engine | In progress — live discovery incomplete | Explicitly authorized by pasted user request 2026-11-04 | `harness/build/phase-02-playwright-ui-discovery.md`; `harness/BUILD_LOG.md`; `harness/context/phase-02-playwright-ui-discovery-context.md` |
| 3 | UI Catalog persistence and one primary Mini-RAG | Not started | Not authorised | — |
| 4 | Qwen Planner, fixture resolution and plan validation | Not started | Not authorised | — |
| 5 | Plan compiler and deterministic Python Playwright runner | Not started | Not authorised | — |
| 6 | On-demand Qwen Healer and controlled write-back | Not started | Not authorised | — |
| 7 | Evidence capture, manifests and audit integrity | Not started | Not authorised | — |
| 8 | Deterministic verifier and outcome state machine | Not started | Not authorised | — |
| 9 | Reporting, template preservation and frontend/API integration | Not started | Not authorised | — |
| 10 | End-to-end OQ pilot, security and operational hardening | Not started | Not authorised | — |

## Current blockers / decisions

- Resolve source-document identity discrepancy before any controlled OQ execution: uploaded OQ filename contains `OQ-036`, while the document header identifies `CLIN-EU-PAT-OPV-1-1-OQ-035, V1.0`. Do not guess.
- Confirm production PQ execution authority, test data and cleanup approach before any production mutation.
- Confirm approved Word template(s), version/hash and permitted report changes; no standalone approved template was identified in the repository.
- Select approved persistence and binary evidence storage; current session state is process-local and files are stored under backend-local folders.
- Define authentication/authorization, secret injection, CORS and credential handling; no provider interface was found, and credential defaults exist in frontend/API source (values intentionally omitted from all records).
- Establish documented test and verification-script commands, supported runtime versions and deployment topology; no test script/configuration or runtime/deployment pin was found.
- Confirm which existing HTTP and WebSocket contracts require long-term compatibility.
- Phase 1 source-shape limitation: supplied OQ/PQ DOCX files organize 42, 8 and 18 ordered step/checkpoint rows in three metadata-bearing tables, each with a blank test-case identifier. The extractor preserves these as one case per table and flags missing identity. Confirm with the document owner whether the scenario grouping stated in the Master Spec is represented elsewhere; do not split rows into cases by inference.
- Compatibility limitation: existing `backend/main.py` still calls legacy `backend/extractor.py` for the served upload workflow. Phase 1 canonical ingestion is not wired into that contract. The legacy parser has template-specific defaults and text transformations; replacing/bridging it requires an explicitly authorized compatibility phase. Do not use it for new canonical ingestion.
- Phase 2 live discovery is not complete: an authenticated run exceeded several minutes without a completion summary or progress output and was stopped. No coverage report was produced, and the CLI currently prints only counts rather than serializing the full sanitized result. The CLI now limits the next live pass to 5 screens, 5 navigation visits and 5 safe UI interactions (1-second interaction timeout). A capped retry was opened but stopped at the manual-authentication boundary; it still needs a fresh manual login and terminal confirmation. The browser context is closed and no authenticated state is persisted.

## Update rules

- `Complete — awaiting approval` is not the same as `Approved`.
- Only the human can set a phase to Approved.
- Record date/time with timezone when adding an execution event.
