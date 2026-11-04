# Repository Agent Instructions — Clinevo Test & Validation Automation

## Mission and source of truth
Build the Clinevo OnePV Test & Validation Automation platform according to `CLINEVO_TEST_VALIDATION_AUTOMATION_MASTER_SPEC.md` (the **Master Spec**). The Master Spec is authoritative for target architecture, requirements, phase sequence and acceptance criteria. `harness/` contains phase gates, status and decision records. Older plans and legacy code are historical material; they do not override the Master Spec.

## Mandatory start-up sequence
1. Read this file and `harness/PHASE_EXECUTION_PROTOCOL.md`.
2. Read only the requested phase file in `harness/build/` and the referenced Master Spec sections.
3. Read `harness/PROJECT_STATUS.md`, the relevant `harness/DECISION_LOG.md` entries and prior phase handoff/context only when relevant.
4. For Phase 0 only, perform bounded repository contract inspection as defined by Master Spec Section 5. Do not bulk-read the legacy repository.
5. Do not ask what task to perform when the user has explicitly supplied a phase prompt. Execute that phase within its gate.

## Non-negotiable architecture invariants
- Both AI Author Studio and DOCX uploads converge on one source-preserving canonical protocol model.
- Discover the authorized UI beyond the landing page: nested navigation, screens, sections, fields, native/custom dropdowns and options, tabs, grids, dialogs, popups, frames and safe conditional UI. Record undiscovered/inaccessible branches honestly.
- Initial discovery is read-only by default. Never save, submit, delete, approve, sign, send or mutate real records merely to explore UI. Use approved synthetic/reversible probes only in an authorised non-production environment.
- Keep responsibilities separate: Discovery traverses authorized live UI and produces observations/coverage/candidate metadata; the UI Catalog validates, versions and persists eligible metadata; Mini-RAG retrieves scoped catalog records for Planning; Planning proposes a typed plan; Compilation validates/translates that plan to the allow-listed DSL; Execution alone runs validated actions through Playwright. These stages do not substitute for or write into one another's responsibilities.
- Maintain one primary UI Mini-RAG over a versioned UI catalog. The catalog may be broad; each model request receives only relevant, deduplicated context.
- Budget prompts with the actual model tokenizer/context limit. Never silently truncate procedures, expected results, dropdowns or evidence. Split only at valid scenario/checkpoint boundaries.
- Qwen interprets and plans using schema-constrained structured output. It does not execute arbitrary code, supply secrets, fabricate clinical test data or determine final PASS/FAIL.
- Use approved synthetic test-data fixtures/factories with provenance. Preserve explicit values and intentional blanks from the protocol.
- Compile plans into an allow-listed Python action DSL. Python Playwright is the only primary browser execution runtime.
- Playwright validates locator scope, uniqueness, semantics and actionability before acting. The Healer may propose a recovery; independent validation and any required approval control execution and cache promotion.
- Capture evidence at each required expected-result checkpoint. Preserve original screenshot bytes; metadata is a sidecar. Watermarks/stitching are optional report derivatives, never substitutes for originals.
- Use SHA-256 and protected audit-chain/signature/storage interfaces. A hash alone is not proof of regulatory compliance or tamper-proof storage.
- Determine outcomes using deterministic typed assertions and observed application state. Exact text comparison is allowed when explicitly required by the protocol. No generic `"error"` substring, fuzzy semantic score or LLM-only PASS.
- Distinguish functional outcome from execution status. Support PASS, FAIL, BLOCKED and NEEDS_REVIEW (canonical spelling defined by Master Spec).
- Treat uncertain non-idempotent mutations as uncertain; do not blindly retry Save/Submit/Delete.
- Enforce environment and role gates. Production mutations require explicit organisational authorisation, approved data and cleanup controls.
- Keep credentials, cookies, tokens, PHI/PII and secrets out of model prompts, UI catalog, logs and caches.
- Authenticate and authorize protected HTTP, WebSocket and storage/report operations server-side. Resolve execution secrets only through an approved runtime provider after authorization; never use browser-submitted passwords or secret defaults. Redact sensitive values from logs, exceptions, traces and prompts. Credentialed CORS must use explicit trusted-origin allow-lists; wildcard origins are prohibited.
- Preserve established frontend/API/WebSocket contracts by default, including paths, methods, payloads, event shapes and workflow. A breaking or behavior-changing migration requires explicit human approval, versioning and a migration/rollback plan.
- Phase 1 preserves source bytes/hash, exact source text, stated test identities, structural references, extraction provenance, ambiguity, conflicts and unmapped content. Normalized identities remain separate from source-stated identities.
- Ingestion is general-purpose: supplied documents, identifiers, layouts and counts are examples, never allowlists. Do not hardcode document-specific IDs/names, filenames, row counts or fixed positions. Use documented extensible structural label maps; preserve unfamiliar IDs/labels/structures as source-backed candidates or unmapped content and flag uncertainty.
- The current label extension and identifier-candidate rules are documented in `docs/ingestion-rules.md`; extend those rules through centralized mappings and regression fixtures, not scattered string checks.
- Zero silent text removal: never filter user-authored text by keyword, phrase, regex, ambiguity-word list, normalization or relevance guess. Preserve original bytes and exact source segments/order/formatting where available. Keep extraction/mapping separate from interpretation; store proposed interpretations separately with source references, status and confidence/review needs. Preserve section directives, notes, repetition and conflicting expectations.
- Account for every source segment as mapped, metadata, unsupported-with-warning or unmapped-with-review. Recognition never makes content executable; later validation/planning/approval gates still apply.
- Do not make unsupported FDA/Part 11/GxP compliance claims. Formal applicability, validation and approval belong to the organisation.

