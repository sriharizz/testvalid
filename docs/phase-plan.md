# Phase Plan

The plan follows Master Spec Section 24. Each phase is separately gated; completion means **awaiting human approval**, not approved. This document itself authorizes no implementation phase; authorization comes from the human for the specific phase.

| Phase | Objective and principal deliverables | Gate |
|---:|---|---|
| 0 | Map the existing UI/API/data/auth/report/test contracts; document target package layout, compatibility approach and open decisions. | Review the three Phase 0 docs; human approval is required before Phase 1. The package layout is conceptual only. |
| 1 | Define layout-independent canonical protocol schemas and DOCX/authoring adapters with extraction coverage and identity-conflict handling. Preserve original bytes, exact source segments/order/formatting where available, stated identities, structural references, provenance, ambiguity and unmapped content. Detailed matching rules are documented in `docs/ingestion-rules.md`. | Generalization/lossless fixtures: unseen IDs/labels/layouts, paragraph/table content, metadata/header variation, authored directives/notes/repetition/conflicting expectations. Every segment is accounted for; unknowns remain reviewable; no keyword-based removal or ambiguity filtering; unresolved identity blocks execution. |
| 2 | Implement authorized read-only Playwright UI discovery, nested navigation/control/option inventory and coverage reporting. | Mock application discovery tests; no unsafe mutating discovery actions. |
| 3 | Implement versioned, scoped UI catalog and one lightweight Mini-RAG with token-aware context budgeting. | Retrieval/scoping/deduplication tests; no instruction truncation. |
| 4 | Implement Qwen adapter, approved fixture resolution, structured planning and plan validation. | Planner tests for ambiguity/provenance/secret exclusion; no model verdict or arbitrary action. |
| 5 | Compile validated plans into an allow-listed Python DSL and execute with deterministic Playwright. | Runner tests for locator uniqueness, environment gates, readback and safe mutation reconciliation. |
| 6 | Add on-demand healer proposals, independent locator validation and versioned controlled catalog promotion. | Healer tests; unvalidated proposals cannot execute or become trusted. |
| 7 | Capture checkpoint evidence, sidecar manifests, hashes and protected audit-integrity interfaces. | Evidence tests; originals remain unchanged; missing required evidence prevents PASS. |
| 8 | Implement deterministic assertion evaluation and execution/outcome state machine. | Verifier tests; support PASS/FAIL/BLOCKED/NEEDS_REVIEW, with no AI-only PASS. |
| 9 | Populate approved templates, generate evidence/report artifacts and integrate compatible APIs with the retained UI. | Template preservation and traceability review; frontend flows and download access tests. |
| 10 | Pilot an approved OQ subset in Validation with synthetic data; harden security, recovery, operations and measured performance. | QA/technical approval before expansion; Production mutations remain gated. |

## Sequencing constraints

- Phase 0 has been approved with the documentation amendments recorded in the decision/build logs. Phase 1 was explicitly authorized; it remains awaiting human review/approval. Phase 2 and each later phase require separate explicit human authorization.
- Implement one phase at a time. Do not pull later-phase functionality into an earlier phase beyond a minimal required interface.
- Run phase-specific and required regression checks when a phase implements code. Record actual commands/results; never claim skipped tests passed.
- Before any controlled OQ execution, resolve the filename/header identity conflict recorded in the Master Spec. Before any Production PQ mutation, obtain explicit organizational approval and approved test-data/cleanup controls.
- Resolve remaining decisions (approved template, persistence/storage, identity/authorization/secret-provider details, CORS origins, test/deployment conventions and compatibility migration mechanics) in the phase(s) that depend on them. Existing frontend/API/WebSocket contracts remain preserved unless an explicit approved migration says otherwise.