## Clean-slate and legacy-code policy
- Preserve the existing frontend UI/experience where practical.
- Perform bounded inspection of frontend routes/components, API calls/types, exact serving endpoints/schemas, data/storage contracts, auth/secret boundary, approved templates and test commands.
- Do not read every legacy source file or reconstruct the old implementation line by line. Do not copy brittle hardcoded dictionaries, regex-driven natural-language parsing, arbitrary selectors, opaque verdict logic or unsafe caches.
- Rebuild backend internals cleanly where justified, while retaining only verified contracts needed by the frontend/data/auth/storage interfaces.
- Do not use the legacy `backend/extractor.py` for new canonical ingestion: its current serving caller applies template-specific parsing and text transformations. Keep the existing serving contract unchanged until an explicitly authorized compatibility integration replaces/adapts that path with source-preserving ingestion.
- Treat package trees in architecture documents as conceptual; create a package/module only in its implementing phase after explicit authorization.
- Never delete/archive legacy code, rewrite migrations, deploy, mutate production, rotate credentials, commit or push without explicit approval.
- The package tree in architecture documents is conceptual. Create packages/modules only in their authorized implementation phase; documentation of a package does not authorize its creation.

## Phase execution gate
- The lossless-ingestion and generalization invariants above supersede conflicting earlier extraction/filtering guidance in this repository, the Master Spec, prompts or legacy code. Never remove section directives or classify ambiguity by keyword alone.
- Execute **one explicitly requested phase only**. Do not start future phases or bundle phases.
- Approval of the architecture or a completed prior phase is not approval to begin the next phase. Require explicit authorization for each phase; approval of Phase 1 does not authorize Phase 2.
- Before coding, state objective, exact scope/files, dependencies, risks and acceptance tests.
- Make the smallest coherent change; add focused tests; run actual commands and report actual output.
- Run the phase tests and required prior-phase regression tests. If commands are unknown, discover them; never invent test commands or fabricate results.
- Update `harness/PROJECT_STATUS.md`, `harness/BUILD_LOG.md` and phase context with material findings only.
- Report changed files, tests passed/failed/skipped, limitations, unresolved decisions and deviations.
- Stop after the phase and wait for explicit human approval. Approval of one phase does not authorize the next.
- If a blocking ambiguity exists, preserve evidence, mark the relevant work BLOCKED/NEEDS_REVIEW and ask one precise decision question. Continue independent safe work within the phase where possible.

## Context efficiency
- Do not repeatedly reread the full Master Spec. Read it once per fresh agent session as supported, then use section pointers and phase files. Never duplicate large source text into status/context logs.
- Read only the files needed for the current phase. Prefer targeted symbol searches and bounded file ranges.
- Keep phase handoffs concise and durable: decisions, interfaces, constraints, test evidence, blockers and next authorised action only.
- Do not create extra agents/subagents unless they have bounded tasks, non-overlapping file ownership and a clear integration/verification benefit.

## Required handoff format
At every phase stop, provide:
1. Phase and status.
2. Files created/changed.
3. What was implemented (or inspected in Phase 0).
4. Exact verification commands and observed results; clearly list skipped tests.
5. Acceptance criteria met/not met.
6. Security, data integrity and recovery notes.
7. Unresolved decisions/blockers and deviations.
8. Updated status/log/context paths.
9. Explicitly state: **Stopped; awaiting approval for the next phase.**
