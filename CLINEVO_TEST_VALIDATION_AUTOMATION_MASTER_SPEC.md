# Clinevo OnePV Test & Validation Automation
## Master System Design, Engineering Specification, and Phase-by-Phase Execution Plan

**Document status:** Architecture baseline approved for implementation  
**Version:** 1.1  
**Prepared:** 2026-11-03  
**Updated:** 2026-11-04  
**Primary implementation language:** Python  
**Browser automation:** Playwright for Python (async API preferred)  
**AI planning model:** Qwen, supplied through a configurable model-serving adapter  
**Backend integration:** Preserve the existing frontend experience and compatible API/data contracts after a bounded inspection; rebuild legacy backend logic where necessary.  
**Intended users:** AI coding agents (Codex, Claude Code, Cursor, Windsurf, etc.), engineers, reviewers, QA and validation stakeholders.

---

# 0. Read This First — Binding Instructions for Any AI Coding Agent

This file is the authoritative architecture and implementation specification for the new system. It supersedes the earlier `master_v5_production_spec.md` wherever the two conflict.

The existing codebase is legacy implementation material, **not the source of truth for the target architecture**. The agent must not spend tokens reading thousands of lines of legacy code, reverse-engineering every old module, or preserving bad implementation patterns. The agent must perform a bounded contract inspection only (see Phase 0), retain the existing frontend UI where practical, identify API/data contracts that must remain compatible, and implement the target architecture cleanly.

## 0.1 Non-negotiable rules

1. **One phase at a time.** Implement only the phase explicitly requested. Run that phase's tests plus required regression tests, report exact results, and stop for human approval.
2. **Do not implement future phases early.** It is acceptable to add a minimal interface/stub required by the current phase, but do not implement a later phase's functionality.
3. **Do not bulk-read the legacy repository.** Follow the bounded repository reconnaissance instructions in Phase 0. Do not read every `.py`, `.tsx`, or generated file.
4. **Preserve the existing frontend experience.** Keep the current visual design, page layout and user workflow unless a specific incompatibility is demonstrated. Refactor frontend internals only when required by the new API contract.
5. **Rebuild backend internals cleanly when justified.** Do not carry forward legacy hardcoded dictionaries, brittle parsers, tightly coupled agents, arbitrary selectors, opaque pass/fail logic or unsafe cache behaviour merely to avoid rewriting code.
6. **No hardcoded application-specific test data.** Do not hardcode OnePV patient names, addresses, clinical values, field lists, dropdown options, validation text, menu paths or application selectors in Python. Such knowledge must originate from the controlled protocol, approved test-data fixtures, live UI discovery or explicitly approved configuration.
7. **Framework guardrails are allowed and required.** Fixed schemas, allowed action types, security policies, verification algorithms, status enums, evidence rules and environment safeguards are framework controls, not prohibited test-data hardcoding.
8. **No regex/string parsing of natural-language procedures as the primary semantic engine.** Structural parsing and identifiers may use deterministic parsing. Qwen interprets procedure meaning into a canonical schema. Preserve source text. Never silently discard text as “noise.”
9. **Never send credentials, cookies, session tokens, patient data or other secrets to Qwen.** Credentials are injected at runtime from an approved secret provider. Logs and model prompts must be redacted.
10. **Qwen never executes arbitrary Python, JavaScript or browser commands.** It produces schema-constrained plans only. A deterministic Python action dispatcher executes allow-listed operations.
11. **Qwen cannot decide final PASS/FAIL.** PASS/FAIL must be determined from structured, deterministic assertions against observed application state and required evidence.
12. **No silent truncation.** Never truncate procedures, expected results, dropdowns, DOM context or evidence metadata just to fit a prompt. Reduce irrelevant context or split at valid semantic boundaries.
13. **No auto-promotion of unverified AI discoveries.** AI-proposed locators and UI cards are candidates until independently validated and, where policy requires, approved.
14. **No unsafe production exploration.** Discovery is read-only by default. Mutating or probe operations require explicit environment, permission and approval gates.
15. **No false regulatory claims.** Do not label the platform or generated artifacts “FDA compliant,” “FDA approved,” or “GxP validated” merely because this architecture includes timestamps, screenshots or hashes.
16. **Do not invent speed claims.** Measure extraction, retrieval, planning, browser execution and review latency. Do not claim 3 ms full execution or fixed LLM call times without benchmark data.
17. **Do not resolve source-document conflicts automatically.** Preserve them and mark the run BLOCKED or NEEDS_REVIEW pending authorised resolution.
18. **No destructive repository operations without explicit approval.** Do not delete the legacy app or rewrite migrations as part of reconnaissance. Use a branch and preserve rollback capability.
19. **Protect identity and secrets at every boundary.** Authenticate and authorize protected API, WebSocket, report, screenshot and storage operations. Resolve execution credentials only through an approved runtime secret provider after authorization. Never accept browser-submitted passwords as trusted execution credentials or place secret defaults in source/configuration. Redact secrets and sensitive data from logs, traces, exceptions and model context. Use explicit trusted-origin allow-lists for credentialed CORS; wildcard origins are prohibited.
20. **Preserve established frontend/API contracts by default.** Keep existing routes, methods, request/response fields, WebSocket event shapes and user workflows compatible. A breaking or behavior-changing contract migration requires explicit human approval, versioning and a migration/rollback plan.
21. **Lossless, general-purpose ingestion.** Treat supplied documents and identifiers as examples, never as allowlists. Do not hardcode document-specific IDs, names, filenames, row counts or positions. Never remove, suppress or normalize-away user-authored text or classify it through keyword/phrase/regex filters or ambiguity word lists. Preserve original bytes, source segments, ordering and formatting where available; account for every segment as mapped, metadata, unsupported-with-warning or unmapped-with-review. Keep extraction separate from interpretation; any derived interpretation is separate, source-referenced, confidence/status-bearing and non-executable until later gates approve it. Preserve section directives, notes, repetition and conflicting expectations. This rule supersedes conflicting earlier wording in this specification, prompts and legacy code.
22. **Legacy parser boundary.** The current serving route imports `backend/extractor.py`, which contains document-specific defaults and text normalization/heuristics. It is historical compatibility code, not an approved canonical ingestion implementation. Do not route new authoring/DOCX ingestion through it. Replace or bridge that path only in an explicitly authorized compatibility phase, preserving established API contracts while ensuring the canonical source and all source-backed fields remain recoverable.

## 0.2 Phase execution protocol

When instructed to execute Phase N:

- Read this specification in full (it is the design source of truth).
- Read only the files allowed by the Phase 0 contract map and the exact files needed for Phase N.
- State the intended files to create/change before implementation.
- Implement Phase N only.
- Add or update tests for Phase N.
- Run the exact phase test commands and all required preceding-phase regression tests.
- Report changed files, tests run, outputs, unresolved issues and deviations from this specification.
- Do not claim success for skipped tests.
- Stop and wait for explicit approval before starting Phase N+1.

If a required contract is genuinely missing or ambiguous, do not guess. Produce a short decision request with the exact evidence and a safe proposed default. Continue with independent work only when it does not depend on that decision.

---

# 1. Project Purpose and Business Objective

Clinevo's Testing & Validation team performs test protocol execution for Clinevo applications, including OnePV Intake. Manual execution includes interpreting test documents, preparing test data, navigating the application, entering and validating data, capturing screenshots, recording actual results, collecting exports, completing approved Word templates, investigating discrepancies and preparing evidence for review.

The current end-to-end validation cycle has been described by the project team as taking approximately **four months**. The business target is to reduce the cycle to approximately **one month**, while preserving validation quality, test traceability, data integrity, security and reviewability.

This is a target, not a guaranteed outcome. The system must measure the full cycle, including planning, execution, rework, evidence review, discrepancy resolution and approvals. Browser speed alone does not demonstrate a four-to-one cycle-time reduction.

## 1.1 Primary product outcome

Build a controlled test-execution platform that:

- Accepts test cases authored in normal English through the existing AI Author Studio.
- Accepts uploaded DOCX validation protocols.
- Extracts and preserves the original test instructions and expected results.
- Discovers the reachable application UI beyond the post-login landing page, including screens, sections, fields, dropdown options, grids, tabs, modals and permitted conditional UI.
- Maintains a versioned UI catalog and a single primary UI Mini-RAG retrieval engine.
- Uses Qwen to interpret test meaning and generate structured, constrained execution plans.
- Executes approved actions through deterministic Playwright for Python.
- Uses an on-demand Qwen Healer to propose recovery for unknown screens or locator drift, with independent validation before reuse.
- Captures checkpoint-based evidence with trustworthy timestamps and metadata.
- Determines test outcomes using deterministic assertions, not an LLM verdict.
- Generates executed protocol and evidence deliverables using approved templates and traceability.
- Supports controlled QA review, discrepancy handling and sign-off.

## 1.2 What success looks like

A successful implementation is not merely one that can click through a demo form. It must demonstrate:

1. Correct preservation of source protocol meaning.
2. Discovery of relevant UI controls and available dropdown options beyond the first page.
3. No uncontrolled context-window growth.
4. Reproducible test-data provenance.
5. Safe, deterministic execution with explicit environment controls.
6. Correct handling of positive, negative and compound test scenarios.
7. Evidence completeness and integrity.
8. No false PASS outcomes in the validated test set.
9. Recoverable, explainable failures.
10. Useful reductions in manual effort measured against a baseline.

---

# 2. Source Material and Facts That Must Be Preserved

The architecture was developed through an initial master v5 plan followed by a later design discussion. The later accepted decisions and corrections in this document supersede conflicting details in the first plan.

## 2.1 Uploaded protocol observations

The uploaded documents and their IDs, names, layouts and counts below are bounded regression examples, not an exhaustive supported-input definition or a basis for extractor hardcoding. General extraction must handle other identifiers and layouts and preserve unfamiliar material for review.

The supplied OQ example is a 66-page Operational Qualification document for Clinevo OnePV Intake System 1.1. Its test-script section contains:

- Test Set 1: Manual Case Registration — scenarios `1.1.1` through `1.1.42` (42 scenarios).
- Test Set 2: Reports – Audit History — scenarios `2.1.1` through `2.1.8` (8 scenarios).

Therefore, the OQ is **not one 50-row execution table** and must not be forced into a fixed “first 25 / second 25” split. The two test sets have different screens, dependencies and workflow intent.

The OQ filename supplied to the conversation contains `OQ-036`, but the document header on its pages states `CLIN-EU-PAT-OPV-1-1-OQ-035, V1.0`. This discrepancy is unresolved. The system must preserve both the uploaded filename and the identifier extracted from the document, flag the mismatch and block controlled execution until an authorised document owner/QA reviewer resolves it.

The OQ examples include, among other things:

- Accessing the Validation environment and logging in.
- Manual Case Registration navigation.
- Negative validation for empty mandatory fields and classification mismatch.
- Positive case registration and generated temporary case ID.
- Manual questionnaire creation and responses.
- Questionnaire template import, duplicate import checks and deletion.
- Reporter and patient creation/update.
- Product selection and auto-populated Generic Name / Formulation Code.
- Event information and MedDRA term/code verification.
- Activity-log create, update and delete, including deletion without a reason followed by deletion with a reason.
- Case submission, case processing, exit and logout.
- A separate Audit History flow that updates a Reported Term, searches history, verifies old/new values and exports Excel for verification.

The supplied PQ example is a 33-page Performance Qualification document containing scenarios `1.1.1` through `1.1.18` (18 scenarios). Its cover identifies the **Production** environment and its flow includes actual case registration, data entry, save/submit and case processing. PQ therefore requires a stronger production safety and approval gate than OQ Validation.

## 2.2 Do not copy old master-plan assumptions blindly

The earlier v5 plan contains implementation-specific assumptions that are superseded or corrected here:

- Do not assume the OQ has one 50-row table.
- Do not hardcode a 25-step batch size as the final batching strategy.
- Do not use fixed character truncation such as `procedure[:2500]` or `expected_result[:800]`.
- Do not cap a dropdown to ten values by discarding the rest of the authoritative local option set.
- Do not treat the first logged-in page as the entire application UI.
- Do not treat runtime Healer observations as automatically trusted permanent cards.
- Do not generate TypeScript `.spec.ts` as the primary execution artifact while the production runner is Python.
- Do not allow a 150-token Qwen judge or fuzzy semantic similarity score to make the final PASS/FAIL decision.
- Do not treat a hash chain without protected signing/storage as tamper-proof.
- Do not promise zero LLM calls or millisecond full-protocol execution without measurement.
- Do not call an internally generated document an official “FDA audit certificate.” Use an accurately named audit-trail/integrity report unless the organisation has formally approved a specific certificate format.

---

# 3. Architecture Decisions — Final Baseline

## 3.1 Approved architecture

```text
INPUT CHANNELS
  ├── AI Author Studio (normal-English test authoring)
  └── DOCX Protocol Upload
          │
          ▼
SOURCE-PRESERVING INGESTION / EXTRACTION
          │
          ▼
CANONICAL TEST SPECIFICATION
          │
          ├─────────────────────────────────────────────────────┐
          │                                                     │
          ▼                                                     ▼
PROTOCOL QUALITY / SAFETY GATE                     PLAYWRIGHT UI DISCOVERY MODE
          │                                         (initial + incremental)
          │                                                     │
          │                                         UI INVENTORY / NAV GRAPH
          │                                                     │
          └────────────────────────┬────────────────────────────┘
                                   ▼
                    VERSIONED UI CATALOG / INDEX
                                   │
                                   ▼
                      ONE PRIMARY UI MINI-RAG
                                   │
                                   ▼
                         QWEN PLANNER
                  (bounded context, structured plan)
                                   │
                                   ▼
                      PLAN VALIDATOR / POLICY GATE
                                   │
                                   ▼
                 PYTHON ACTION-PLAN COMPILER / DSL
                                   │
                                   ▼
                  DETERMINISTIC PLAYWRIGHT RUNNER
                                   │
                    ┌──────────────┴──────────────┐
                    │                             │
                    ▼                             ▼
          LIVE UI / DOM OBSERVATION       ON-DEMAND QWEN HEALER
                    │                    (candidate recovery only)
                    │                             │
                    └──────────────┬──────────────┘
                                   ▼
                     CHECKPOINT EVIDENCE ENGINE
                                   │
                                   ▼
                  INDEPENDENT DETERMINISTIC VERIFIER
                                   │
                                   ▼
                REPORTING / EVIDENCE / QA REVIEW
```

## 3.2 Core responsibility boundaries

| Component | Owns | Must not own |
|---|---|---|
| DOCX extractor | Structural extraction and source references | Guessing test intent or deleting unclear text |
| Canonical protocol layer | Authoritative normalized test representation | UI-specific locator execution |
| UI discovery engine | Read-only traversal of authorised live UI; raw observations, coverage and candidate metadata | Owning the durable approved catalog, planning tests, compiling actions or executing test scenarios |
| UI catalog | Versioned UI metadata, navigation relationships and lifecycle state; controlled persistence/promotion | Crawling the application, storing patient/case records or credentials, planning or executing tests |
| UI Mini-RAG | Retrieving relevant, scoped catalog records for planning | Discovering/crawling live UI, mutating catalog records, rewriting source protocols or inventing expected results |
| Qwen Planner | Semantic interpretation and structured plan proposal | Direct browser access, arbitrary code or final verdict |
| Plan validator | Schema, policy, environment, data and locator checks | Guessing missing business requirements |
| Generator/compiler | Compile validated plan to the Python runner's action DSL | Generating unrestricted executable code |
| Playwright runner | Deterministic navigation, actions and observations | Deciding PASS from a click succeeding |
| Qwen Healer | Suggest locator/control mapping for unfamiliar UI | Silently changing acceptance criteria or trusted cache |
| Evidence engine | Preserve original checkpoint artefacts and metadata | Changing raw evidence after capture |
| Verifier | Deterministic expected-vs-actual assertion evaluation | AI similarity as a verdict |
| Report generator | Populate approved templates with verified outputs | Reformatting official controlled templates without approval |

## 3.3 One UI Mini-RAG, not multiple overlapping UI RAGs

The initial system uses **one primary UI Mini-RAG** backed by a complete, versioned UI catalog. The catalog is the source store; Mini-RAG is the retrieval layer. A separate requirements/SOP retrieval index may be added only if a concrete requirement needs it and after a separate design decision. Do not add extra RAG systems by default.

## 3.4 Python execution is the primary runtime

The production browser runner is Python Playwright. The Generator must produce a typed JSON action plan / Python-compatible execution DSL. Do not create TypeScript code as the required execution format. A TypeScript export can be added later only if the product has a genuine external need for it.

## 3.5 Clean backend architecture; preserve the frontend contract

The team is willing to replace legacy backend internals. Therefore:

- Prefer a clean modular backend over copying old flat-file structures just to preserve implementation.
- Preserve existing frontend visual design and primary UX.
- Preserve existing API contracts where the current frontend or other consumers depend on them. A breaking or behavior-changing versioned migration requires explicit human approval; see Section 20.2.
- Reuse approved persistence and authentication services when they are sound and compatible.
- Do not preserve legacy business logic that violates this specification.
- Do not delete the legacy implementation before the new system reaches an approved migration/parity point.

---

# 4. Operating Modes

The platform has three distinct modes. Keep them separate in code and permissions.

## 4.1 Discovery mode

Purpose: build and refresh knowledge about the application's reachable UI.

- Runs with an authorised discovery identity.
- Defaults to read-only exploration.
- Produces observations, coverage and candidate metadata. It does not plan protocol scenarios, compile execution actions or execute test cases. A separate catalog service validates, versions and persists eligible metadata under its lifecycle policy.
- Can inspect screens, forms, fields, dropdown options, grids, tabs, modals, menus and frames.
- May perform reversible probe selections only in an approved non-production environment using synthetic fixtures and documented reset/cleanup.
- Never submits, saves, deletes, approves, signs, sends or mutates real business records just to discover the UI.
- Records what was discovered, what was not reachable and why.

## 4.2 Planning mode

Purpose: compile an authored or uploaded protocol into a safe, reviewable action plan.

- Uses the canonical protocol, relevant UI Mini-RAG cards and approved synthetic test-data fixture references.
- Reads catalog content through Mini-RAG; it does not traverse the live UI or write catalog records.
- Produces a proposed typed plan for deterministic validation; it does not compile or execute browser actions.
- Does not control the browser.
- Does not alter the source protocol.
- Produces a validated plan, not Python/JavaScript code.
- Marks uncertain instructions as `NEEDS_REVIEW`.

## 4.3 Execution mode

Purpose: execute an approved plan against a declared environment.

- Uses isolated Playwright browser contexts.
- Uses an authorized run identity and credentials injected at runtime from an approved secret provider; credentials are not submitted by the browser as trusted execution secrets.
- Executes only allow-listed actions compiled from a validated plan. Execution does not perform discovery traversal or promote catalog records.
- Captures evidence at defined checkpoints.
- Verifies each expected result deterministically.
- Stops on unsafe ambiguity or unrecoverable execution errors.

---

# 5. Bounded Legacy Repository Reconnaissance (Phase 0)

The coding agent must understand just enough of the current repository to preserve the user-facing application and connect the replacement backend. It must not perform a line-by-line audit of the old implementation.

## 5.1 Inspect these areas only

1. Repository directory tree, excluding `.git`, `node_modules`, virtual environments, build outputs, caches and generated artefacts.
2. Dependency manifests and runtime versions (`pyproject.toml`, `requirements*.txt`, `package.json`, lockfiles, Docker/compose files and deployment manifests if present).
3. Frontend application entry points, routing, layout/theme, AI Author Studio components and API client/service modules.
4. Frontend TypeScript types/interfaces for protocol/session/step/report/evidence objects.
5. Backend route declarations and request/response schemas only for endpoints used by the existing frontend.
6. Database schema/migrations and storage contracts relevant to protocols, sessions, users, reports and files.
7. Authentication/session boundary and environment configuration interfaces. Never print secret values.
8. Existing approved Word templates or report-generation interfaces, if present.
9. Existing test commands and a small representative set of tests.

## 5.2 Do not inspect by default

- Every legacy backend module line by line.
- Old AI prompts and hardcoded clinical dictionaries, except targeted search to confirm they will not be reused.
- Generated bundles, minified assets, `node_modules`, caches, log dumps or uploaded PHI.
- Old architecture modules merely to infer the new architecture.

## 5.3 Required targeted searches

Use targeted symbol searches to locate:

- FastAPI route paths and HTTP methods used by the frontend.
- Pydantic request/response schemas used by those routes.
- Frontend API calls and data types.
- Supabase/Postgres table names or other current persistence contracts, if present.
- Authentication provider interface and secret injection boundary.
- Existing approved DOCX template paths and report output endpoints.

Do not dump full file contents when a targeted signature, schema or call site is enough.

## 5.4 Phase 0 deliverable

Create `docs/legacy-contract-map.md` with:

- Current frontend routes/components to preserve.
- Existing API endpoints and request/response shapes used by those components.
- Existing data tables/storage contracts that must remain compatible or be migrated.
- Authentication/secret boundary (names/interfaces only; no values).
- Approved document templates and output contract.
- Existing test commands.
- Proposed new backend package structure.
- Legacy components explicitly not reused and why.
- Unknowns and decisions requiring human approval.

Stop after Phase 0. Do not begin implementation until the contract map is reviewed.

---

# 6. Canonical Protocol Model

Both input channels must converge on one canonical model. This is a central design invariant.

## 6.1 Source-preserving extraction

Every extracted item must retain:

- Original source text.
- Original document name and byte-level SHA-256.
- Protocol identifier/version as written in the document.
- Test set/scenario/step identifier as written.
- DOCX structural location: table index, row index, cell index, paragraph index and OOXML relationship/merge information as applicable.
- Original ordering.
- Extraction method and parser version.
- Extraction confidence and warnings.
- Exact original content for every extracted paragraph, cell, step and checkpoint, with the original document bytes retained in controlled source storage and a source SHA-256. No uncertain text or unmapped content may be silently omitted, normalized away or replaced by inference.
- Test-set, test-case/scenario, step and checkpoint identities as stated in the source. Keep normalized identifiers separate and linked; preserve missing, conflicting or ambiguous identities as explicit unknowns/conflicts.
- Reviewable extraction provenance: parser/extractor version, method, structural location, confidence, warnings, unsupported structures and source-segment-to-canonical-entity mapping. Retain and flag source segments that have no canonical mapping.
- The complete original source remains retrievable unchanged. Do not discard section directives, notes, repeated instructions, unfamiliar phrases, empty/intentional fields or conflicting expectations. Normalize labels only for lookup; never replace original source text, bytes or available formatting.
- Account for every source segment as explicitly mapped, metadata, unsupported with a warning, or unmapped with a review reason. Content not understood by current rules remains source-backed and reviewable; it is never silently rejected or omitted.

DOCX has no stable fixed pagination guarantee: page numbers can change with Word version, fonts, layout and rendering. For DOCX, use structural references as the primary provenance locator. If an approved rendering pipeline produces a PDF, a page number can be stored as an additional reference, never as the sole source pointer.

## 6.2 Canonical entities

The exact field names may be refined during Phase 1, but the model must represent at least:

### `ProtocolDocument`

- `document_id`
- `original_filename`
- `source_sha256`
- `media_type`
- `protocol_identifier_as_stated`
- `protocol_version_as_stated`
- `application_name`
- `application_version_as_stated`
- `qualification_type` (OQ / PQ / IQ / other / unknown)
- `environment_as_stated`
- `extraction_status`
- `identity_conflicts[]`
- `source_refs[]`

### `Protocol`

- `protocol_id`
- `document_id`
- `protocol_version`
- `environment`
- `test_sets[]`
- `preconditions[]`
- `acceptance_criteria[]`
- `source_refs[]`
- `review_status`

### `TestSet`

- `test_set_id`
- `title`
- `objective`
- `sequence`
- `scenarios[]`
- `dependencies[]`
- `source_refs[]`

### `Scenario`

- `scenario_id` (preserve protocol ID such as `1.1.38`)
- `title`
- `objective`
- `preconditions[]`
- `procedure_original`
- `actions[]`
- `checkpoints[]`
- `data_requirements[]`
- `dependencies[]`
- `environment_constraints`
- `risk_classification`
- `source_refs[]`
- `interpretation_status`

### `ActionStep`

- Stable internal ID.
- Original source step text and source reference.
- Semantic action type (navigation, fill, select, click, read, wait, download, verify, etc.).
- Target intent (field/control concept, not an unverified CSS selector).
- Value source (explicit protocol value, approved fixture reference, runtime variable, intentionally blank, or not applicable).
- Precondition and dependency references.
- Whether the action is mutating/destructive.
- Whether it requires human approval.

### `ExpectedResultCheckpoint`

- Stable checkpoint ID.
- Original expected-result text.
- Source reference.
- Semantic expectation category.
- Structured assertion specification, if unambiguous.
- Whether the assertion needs persistence verification.
- Required evidence type(s).
- Interpretation confidence/status.

### `SourceRef`

- `document_id`
- `table_index`, `row_index`, `cell_index`, `paragraph_index` where relevant.
- `xml_path` or stable OOXML reference if available.
- `scenario_id` / `step_id` / checkpoint mapping.
- Optional rendered page number as secondary metadata.

## 6.3 Preserve compound scenarios and checkpoint trajectories

A single scenario may have multiple actions and multiple expected-result checkpoints. Do not flatten it to one action or one final expected result.

Examples:

- Delete without reason → expected error → enter reason → delete → expected success.
- Populate required sections → verify auto-populated fields → submit with one intentionally missing field → expected validation error.
- Update a record → search the audit history → verify old and new values → export Excel → verify downloaded content.

Represent each checkpoint in order and preserve the relationship between intermediate and final states.

## 6.4 Natural-language interpretation rules

- Do not use regex or `if "reporter" in text` rules to interpret arbitrary prose.
- Structural parsing can identify document tables, numbered scenario IDs, explicit field/value formats and cross-references, but must preserve their raw text.
- Qwen may normalize semantic intent into the canonical schema.
- Qwen may not invent missing expected results, mandatory fields, application rules or values.
- If a source instruction is vague (for example, `(Enter the data)`), resolve the value from an approved synthetic fixture or test-data policy. If none exists, flag it for author/reviewer input.
- Explicitly blank fields in negative tests must remain blank; never auto-fill them because a field appears mandatory.
- Cross-references such as “Refer expected result 1” must be represented as links between procedure substeps and the relevant checkpoint, not discarded.
- No keyword-, phrase-, regex- or fixed ambiguity-word filtering is permitted. Do not infer ambiguity or irrelevance from words such as “appropriate,” “relevant,” “details,” “some,” “below” or “select” alone. Assess meaning only in context; if context cannot be established, preserve the source and leave interpretation unresolved.
- Store deterministic or model-derived interpretations separately from original text, with source references, method, confidence where available, and proposed/review/approval status. An interpretation cannot overwrite source content or become executable merely because a field was recognized.
- Distinguish explicitly structured content, high-level instructions requiring later UI discovery, genuinely ambiguous/conflicting instructions, and unrecognized content requiring review. If extraction alone cannot establish a category, retain it as unclassified/unmapped for reviewed interpretation.
- Section directives and navigation context remain in source order. A later phase may attach derived section context while retaining the original segment and provenance.

---

# 7. DOCX Ingestion and Extraction

## 7.1 Extraction pipeline

1. Accept DOCX file and enforce upload size/type limits.
2. Preserve original bytes unchanged in controlled storage.
3. Calculate `source_sha256` before processing.
4. Inspect package structure and document properties.
5. Extract body paragraphs, tables, rows, cells, nested tables, headers and footers where relevant.
6. Preserve table/row/cell coordinates and merged-cell relationships.
7. Preserve list numbering/bullets and paragraph order.
8. Identify protocol/test-set/scenario structures mechanically where explicit.
9. Preserve procedure and expected-result text exactly.
10. Build a source-preserving extraction representation.
11. Pass the relevant extracted structure to Qwen for semantic mapping into canonical entities.
12. Validate that every source step and expected-result block is represented or explicitly flagged.
13. Run document identity and extraction quality gates.

Extraction rules must be structural, extensible and format-agnostic. Keep label aliases in a documented mapping/configuration surface that can be extended without scattering string checks. Support variable header positions, metadata across rows, different labels/numbering conventions, multiple sets/cases, paragraph and table layouts, and missing metadata. Unknown labels and structures remain source-backed and trigger review. Do not force a layout or identifier format to match the supplied examples.

Phase 1's current label and identifier-candidate rules are documented in `docs/ingestion-rules.md`; that mapping is deliberately small and extensible. It must not become an allowlist of supported documents or a natural-language filter.

Preserve every extracted source segment, including content not yet mapped to a canonical entity. Record ambiguity explicitly; semantic interpretation must not overwrite original text or silently resolve conflicting identities.

## 7.2 DOCX edge cases to handle

- Merged cells across columns or rows.
- Repeated table header rows.
- Multi-page tables.
- A scenario title in one row and continuation text in later rows.
- Expected results spanning several rows.
- Numbered steps and bullet lists inside one cell.
- “Refer expected result N” links.
- Blank/empty cells.
- Nested tables.
- Repeated table headers on page breaks.
- Paragraphs outside tables that govern subsequent test steps.
- Header/footer document identifiers and version numbers.
- Text boxes or drawing-layer content that `python-docx` does not expose as ordinary paragraphs/tables; flag for an alternative OOXML extraction path or manual review rather than silently omitting it.

Use `python-docx` for the normal Word object model and inspect raw OOXML when required for merge/numbering/relationships. Do not use OCR for a normal DOCX. If a scanned PDF/image is later supported, define a separate OCR validation path and retain its confidence/provenance.

## 7.3 Extraction quality gate

The extractor must produce an extraction coverage report:

- Source tables/rows/cells observed.
- Source paragraphs observed.
- Scenario IDs detected.
- Procedure blocks detected.
- Expected-result blocks detected.
- Cross-references resolved/unresolved.
- Empty or merged cells.
- Unsupported structures.
- Conflicting document identity/version/environment values.
- Any text with no canonical mapping.

The source is not ready for planning if important test content was omitted or the protocol identity conflict is unresolved.

---

# 8. Playwright UI Discovery and Inventory Engine

This component is a major part of the final architecture. It must not be reduced to a first-page DOM scrape or to opportunistic learning only when test execution fails.

## 8.1 Discovery objective

Systematically discover the application UI that is reachable under the authorised discovery account and declared environment, beyond the initial post-login page. The target inventory includes navigation structure, screen metadata, sections, fields, control types, available choices, tables/grids, tabs, nested accordions, modals, popups, pages/tabs, frames and permitted conditional UI branches.

The goal is to discover **UI structure and available choices**, not to scrape all business records or patient data.

## 8.2 Discovery scope

### Navigation

- Landing page and global header.
- Sidebar/menu navigation.
- Nested menus and accordion groups.
- Links and internal routes reached through actual UI navigation.
- Breadcrumbs and contextual navigation.
- User-role-specific visibility (catalogued by role; never assume one role sees all routes).

### Screens and sections

- Full reachable page structure.
- Tabs and tab panels.
- Accordions and expandable sections.
- Cards, panels and nested forms.
- Search pages and result views.
- Modal/dialog content.
- Confirmation and validation dialogs when safely reachable.
- New browser tabs/popups opened by a permitted navigation action.

### Controls

Discover more than only `<input>`, `<select>`, `<textarea>` and `<button>`. Include:

- Textboxes and textareas.
- Native select controls.
- Custom comboboxes, listboxes and autocomplete controls.
- Radio buttons and checkboxes.
- Switches/toggles.
- Date/time pickers.
- Buttons and links.
- Search icons and lookup controls.
- Contenteditable controls.
- Tabs and tab panels.
- Tables, grids, column headers, row actions and pagination.
- File upload/download controls.
- Alerts, status badges and validation messages.
- Iframes and open Shadow DOM controls where supported.

### Field metadata

For each discovered field, capture what is available and safe:

- Accessible name / label.
- Role and control type.
- Associated label relationship.
- Placeholder/title when present.
- Input type.
- Required/optional state if declared by DOM/ARIA or a verified UI property.
- Readonly/disabled state.
- Max length, min/max, pattern or constraints if exposed.
- Parent screen/section/container.
- Stable locator recipe and locator evidence.
- Discovery timestamp and UI version fingerprint.

Do not infer `required=true` just because the field label sounds mandatory. Store the evidence source and confidence.

## 8.3 Dropdown and option discovery — explicit requirement

Yes: initial discovery must open permitted dropdowns and inspect their available options, not merely record that a field is a dropdown.

### Native `<select>`

- Inspect all `<option>` elements, their values, labels and disabled/selected states.
- Preserve the complete option set locally when it is available.
- Record whether the list appears complete or dynamically constrained.

### Custom dropdown / combobox

- Use the accessible control to open the list.
- Locate the associated listbox/options.
- Record options and disabled states as they appear.
- Support scrolling and virtualized option lists.
- If the control loads options asynchronously, wait for a stable completion condition and record the retrieval/loaded state.
- If options are paginated, record paging behaviour and available pages/cursor semantics.
- Close the dropdown without selecting an option during read-only discovery.

### Very large option dictionaries / lookup controls

- Keep the complete enumerable option metadata in the local catalog when the UI exposes it safely and feasibly.
- Do not send the full list to Qwen.
- For very large searchable catalogs (for example, terminology/product lookup search), index the search control and its behaviour, not necessarily every possible domain record. Retrieve actual candidates at execution time using the approved UI search workflow.
- If the UI only renders a small virtualized window, record that the catalog is partially observed and use controlled search-based retrieval when a specific option is required.

### Conditional fields

Some selections reveal additional fields or dropdowns. The discovery engine must identify conditional dependencies. It may explore a safe branch using approved synthetic probe values only in a Validation/test environment, then reset/clean up. It must not save, submit or create real records solely to discover the branch.

If a conditional branch cannot be safely reached, record `conditional_not_discovered` with the condition and reason. Never claim 100% coverage without evidence.

## 8.4 Discovery traversal algorithm

Use a controlled breadth-first/graph traversal over permitted navigation states:

1. Create an isolated Playwright browser context for the discovery session.
2. Authenticate using the approved discovery identity, with credentials injected outside the LLM.
3. Capture the landing-page navigation and state.
4. Extract all visible and accessible navigation items.
5. Expand collapsed parent menus/accordions and capture child items.
6. Add permitted navigation targets to a traversal queue.
7. Visit each target through actual UI navigation; do not guess hidden URLs unless the route is discovered from an approved UI link or configuration.
8. Wait for a stable page state using explicit locators/network/application readiness rules; avoid arbitrary fixed sleeps as the primary synchronisation mechanism.
9. Record screen identity and extract controls, sections, tables, dropdown metadata and navigation relationships.
10. Explore safe tabs, accordions and non-mutating modals.
11. Detect new pages/popups and inspect their content when authorised.
12. Detect frames and inspect each accessible frame.
13. Inspect open Shadow DOM where supported; mark closed Shadow DOM or inaccessible embedded controls as unsupported/partial.
14. Record the observed state fingerprint and mark the traversal node as visited.
15. Continue until the queue is exhausted or a policy/permission boundary is reached.
16. Produce a coverage report listing discovered, visited, inaccessible, conditionally undiscovered and unsupported UI states.

Use a stable state fingerprint to prevent navigation loops. Do not use only the URL as screen identity: single-page applications often reuse one URL for several tabs/modals/states.

## 8.5 Safe discovery boundaries

The discovery engine must not:

- Click Save, Submit, Delete, Approve, Sign, Send, Finalise, or other mutating actions merely to discover what they do.
- Open patient/case records and collect actual record contents unless separately authorised for a specific test purpose.
- Store real patient identifiers, names, dates of birth, addresses, clinical narratives or other PHI in UI cards.
- Bypass authentication or role-based access controls.
- use application APIs to mutate records as a shortcut around the UI.
- Continue into a destructive workflow simply because a button is visible.

Read-only search, opening non-mutating views, opening a dropdown and reading its options are allowed under the discovery account's approved scope. Any reversible probe operation must be separately allow-listed, use synthetic data, run only in an approved non-production environment and have a documented reset/cleanup procedure.

## 8.6 Discovery tools and Playwright capabilities

Prefer Playwright's semantic inspection and locator APIs:

- `page.get_by_role()`
- `page.get_by_label()`
- `page.get_by_placeholder()` where appropriate
- `page.get_by_test_id()` where the application provides stable test IDs
- `locator.aria_snapshot()` for a scoped subtree
- `page.aria_snapshot()` where supported by the installed Playwright version
- DOM metadata extraction for properties not represented in the accessibility tree
- `frame_locator()` / frame inspection for accessible iframes
- page/popup/download events for new tabs and exports

Playwright Python `page.aria_snapshot()` is documented as available from v1.59. Feature-detect or pin a compatible version; if the installed version is older, use the available locator-level snapshot and DOM extraction paths. AI-optimised snapshots are a compact observation format, not a complete replacement for DOM metadata extraction.

Playwright locators support open Shadow DOM; closed Shadow DOM is not traversed by standard locators. Record this limitation rather than fabricating coverage.

## 8.7 UI Catalog record statuses

Every discovered screen/control/option record must have a lifecycle status:

- `observed`: extracted from the live UI but not yet validated.
- `candidate`: interpreted/mapped by the AI or discovery logic.
- `validated`: locator uniqueness, role, context and behaviour checked deterministically.
- `approved`: reviewed/approved for reuse if the organisation's control process requires approval.
- `stale`: invalidated by a build/role/locale/UI fingerprint change.
- `unsupported`: inaccessible or not safely discoverable.

Do not silently promote `observed` or `candidate` records to `approved`.

---

# 9. Versioned UI Catalog and One Primary Mini-RAG

## 9.1 Catalog structure

Maintain a persistent inventory consisting of:

1. **Navigation graph** — parent/child/menu relationships and discovered route transitions.
2. **Screen cards** — screen title, path, application/environment/build, role/locale and structural summary.
3. **Section cards** — form sections, tabs, accordions, cards, modal content and grids.
4. **Field/control cards** — field label, role, type, constraints, locator recipe and source evidence.
5. **Option sets** — full observed option metadata or searchable/partial inventory references.
6. **Interaction relationships** — which safe control opens which screen/modal/tab or reveals a conditional section.
7. **Coverage records** — discovered/visited/unsupported/conditional statuses.

A card may be stored as JSON or in an existing relational store, but the logical model must be versioned and queryable. Keep sensitive business data out of the catalog.

## 9.2 Example card (illustrative only)

```json
{
  "card_id": "ui-card-versioned-id",
  "application": "OnePV",
  "environment": "Validation",
  "application_build": "observed-build-id",
  "role_profile": "approved-discovery-role",
  "locale": "en",
  "screen_title": "Patient Information",
  "navigation_path": ["Intake", "Manual Case Registration"],
  "section_title": "Patient Information",
  "controls": [
    {
      "control_id": "stable-catalog-control-id",
      "accessible_name": "Date of Birth",
      "role": "textbox",
      "control_type": "date",
      "locator_recipe": {
        "strategy": "label",
        "name": "Date of Birth",
        "scope_card_id": "ui-card-versioned-id"
      },
      "metadata_status": "validated"
    }
  ],
  "discovery_status": "validated",
  "discovered_at_utc": "2026-11-03T18:40:12.123Z"
}
```

Do not hardcode this example as an application definition. Actual card content is discovered from the live UI.

## 9.3 Stable identity and deduplication

Deduplicate by a canonical identity that includes relevant scope, such as:

- Application.
- Environment.
- Application build/version fingerprint.
- Role profile.
- Locale.
- Screen/navigation identity.
- Section identity.
- Control role/type and stable label/accessible name.

Do not rely on transient generated DOM IDs alone. Do not merge cards across environments/roles/builds merely because their visible labels look similar.

A batch of scenarios may reference the same UI card many times. Include the card once in the retrieved context and use references from each scenario to that card. Deduplication must not remove test steps or checkpoint relationships.

## 9.4 Retrieval method

Start with a lightweight CPU-based retriever appropriate for structured UI metadata:

- Exact metadata filters first (application, environment, build, role, locale, screen/section scope).
- Lexical token matching and character n-gram TF-IDF or an equivalent tested CPU retrieval approach.
- Optional embeddings only if an offline evaluation demonstrates materially better retrieval quality and acceptable operational cost.
- Do not add a vector database solely because the project contains the word RAG.

Use a relevance threshold and return source references/scores. If no relevant card meets the threshold, the planner must not pretend the screen is known; it may request live discovery or mark the plan `NEEDS_REVIEW`.

## 9.5 Dropdown retrieval policy

- Store full option metadata locally where discoverable.
- Resolve exact protocol-explicit values against the local option set or live UI.
- For Qwen context, return a small ranked candidate set (ten is a soft default prompt cap, not a data deletion rule).
- If the correct value is not among the candidates, perform a targeted local/live query for the exact requested option.
- Never silently pick a different option because the true one was pruned.
- If multiple candidates are ambiguous, stop for review.
- If a step simply says “select from dropdown” without a target value, use an approved fixture/data-policy value. Do not let Qwen pick an arbitrary clinically meaningful value without provenance.

---

# 10. Context-Window and Token-Budget Management

Context control is an architectural requirement. A complete UI catalog can be large; a single Qwen request must remain bounded.

## 10.1 Principle

**Index broadly; retrieve narrowly; send only what the current planning unit needs.**

A large local UI inventory does not imply a large LLM prompt.

## 10.2 Prompt context contents

For a planning unit, include only:

- The complete original procedure text for the selected scenario(s).
- The complete expected-result text and linked checkpoint context.
- Preconditions and scenario dependencies relevant to that unit.
- Relevant UI navigation path and section cards.
- Relevant field/control cards.
- Relevant dropdown option candidates (not all catalog options).
- Approved fixture references/values necessary for planning (synthetic and non-sensitive).
- Action/verification schema and safety constraints.

Do not include:

- The complete application DOM.
- Every UI card in the catalog.
- Unrelated Admin/Reports/Calls/E-mails screens.
- All scenarios in the protocol for every request.
- Every option of a 250-option dropdown.
- Patient/case records or real PHI.
- Passwords, cookies, access tokens or session state.
- Repeated copies of a card already present in the current planning context.

## 10.3 Token-budget calculation

Use the tokenizer corresponding to the configured Qwen model/runtime wherever available. Do not estimate tokens from characters alone.

```text
available_input_budget =
    model_context_limit
  - system_prompt_tokens
  - schema_and_tool_tokens
  - reserved_output_tokens
  - runtime_margin
```

Measure the actual prompt token count before dispatch. Keep a configurable safety margin. The model context limit and output reserve must come from deployment configuration, not assumptions in code.

## 10.4 Batching policy

Do not use a fixed `<=25` steps as the principal batching rule.

- Group scenarios by test-set boundaries, dependencies and logical workflow.
- Preserve the original scenario execution order unless an approved change explicitly permits reordering.
- Keep compound scenarios and their checkpoint trajectories together.
- Use the tokenizer budget to decide batch size.
- If a planning unit exceeds budget, split between independent scenarios or at an explicitly modelled checkpoint boundary.
- Never split a compound scenario in a way that loses its state trajectory or dependency context.
- Never silently truncate original procedure or expected-result content.
- Record the batch membership, token count, model/config version and source scenario IDs.

## 10.5 Runtime context control

A Healer request should contain only:

- Current scenario/action and expected checkpoint.
- Current screen's relevant accessible snapshot/DOM metadata.
- Relevant local UI card, if any.
- The specific locator failure/ambiguity.
- Allowed action/locator schema.

Do not send the entire page or full history unless a measured need justifies it. Keep an execution event summary outside the LLM conversation and pass only the necessary recent state.

## 10.6 Observability metrics

Record per request:

- Prompt tokens.
- Output tokens.
- Retrieved card IDs and count.
- Duplicate-card count removed.
- Context budget utilisation.
- Truncation flag (must always be false for source instructions).
- Retrieval latency.
- Planner latency.
- Cache hit/miss.
- Retry and schema-validation outcomes.

If a context budget is exceeded, split or retrieve less irrelevant material; do not delete source instructions.

---

# 11. Qwen Planner and Structured Plan Generation

## 11.1 Qwen's role

Qwen is the **semantic protocol compiler/planner**. It is not a free-roaming browser agent and is not the verifier.

It receives canonical test content plus relevant UI context and produces a structured plan describing:

- Navigation path.
- Field/control targets.
- Action sequence.
- Value provenance.
- Dependencies and runtime variables.
- Pre-action checks.
- Expected-result checkpoint references.
- Evidence checkpoints.
- Ambiguities and missing information.

## 11.2 Test-data policy

The earlier “100% Qwen data synthesis” requirement is superseded.

Qwen must not invent clinical or personal data merely because a field needs a value. Values must originate from:

1. Explicit values in the approved protocol, or
2. Approved synthetic test-data fixtures/data factory, or
3. Explicit author/reviewer input, or
4. An approved deterministic runtime value provider (for example, a test-run date parameter where the protocol specifies relative timing).

Qwen may map fixture fields to UI fields and select among approved fixture values. Every applied value must have provenance:

- `protocol_explicit`
- `approved_fixture`
- `runtime_parameter`
- `intentionally_blank`
- `reviewer_supplied`

Do not use `ai_synthesized_mandatory` as permission to fabricate clinical facts. If the source does not define a required value and no approved fixture exists, mark `NEEDS_REVIEW`.

## 11.3 Credentials and authentication

- Exclude login/password/enterprise fields and all secret values from Qwen prompts.
- Authenticate and authorize the requesting user/service before planning or execution access. Runtime credentials come from a vault or approved secret-injection boundary after authorization; they are never accepted as trusted browser request fields or source defaults.
- Keep credentials masked in UI where supported and never log values.
- Do not store passwords, cookies, bearer tokens or session identifiers in UI catalog, plan cache, model prompt or report.
- Enforce least privilege, role/environment/run scope and audit secret access. Redact sensitive values in exceptions, traces and diagnostic output as well as ordinary logs.
- An authenticated browser context can be reused only within the policy-approved scope and must be isolated per run/user.

## 11.4 Structured outputs

Use a strict typed schema (for example, Pydantic models) for Qwen's response. If the deployed serving stack supports JSON Schema constrained decoding (for example, a compatible vLLM structured-output mode), use it. This is an aid, not a substitute for application-side validation.

After receiving model output:

1. Parse JSON.
2. Validate against the exact schema.
3. Reject unknown action types/fields where appropriate.
4. Validate every referenced scenario/checkpoint/card/fixture ID.
5. Validate value provenance.
6. Validate locator recipes against catalog evidence.
7. Validate environment and mutation policy.
8. Validate action order and dependencies.
9. Validate that required checkpoints have assertions/evidence mappings.
10. If invalid, permit at most one bounded repair attempt using the validation errors; if still invalid, mark `NEEDS_REVIEW`/`BLOCKED` and do not execute.

Use deterministic low-variance settings where supported, but do not assume temperature zero guarantees correctness.

## 11.5 Planner output contract (illustrative)

```json
{
  "plan_id": "plan-id",
  "protocol_id": "protocol-id",
  "protocol_version": "1.0",
  "environment": "Validation",
  "model_info": {
    "model_name": "configured-qwen-model",
    "runtime_version": "configured-runtime",
    "prompt_version": "planner-v1"
  },
  "scenario_plans": [
    {
      "scenario_id": "1.1.38",
      "actions": [
        {
          "action_id": "action-1",
          "type": "click",
          "target_control_ref": "activity-log-delete-control",
          "source_step_ref": "source-step-ref"
        }
      ],
      "checkpoints": [
        {
          "checkpoint_id": "checkpoint-1",
          "assertion_spec_ref": "assertion-spec-ref",
          "evidence_required": ["screenshot", "observed_state"]
        }
      ],
      "ambiguities": []
    }
  ]
}
```

This is an illustration of shape, not a hardcoded OnePV test plan.

---

# 12. Plan Compiler and Python Action DSL

The generator must compile the validated plan into a constrained execution format consumed by the Python runner.

## 12.1 Allowed action types

Define and validate a small, explicit action vocabulary, such as:

- `navigate_to_screen`
- `expand_navigation_item`
- `click`
- `fill`
- `select_native_option`
- `select_custom_option`
- `check`
- `uncheck`
- `set_toggle`
- `read_value`
- `read_text`
- `wait_for_state`
- `capture_evidence`
- `download_file`
- `assert_checkpoint`
- `close_dialog`
- `reset_form` (only when explicitly in the protocol/approved plan)

The exact list is frozen in code and validated. Add new action types only through a reviewed change.

## 12.2 Forbidden plan output

Reject plans containing:

- Arbitrary Python/JavaScript source.
- `eval`/`exec` instructions.
- Unrestricted browser tool calls.
- Arbitrary network requests.
- Unapproved API/database mutations.
- Unapproved file-system commands.
- Credentials/secrets.
- Unmapped test data.
- Unreferenced locators.
- A final PASS/FAIL label generated by Qwen.

## 12.3 Locator recipe

A locator recipe should describe intent and supporting evidence, e.g. role/name/label/test ID and optional container scope. Do not generate fragile selectors from guesses.

Before an action:

- Resolve the locator in the current live DOM.
- Confirm the expected role/type.
- Confirm it resolves to exactly one element.
- Confirm visible/enabled/editable/actionable state as appropriate.
- Confirm it is scoped to the intended section/modal/grid if needed.
- Do not silently use `.nth()` or force a click to bypass ambiguity.

CSS/XPath selectors are last-resort locator strategies only when they are derived from stable, observed attributes and validated. Record the evidence and version for reuse.

---

# 13. Deterministic Playwright Runner

## 13.1 Runner principles

- Use Playwright for Python; async API is preferred for FastAPI orchestration.
- Use isolated `browser.new_context()` per execution session.
- Keep execution state, evidence and temporary files in a run-scoped directory.
- Respect the protocol's declared sequence and dependencies.
- Use Playwright's auto-waiting and retrying assertions; avoid arbitrary fixed sleeps as the primary wait strategy.
- Use user-facing semantic locators first: role, label, placeholder and approved test IDs.
- Use explicit timeouts and report which precondition timed out.
- Do not use `force=True` as a generic recovery method.
- Do not rely on transient DOM IDs or positional selectors without validated evidence.
- Treat network/console signals as diagnostics and supporting evidence, not the sole test oracle.

## 13.2 Navigation

- Resolve route path from the versioned navigation graph and/or live UI observation.
- Expand collapsible parent menus before child links.
- Validate the target screen after navigation, not merely that a click occurred.
- Support same-URL SPA state changes by observing screen state, selected tab, heading and relevant controls.
- Handle popups/new pages through Playwright page events where the protocol requires them.
- Handle frames with frame locators where accessible.

## 13.3 Form actions and readback

Before committing a form action:

1. Resolve each field/control against the current UI.
2. Validate uniqueness and control type.
3. Apply values from their approved source.
4. Read back values after entry/selection.
5. Confirm intentionally blank fields remain blank.
6. Observe auto-populated fields after their triggering selection.
7. Record applied-input provenance and observed value.
8. Capture required pre-action evidence checkpoint.
9. Perform Save/Submit/Delete only when approved by the plan/environment gate.
10. Capture the resulting state before dismissing transient dialogs.

For auto-populated values (e.g. Generic Name/Formulation Code) capture their actual observed values before Save/Submit if the form may reset/redirect. Do not assume the value was correctly populated merely because a lookup selection was made.

## 13.4 Tables and grids

- Discover header-to-column relationships from the live table/grid structure.
- Resolve row-specific controls in the correct row and column context.
- Do not assume the first matching “Response” input is the intended one.
- Support pagination and result filtering where the protocol requests it.
- Verify row counts/content after mutations only where that is an accepted expected result.

## 13.5 Idempotency and retries

Non-idempotent actions must not be blindly retried after uncertain outcomes.

If a click/submit times out after it may have reached the application:

1. Stop further mutation.
2. Capture current evidence and technical state.
3. Perform a read-only reconciliation (for example, search for the record/ID) if approved.
4. Determine whether the action happened.
5. If the outcome cannot be established, mark `NEEDS_REVIEW`.
6. Do not issue another Save/Submit/Delete just because the first response was lost.

## 13.6 Network and console diagnostics

Record relevant network failures and console errors with timestamps and redaction. Do not automatically classify every HTTP 4xx as a failure: negative validation scenarios may intentionally trigger a 4xx response. Map a network response to the relevant expected checkpoint and application behaviour. An unrelated 5xx or browser infrastructure error may block execution, but it is not automatically proof of a functional requirement failure.

---

# 14. On-Demand Qwen Healer and Controlled Self-Learning

## 14.1 When to call the Healer

Call the Healer only when:

- A planned screen/modal is genuinely not represented in the catalog.
- A known control cannot be resolved on the current application build.
- A locator is ambiguous or a control's role/label changed.
- A conditional UI branch exposes new controls required by the current approved scenario.

Do not call the Healer for every action or every screen. Do not use it as a replacement for systematic initial discovery.

## 14.2 Healer input

Send only:

- Current scenario/procedure and relevant expected checkpoint.
- Current screen/section identity.
- Relevant accessible snapshot and DOM control metadata.
- Existing card/locator and the specific failure reason.
- Allowed action and locator schema.

Do not send full page DOM by default, unrelated UI, credentials, PHI or session secrets.

## 14.3 Healer output and acceptance

The Healer may propose:

- A mapping from protocol intent to a live control.
- A locator recipe.
- A control type.
- A candidate UI card update.

The backend must then validate:

1. The target resolves to exactly one element.
2. Role/control type matches the proposed semantic target.
3. The element is within the correct form/section/dialog/grid scope.
4. It is visible and actionable for the intended operation.
5. The operation is allow-listed and permitted for the environment.
6. No other plausible control is also matched.
7. The proposed value has approved provenance.

If validation fails or ambiguity remains, do not execute; mark `NEEDS_REVIEW` or `BLOCKED`.

## 14.4 Controlled write-back

- Store the discovery as `candidate` first.
- Store validation observations and the exact UI/application fingerprint.
- Promote to `validated` only after deterministic checks.
- Promote to `approved` only when the configured approval policy is satisfied.
- Do not overwrite the last known-good card without versioning.
- Keep a rollback path.
- Do not update expected results or test data during locator healing.

---

# 15. Evidence Capture and Audit-Trail Subsystem

Evidence is a first-class subsystem. It must not be a screenshot helper that only runs at the end of a scenario.

## 15.1 Capture policy

Capture evidence at every required expected-result checkpoint, plus critical failures. Do not capture after every trivial click if that adds no evidentiary value.

| Situation | Capture point | Evidence purpose |
|---|---|---|
| Successful login | After the authenticated identity/environment is confirmed | Establish execution identity/context |
| Form populated | After input readback and before Save/Submit | Show state before mutation |
| Auto-populated field | After the field is populated/read back, before form disappears | Show actual auto-populated state |
| Validation error | Once the expected error/alert is visible and stable, before dismissal | Show application response |
| Save confirmation | Once confirmation and generated ID are visible, before dismissal | Show save result |
| Compound delete | Capture both error-without-reason and success-after-reason checkpoints | Preserve the two-stage trajectory |
| Persistence check | After reopening/searching the saved item | Show persisted outcome |
| Audit history | After search result/old-new values are visible | Show history verification |
| Export | Preserve downloaded original file plus verification result; capture relevant UI state | Show export and content verification |
| Failure | Immediately after mismatch/timeout/ambiguity, before recovery changes the state | Preserve failure evidence |

## 15.2 Original screenshot and derivative policy

1. Capture the original screenshot bytes from Playwright at the checkpoint.
2. Persist the original unchanged.
3. Record capture time and sequence immediately.
4. Calculate SHA-256 over the original bytes.
5. Create a sidecar metadata manifest referencing the original hash.
6. Append the evidence event to the ordered audit event log.
7. Generate a watermarked/stamped derivative only for human-readable report presentation if needed.
8. Never replace or mutate the original evidence with the derivative.

A stitched image may be useful as a report convenience, but it must not replace the original stage screenshots. The separate originals preserve capture time and state for each checkpoint.

A 36-pixel watermark is not a regulatory requirement. Do not use “FDA Verified,” “FDA Compliant,” or “GxP Validated” banners without formal organisational approval and substantiation.

## 15.3 Evidence metadata manifest

Each evidence artifact must carry at least:

- `run_id`
- `protocol_id` and version
- Original document filename and SHA-256
- Test set/scenario/step/checkpoint IDs
- Capture sequence number
- `captured_at_utc` (RFC 3339/ISO 8601 with `Z` or explicit offset)
- Timestamp source and clock-synchronisation health/status
- Application name/build/version if observable
- Environment
- Executing authenticated user identity or controlled service identity
- User role/profile
- Browser name/version
- Playwright version
- Operating system/runtime version
- Viewport dimensions
- Screen/navigation path
- Evidence type
- Assertion/checkpoint reference
- Original file path/object key
- MIME type, file size and SHA-256
- Related trace/download/observed-state artifact references
- Redaction/classification status where applicable

Do not store password, access token, cookie or raw session ID. A pseudonymous execution/session correlation identifier may be used if the security policy permits it.

## 15.4 Time integrity

- Use a synchronised trusted server clock for capture timestamps.
- Record UTC.
- Record monotonic sequence/timing information to preserve event order within a run.
- Record clock synchronisation/health state and clock offset where available.
- Keep application-displayed local time as a separate observed value when the test expects it.
- Never invent a timestamp after capture or substitute report-generation time for evidence-capture time.

## 15.5 Audit event integrity

Use canonical serialisation for audit events and a sequence-linked hash structure. For example:

```text
entry_hash = SHA256(previous_entry_hash || canonical_event_bytes || artifact_hashes)
```

This makes unauthorised alteration detectable only when the trusted head/checkpoint and signing/storage controls are protected. A hash chain by itself is not tamper-proof: an attacker who can rewrite every event and recompute every hash can recreate a chain.

Required safeguards, subject to the organisation's validated controls:

- Protected signing key held outside the execution worker (e.g. approved KMS/HSM or equivalent).
- Digital signature or keyed seal over audit checkpoints/manifests.
- Append-only/WORM or equivalent tamper-resistant evidence storage where required.
- Access control and separation of duties.
- Retention policy tied to the applicable records/predicate rules.
- Backup, restore and integrity-verification procedures.
- Periodic verification of artifact hashes and audit-chain signatures.
- Complete audit of evidence access/export/deletion/administrative actions.

## 15.6 Playwright traces

Playwright Trace Viewer can support debugging by recording action snapshots, before/after DOM states, screenshots, logs and network activity. It is diagnostic evidence, not a substitute for the checkpoint evidence and validated assertion record.

Trace files can contain sensitive page content, DOM snapshots, network data and screenshots. Store them in controlled, access-restricted storage, redact where required and never upload regulated/sensitive traces to a public viewer. Retain traces according to a documented risk-based policy (e.g. selected for failures or configured controlled runs).

---

# 16. Deterministic Verification and PASS/FAIL Model

This design explicitly rejects an AI-only verdict.

## 16.1 Three layers of evaluation

### Layer 1 — Execution integrity and precondition checks

Examples:

- Correct environment and application identity.
- Authenticated user/role is authorised.
- Browser/runtime is healthy.
- Required locator resolves uniquely.
- Action executes within policy.
- No unreconciled browser/runner failure.
- Required evidence capture succeeded.

This layer classifies execution readiness/integrity. It does not independently decide functional PASS.

### Layer 2 — Deterministic assertion engine (final functional oracle)

Convert the approved expected result into typed assertions and compare them to observed application state. Supported assertion types should include, as applicable:

- Element visible/hidden.
- Exact text or approved text pattern.
- Input value equals expected value.
- Selected option equals expected option.
- Checkbox/toggle state.
- Expected control count/row count.
- Generated identifier exists and is non-empty/valid according to approved ID rules.
- Expected row/entity present or absent.
- Confirmation/alert visible.
- Specific validation feedback shown.
- Field status/code value displayed.
- Persisted value confirmed by a validated read-only UI/API/data-source check.
- Old and new audit-history values both present.
- File download completed and file content/schema/cell values verified.
- Expected page/tab/view is active.

The verifier should use Playwright's auto-retrying assertions where possible, and typed parsers for downloaded file contents. It must retain observed values and assertion result details.

### Layer 3 — AI assistance for explanation only

Qwen may help explain ambiguous prose, summarise a discrepancy or propose a structured assertion for human approval. It must not override deterministic assertion results, assign PASS from similarity, or convert a missing assertion into success.

## 16.2 String matching policy

Do not use broad rules such as:

```python
if "error" in page_text:
    result = "PASS"
```

That can pass on an unrelated error.

Exact text comparison is acceptable when the approved protocol explicitly requires a specific message. Use an approved normalization policy (e.g. whitespace or Unicode normalization) only when documented and testable.

For a generic expectation such as “System shall display error message,” verify the relevant validation feedback is visible and correlated to the attempted action/invalid condition, and verify the prohibited operation did not succeed. Do not pretend a generic word match proves it.

Do not use fuzzy semantic similarity (e.g. score >= 0.65) as the final acceptance criterion.

## 16.3 Positive, negative and compound scenarios

- Positive test: required successful state and confirmation must be observed; unexpected validation errors must be investigated.
- Negative test: the expected validation response must occur and the prohibited mutation must not have succeeded.
- Compound test: every checkpoint must be evaluated in order; intermediate negative and final positive states must both be satisfied where the protocol expects them.
- Persistence test: a UI message alone may be insufficient; perform a permitted readback/search to confirm persistence when the expected result requires it.
- Export test: a download event alone is insufficient; inspect and verify the downloaded file's actual contents.

## 16.4 Network status is not the test oracle

- A 4xx response may be an expected result for a negative validation test.
- A 5xx or network error may indicate infrastructure/application failure, but must be correlated with the scenario and observed state.
- Do not classify every HTTP 4xx as FAIL or every HTTP 2xx as PASS.
- Never use an unverified HTTP status alone as proof that a business record was or was not created.

## 16.5 Final statuses

Use these four externally visible statuses:

- `PASS`: every required expected-result checkpoint passed deterministic verification; required evidence exists and is integrity-verified; execution preconditions were valid.
- `FAIL`: the test executed sufficiently to establish that the application did not meet an approved expected result.
- `BLOCKED`: execution could not safely proceed due to wrong environment, missing permission, unavailable prerequisite, infrastructure outage, or another precondition failure.
- `NEEDS_REVIEW`: protocol interpretation is ambiguous, evidence is incomplete/uncertain, a non-idempotent action may have occurred but cannot be reconciled, or the actual result cannot be determined reliably.

Keep `execution_status` (e.g. completed/failed/blocked) separate from `functional_outcome` (PASS/FAIL/undetermined) internally. Do not turn a runner crash into a functional FAIL without evidence.

## 16.6 PASS rules

A scenario can PASS only when:

1. Document/protocol identity and version were accepted.
2. Environment, identity and role preconditions were satisfied.
3. Every required checkpoint has an approved assertion specification.
4. Every required action completed under policy.
5. Every required assertion passed.
6. Required evidence exists and hashes verify.
7. No unresolved execution ambiguity remains.
8. All compound checkpoint trajectories passed in order.

The protocol-level result is not automatically PASS because most scenarios passed. Apply the protocol's acceptance criteria and QA discrepancy disposition rules.

---

# 17. Caching Architecture

Use three main caches. A cache hit reduces repeated work; it does not bypass live validation or the need to execute the protocol.

## 17.1 Cache 1 — Document Extraction Cache

Stores source-preserving extracted structures/canonical documents.

Key must include:

- Original document SHA-256.
- Extractor/parser version.
- Canonical schema version.
- Any conversion/OCR engine version if applicable.

Never reuse cached extraction when source bytes or parser/schema version differs.

## 17.2 Cache 2 — UI Metadata / Discovery Cache

Stores navigation graph, screen cards, control cards, option inventories and validated locator recipes.

Scope the cache by:

- Application identity.
- Environment.
- Application build/version fingerprint.
- Role/profile.
- Locale.
- Relevant UI/catalog version.

Do not reuse a Validation UI card blindly in Production or across roles/builds. A live pre-action locator check is still required.

## 17.3 Cache 3 — Plan Blueprint Cache

Stores validated plan blueprints, not stale runtime values.

Key must include:

- Protocol source/canonical hash and version.
- Canonical schema version.
- Planner prompt version.
- Qwen model name/revision and serving runtime version.
- UI catalog fingerprint/version.
- Application build.
- Environment and role profile.
- Locale.
- Test-data fixture version.
- Action policy/verification policy version.
- Generator/compiler version.

Do not use a plan if any relevant key dimension differs.

## 17.4 Dynamic values and run-scoped variables

Cache reusable action structure and parameter slots, not resolved dynamic values.

Examples:

- `TEST_RUN_DATE` resolved at execution from approved timezone/rule.
- Case ID generated in the current run stored only in that run's variable store.
- Unique synthetic test data obtained from the fixture/data factory with run scope.

Never reuse yesterday's date, a previous run's case number, another user's data or prior session state unintentionally.

## 17.5 Cache invalidation

Invalidate or revalidate relevant entries when:

- Protocol or source document changes.
- Application build/UI fingerprint changes.
- Role/permissions change.
- Locale changes.
- UI card changes.
- Qwen model/runtime/prompt changes.
- Canonical schema/action policy changes.
- Fixture version changes.
- Locator becomes missing/ambiguous or no longer matches expected role/type.

Invalidate only the affected scope where safe, but never keep a known-bad locator active.

## 17.6 Cache security

Never cache:

- Passwords, cookies, bearer tokens or session IDs.
- Real PHI or patient record contents.
- Unapproved dynamic test values.
- Live DOM snapshots containing sensitive business data.

Use atomic writes, integrity checks, versioned files/records and concurrency-safe locking. Avoid shared mutable global cache objects across concurrent runs.

---

# 18. Security, Privacy, and Environment Controls

## 18.1 Environment model

Every protocol/run must declare its environment explicitly. At minimum support the configured equivalents of:

- Development (if used for engineering only).
- Validation / test environment.
- Production.

The runner must independently verify that the current application environment matches the protocol/approval. Do not rely only on a user-selected label; verify the resolved target URL/environment identity against an allow-listed configuration.

## 18.2 Production gate

Production execution is blocked by default for mutations.

Before any production mutation, require:

- Explicit written organisational approval for the test and account.
- Validated production test-data/record handling policy.
- Authorised role and least-privilege access.
- Defined data retention and cleanup or retention strategy.
- Approved run window and monitoring where required.
- Human approval of the exact action plan where policy requires it.

If not satisfied, permit only approved read-only activities. PQ example protocols explicitly use Production, so this gate is mandatory.

## 18.3 Sensitive data boundaries

- UI discovery stores structure, not patient/case records.
- Do not put PHI/PII into Qwen prompts or embeddings.
- Use synthetic and approved test fixtures for non-production tests.
- If sensitive values can appear in screenshots/trace, apply access classification, retention and encryption. Do not modify raw evidence silently; create a separately labelled redacted derivative only under an approved process.
- Redact secrets and sensitive data from logs.

## 18.4 Credential management

- Use approved secrets manager/vault or controlled runtime injection.
- No secrets in source code, `.env` committed files, logs, database plan cache, UI catalog or model context.
- Audit secret access/use with identity and timestamp.
- Use least privilege and rotation policies.
- Do not persist authenticated storage state unless policy explicitly approves the scope and encryption.
- Do not place passwords, tokens or secret defaults in frontend bundles, API request bodies, protocol/session models, URLs, WebSocket messages, reports or browser-visible state. The client may identify a requested account; the authorized backend resolves credentials through the approved provider.
- Apply centralized redaction to structured logs, exceptions, traces, prompts, model outputs and report metadata. Exclude credentials, cookies, bearer tokens, session secrets and PHI/PII. Validate redaction with focused tests before controlled use.

## 18.6 Authentication, authorization and browser/API boundary

- Use an approved identity provider or authenticated service identity. Define role-based permissions for protocol upload, discovery, planning, plan approval, execution, review, evidence/report access and administration.
- Enforce authorization server-side for every operation and resource. Never trust a UI control, client-supplied role, username, environment label or CORS policy as proof of permission.
- Obtain scoped execution credentials from the approved secret provider only after authenticating the requester and validating the run's environment/role policy. Browser clients must not send passwords or secret material to execution endpoints.
- Protect WebSocket establishment and each run-scoped message with the same identity, authorization and tenant/environment checks as HTTP. Do not put bearer secrets in query strings.
- Until the identity and secret-provider boundary is approved and configured, protected execution and Production mutations remain unavailable.

## 18.7 CORS policy

- Configure explicit trusted origins and only the methods/headers required by the deployed frontend.
- Never combine wildcard origins with credentialed CORS. CORS is a browser origin policy, not authentication or authorization.
- Keep environment-specific CORS configuration controlled and reviewed; do not use permissive defaults in a controlled deployment.

## 18.5 User and run isolation

- Isolate browser contexts per execution run/user.
- Separate artifact folders and data scopes by `run_id`.
- Prevent simultaneous runs from colliding on the same mutable test record/account unless explicitly coordinated.
- Use concurrency locks or run scheduling for shared test data.
- Keep tenant/environment boundaries enforced at API and storage layer.

---

# 19. Reports and Approved Word Templates

The platform should generate controlled deliverables, but it must not invent or replace official organisation templates.

Expected output types may include:

1. **Executed Protocol DOCX** — the approved protocol template populated with actual observed results, status, evidence references, execution identity/date and deviations as permitted.
2. **Evidence Dossier** — organised original screenshots, metadata manifests, hashes, trace/download references and checkpoint mapping, with an index/document in the approved format.
3. **Audit Trail / Integrity Report** — ordered events, actor, timestamps, artifact hashes, signatures/verification state and relevant deviations. Do not call this an “official certificate” unless the organisation defines and approves that deliverable.
4. **Executive Summary** — protocol/run outcome, counts/statuses, deviations and reviewer-ready summary.

## 19.1 Template constraints

- Reuse the approved Word templates/layouts already supplied by the business.
- Do not change headings, tables, pagination, logos, headers/footers, controlled identifiers or signatures without approval.
- Preserve original document and create a separate executed copy.
- Insert actual results only after verification.
- Never write PASS for missing/ambiguous evidence.
- Keep traceability from every report row to source step, checkpoint, assertion and evidence artifact.
- Maintain a template version/hash in the run manifest.

---

# 20. Backend, API, Frontend and Persistence Integration

The existing frontend visual UI should be retained wherever practical. The backend may be rebuilt.

## 20.1 Expected service boundaries

The implementation should use clear layers, for example:

```text
backend/
  app/
    api/                 # FastAPI routes and request/response mapping
    core/                # configuration, logging, security, policy
    domain/              # canonical protocol/run/evidence entities
    schemas/             # Pydantic request/response/model schemas
    services/
      ingestion/         # DOCX and authoring ingestion
      discovery/         # Playwright UI discovery and inventory
      catalog/           # versioned UI catalog repository
      retrieval/         # single UI Mini-RAG retriever
      planning/          # Qwen Planner and structured outputs
      compilation/       # action DSL compiler/validator
      execution/         # Playwright runner and action dispatcher
      healing/           # on-demand locator recovery
      verification/      # deterministic assertions
      evidence/          # screenshot/manifest/audit integrity
      reporting/         # approved DOCX/report generation
      caching/           # extraction/UI/plan caches
    infrastructure/      # database, object storage, Qwen client, secrets provider
    workers/             # background jobs and run orchestration
  tests/
    unit/
    integration/
    fixtures/
```

This tree is conceptual architecture only. It does not declare that packages exist or authorize creating empty folders. Introduce each package/module only in the phase that implements its responsibility, after that phase is explicitly authorized. Adapt names to approved repository/deployment conventions while preserving clear responsibility boundaries.

## 20.2 API contract preservation

During Phase 0, identify frontend-used endpoints and types. Preserve current route paths, methods, request/response fields, status meanings, WebSocket event names/payloads, download behavior and UI workflow by default. Do not remove or change a contract for compatibility reasons unless a human explicitly approves it. An approved breaking change requires an explicit versioned migration, documented compatibility window and rollback path. Do not break AI Author Studio, upload flows, live execution view, session status, report download or evidence navigation unexpectedly.

Potential logical endpoints (final paths must align with the actual frontend contract map):

- Create authoring protocol/session.
- Upload DOCX and inspect extraction status.
- Retrieve protocol extraction/quality report.
- Start/inspect UI discovery job (authorised administrators only).
- Retrieve UI discovery coverage/catalog status.
- Compile/validate plan.
- Approve/reject plan where required.
- Start/monitor execution run.
- Retrieve scenario/checkpoint results.
- Retrieve evidence list/metadata.
- Download executed protocol and evidence dossier.
- Review/record deviation disposition and sign-off using approved organisational controls.

Use asynchronous/background job orchestration for long discovery/planning/execution tasks. Avoid holding a single HTTP request open for a long-running browser run.

## 20.3 Persistence guidance

Reuse the current approved database/object-storage services if the bounded contract inspection confirms they are fit for purpose. Do not add Redis, a vector DB, a new workflow engine or another data store without an explicit need and measured benefit.

Store structured metadata and run state in the approved relational datastore where suitable. Store binary documents/screenshots/traces/downloads in controlled file/object storage with metadata and integrity hashes. Keep catalog/index data versioned. Apply tenant/environment/run scoping in every query.

---

# 21. Observability and Operational Reliability

Every run must be diagnosable without reading raw sensitive data.

Record structured events for:

- Upload received and source hash.
- Extraction started/completed and coverage warnings.
- Identity/environment conflict.
- Discovery start/finish, navigation coverage and unsupported states.
- Catalog version/fingerprint changes.
- Retrieval request, selected cards, scores and token budget.
- Qwen request/model/prompt version/token counts/schema outcome (not raw sensitive prompt content).
- Plan validation/approval.
- Browser context start and environment verification.
- Each action start/end and locator/role summary (no values if sensitive).
- Checkpoint evaluation and actual assertion values according to sensitivity policy.
- Evidence capture time/hash/write result.
- Cache hit/miss/invalidation.
- Healer proposal/validation/approval/write-back.
- Run status and exception/deviation.
- Report generation/template hash.
- Reviewer disposition/sign-off.

Use correlation IDs (`run_id`, `scenario_id`, `checkpoint_id`, `evidence_id`) consistently. Keep logs structured and avoid secrets/PHI.

---

# 22. Failure Modes and Required Behaviour

| Failure | Required response |
|---|---|
| DOCX file corrupt/unsupported | Preserve original, report extraction failure, do not plan |
| Filename/header protocol ID mismatch | Flag identity conflict and BLOCK controlled execution pending review |
| Missing expected result | NEEDS_REVIEW; do not invent an oracle |
| Qwen malformed JSON | One bounded schema-repair attempt; then stop planning |
| Qwen hallucinates field/value | Reject unsupported references/provenance; NEEDS_REVIEW |
| Retrieved UI card from wrong environment/build/role | Reject card and refresh discovery |
| Dropdown requested value not in retrieved shortlist | Query full local/live option source; never choose a substitute silently |
| Dropdown option list virtualized/incomplete | Mark partial; targeted live query or NEEDS_REVIEW |
| Screen missing from UI catalog | Trigger live discovery/Healer only for relevant safe scope |
| Locator matches zero controls | Stop action; healer may propose recovery |
| Locator matches multiple controls | Do not click; scope more precisely or NEEDS_REVIEW |
| Healer proposal unvalidated | Do not execute or promote to trusted cache |
| Browser timeout after possible Save/Submit | Reconcile read-only state; never blindly retry non-idempotent action |
| Application returns expected validation error in negative test | Evaluate against the negative checkpoint; do not mark automatic FAIL based on 4xx |
| Unexpected unrelated validation/server error | FAIL only if expected behaviour is demonstrably not met; otherwise BLOCKED/NEEDS_REVIEW depending on cause |
| Screenshot capture/write failure | Required checkpoint evidence incomplete; do not PASS |
| Hash/signature verification fails | Evidence integrity failure; BLOCK/NEEDS_REVIEW and preserve artefacts |
| Download triggered but file invalid | FAIL if the application failed the explicit export requirement; otherwise classify infrastructure/format issue accurately |
| Production target not explicitly approved | BLOCK mutation |
| Clock out of sync | Flag timestamp trust issue and block evidence acceptance per policy |
| Cache stale | Invalidate/revalidate before action |
| Parallel runs collide on same test data | Lock, isolate or BLOCK conflicting run |

---

# 23. Test Strategy and Acceptance Criteria

The platform itself must be tested. A demo run is not sufficient.

## 23.1 Unit tests

At minimum:

- Canonical schema validation.
- DOCX table/paragraph/merge/reference extraction.
- Preservation of raw source text and source refs.
- Lossless authored-input fixtures for unfamiliar/vague phrases, section directives, additional notes, repetition and conflicting expectations; assert exact original-byte recovery and accounting of every segment.
- DOCX fixtures for unfamiliar identifier formats/labels, varied table/header/metadata layouts, paragraph-based structures and unrecognized content; assert review flags instead of destructive rejection or guessed mapping.
- Scenario/checkpoint mapping and compound trajectories.
- Document identity conflict detection.
- Retrieval relevance, deduplication and scoped card filtering.
- Token-budget calculation and semantic batching.
- Planner JSON/Pydantic validation.
- Fixture provenance and intentional blank-field preservation.
- Action allow-list enforcement.
- Locator uniqueness/role checks.
- Assertion engine per assertion type.
- Evidence manifest/hash/chain/signature operations.
- Cache key composition and invalidation.
- Run status transition rules.

## 23.2 UI discovery integration fixture

Create a controlled mock application with:

- Login page.
- Landing page with multiple nested accordion menus.
- More than one internal route.
- A Manual Case Registration-like multi-section form.
- Text/date/toggle/radio/native-select/custom-select controls.
- A 250-option dropdown.
- A virtualized or paginated option control.
- A search modal and confirmation dialog.
- Tabs and nested accordions.
- A table/grid with input cells.
- A new popup/tab.
- An iframe with accessible controls.
- Open Shadow DOM control and a documented closed Shadow DOM limitation.
- Conditional fields revealed by a safe selection.
- A destructive Save/Submit/Delete control that the discovery engine must not activate.

Acceptance:

- Discovery reaches nested permitted screens, not just the first page.
- It identifies fields and control types.
- It opens and inventories safe dropdowns/options.
- It records partial coverage honestly for virtualized/inaccessible options.
- It explores safe nested tabs/modals/frames.
- It does not trigger destructive actions.
- It avoids duplicate catalog entries across repeated visits.
- It scopes metadata by environment/build/role/locale.

## 23.3 Context and retrieval tests

- Index a large catalog with unrelated screens.
- Query one Reporter scenario and retrieve only relevant cards.
- Query one Audit History scenario and do not include Patient/Questionnaire cards.
- Ensure repeated cards appear once in a batch.
- Ensure full original instructions are preserved.
- Ensure context over-budget causes a valid split, never truncation.
- Ensure a 250-option option set remains local and only relevant candidates enter the prompt.
- Ensure the true exact option can still be retrieved even if it was not in the first shortlist.
- Measure retrieval precision/recall on a labelled test set; do not rely on assumed `<5ms` claims.

## 23.4 Planner tests

- Clear positive scenario.
- Clear negative scenario.
- Compound negative→positive scenario.
- Positive setup→negative submit scenario.
- Missing target test data.
- Intentional blank field.
- Unknown field not in catalog.
- Ambiguous locator.
- Malformed model response.
- Unsupported action and invented value rejection.
- Credential/PHI prompt redaction tests.

## 23.5 Runner and verifier tests

- Navigation with collapsed menus.
- Native and custom dropdowns.
- Table header-to-cell mapping.
- Auto-populated field pre-save readback.
- Form that resets after Save.
- Expected validation error before dismiss.
- Compound deletion trajectory.
- Case ID creation and persistence search.
- MedDRA code display/relationship checks.
- Audit-history old/new values.
- Excel download and content verification.
- Browser crash before action.
- Timeout after possible mutation and safe reconciliation.
- Duplicate locator match must stop.
- No AI-only PASS.
- No network-status-only verdict.

## 23.6 Evidence tests

- Screenshot captured at each required checkpoint.
- Original bytes preserved unchanged.
- UTC timestamp and event ordering present.
- Manifest links to scenario/checkpoint/source document.
- SHA-256 verification detects modified file.
- Chain/signature verification detects altered event/artifact references.
- Missing screenshot prevents PASS where evidence is required.
- Derivative watermark does not overwrite original.
- Trace files are stored under controlled access and redaction policy.
- Clock-sync failure is surfaced.

## 23.7 End-to-end pilot

Begin with a small, approved OQ subset in Validation, using synthetic fixtures and an authorised test account. Only after the system demonstrates extraction, discovery, planning, execution, evidence and verification quality should it progress to the full OQ test sets.

Do not begin automated PQ Production mutations until the production gate is formally approved.

## 23.8 False-pass requirement

For the validated acceptance suite, no known wrong-field error, stale locator, missing checkpoint, failed persistence check, invalid export or evidence-integrity failure may be reported as PASS. Include explicit negative tests proving that the verifier rejects these false-positive patterns.

---

# 24. Phased Implementation Roadmap

Every phase has a scope, deliverables, test gates and a stop point. The agent must not combine phases.

## Phase 0 — Bounded repository contract inspection and clean-slate plan

**Purpose:** understand only what must be preserved from the existing project.

**Allowed inspection:** as specified in Section 5.

**Deliverables:**

- `docs/legacy-contract-map.md`
- `docs/target-package-layout.md`
- `docs/phase-plan.md`
- Proposed API compatibility strategy that preserves observed frontend contracts unless a human explicitly approves a versioned change.
- Legacy modules explicitly not reused.
- List of open decisions.

**Acceptance:** frontend routes, API contracts, database/storage contracts, authentication boundary and template paths are mapped. No bulk legacy source audit performed. No code deleted.

**Stop:** request approval.

## Phase 1 — Canonical schemas and source-preserving DOCX extraction

**Suggested modules:**

- `domain/protocol.py`
- `schemas/protocol.py`
- `services/ingestion/docx_extractor.py`
- `services/ingestion/author_input_adapter.py`
- `services/ingestion/quality_gate.py`
- Unit tests and DOCX fixture set.

**Deliverables:**

- Canonical protocol/test-set/scenario/action/checkpoint/source-ref models.
- Source-preserving DOCX parser.
- Cross-reference handling.
- Extraction coverage report.
- Protocol identity conflict detection.
- Authoring JSON adapter.
- Preservation of source bytes/hash, exact original text, stated test-set/test-case/step/checkpoint identities, structural source references and extraction provenance (parser/version/method/confidence/warnings). Keep normalized identities separate; preserve ambiguity, conflicts and unmapped source content.

**Acceptance:** supplied OQ/PQ documents are regression examples, with their observed structure and unresolved identity/case grouping faithfully represented. Synthetic fixtures vary identifiers, labels, header positions, metadata rows, paragraph/table content and case/set counts. Previously unseen identifiers are retained as source-backed candidates when general format rules match; unfamiliar structures remain recoverable and flagged rather than rejected or guessed. Original bytes and exact content remain retrievable; every source segment is accounted for; stated identities/references/provenance/conflicts remain separate from normalized or proposed interpretations; no source segment becomes executable by extraction. Authored fixtures include unfamiliar/vague phrases, section directives, notes, repetition and conflicting expectations, and verify full original-byte recovery and zero silent text removal.

**Stop:** run Phase 1 tests and obtain approval.

## Phase 2 — Playwright UI Discovery and Inventory Engine

**Suggested modules:**

- `services/discovery/browser_session.py`
- `services/discovery/navigation_traversal.py`
- `services/discovery/dom_inspector.py`
- `services/discovery/option_inspector.py`
- `services/discovery/state_fingerprint.py`
- `services/discovery/coverage_report.py`
- `domain/ui_catalog.py`
- Mock application and integration tests.

**Deliverables:**

- Isolated authorised discovery session.
- Navigation graph traversal beyond landing page.
- Screen/section/control extraction.
- Native/custom dropdown inspection.
- Tables, tabs, accordions, modals, popups, frames and open Shadow DOM support where available.
- Safe discovery policy and non-mutating action gate.
- Coverage report and candidate/validated status lifecycle.

**Acceptance:** discovery tests described in Section 23.2 pass; fields and option metadata are discovered; conditional/unreachable controls are flagged accurately; no mutating action is triggered by discovery.

**Stop:** run Phase 2 tests and obtain approval.

## Phase 3 — UI Catalog persistence and one primary Mini-RAG

**Suggested modules:**

- `infrastructure/catalog_repository.py`
- `services/catalog/catalog_manager.py`
- `services/retrieval/ui_mini_rag.py`
- `services/retrieval/token_budget.py`
- Tests for versioning, scoping, deduplication and retrieval.

**Deliverables:**

- Versioned catalog storage.
- Environment/build/role/locale scoping.
- Navigation graph and card persistence.
- Stable card identity and deduplication.
- Lightweight CPU retrieval.
- Full local option storage and bounded candidate retrieval.
- Tokenizer-aware context budget calculation.

**Acceptance:** retrieval tests pass; wrong environment/build card is rejected; duplicate cards do not bloat context; context overflow creates a valid split; original text is never truncated.

**Stop:** run Phase 3 tests and obtain approval.

## Phase 4 — Qwen Planner, fixture resolution and plan validation

**Suggested modules:**

- `infrastructure/qwen_client.py`
- `services/planning/planner.py`
- `services/planning/prompt_builder.py`
- `services/planning/fixture_resolver.py`
- `services/planning/plan_validator.py`
- `schemas/plan.py`
- Mock/model contract tests.

**Deliverables:**

- Configurable Qwen provider/serving adapter.
- Token-budgeted prompts with no source truncation.
- Structured schema-constrained output where supported.
- Positive/negative/compound planning.
- Value provenance and explicit blank preservation.
- Ambiguity handling.
- Credential/PHI exclusion checks.
- One bounded JSON repair attempt.

**Acceptance:** all planner tests in Section 23.4 pass; no generated value without approved provenance; no arbitrary action; no model-generated verdict.

**Stop:** run Phase 4 tests and obtain approval.

## Phase 5 — Plan compiler and deterministic Python Playwright runner

**Suggested modules:**

- `services/compilation/action_plan_compiler.py`
- `services/execution/playwright_runner.py`
- `services/execution/locator_resolver.py`
- `services/execution/navigation_executor.py`
- `services/execution/action_dispatcher.py`
- `services/execution/run_context.py`
- Runner integration tests.

**Deliverables:**

- Allow-listed Python action DSL.
- Deterministic runner.
- Semantic locator resolution and uniqueness checks.
- Environment and role preflight.
- Isolated contexts and run-scoped variables.
- Native/custom dropdown execution.
- Grid/table resolution.
- Pre-save readback.
- Safe non-idempotent retry/reconciliation policy.

**Acceptance:** all runner tests pass; ambiguous or duplicate locator prevents execution; no arbitrary generated code; no blind retry after uncertain mutation; Python is the only primary runtime.

**Stop:** run Phase 5 tests and obtain approval.

## Phase 6 — On-demand Qwen Healer and controlled write-back

**Suggested modules:**

- `services/healing/healer.py`
- `services/healing/locator_candidate_validator.py`
- `services/catalog/catalog_promotion.py`
- Healer tests.

**Deliverables:**

- Trigger conditions for unknown screen/failed locator.
- Minimal snapshot/context builder.
- Qwen candidate mapping.
- Independent locator validation.
- Candidate/validated/approved/stale lifecycle.
- Versioned write-back and rollback.

**Acceptance:** healer never executes unvalidated proposals; ambiguous match stops; does not modify expected results or fixture provenance; validated updates are scoped by build/environment/role.

**Stop:** run Phase 6 tests and obtain approval.

## Phase 7 — Evidence capture, manifests and audit integrity

**Suggested modules:**

- `domain/evidence.py`
- `services/evidence/capture_service.py`
- `services/evidence/manifest_builder.py`
- `services/evidence/hash_chain.py`
- `services/evidence/signature_provider.py`
- `services/evidence/storage.py`
- Evidence tests.

**Deliverables:**

- Checkpoint-based capture hooks.
- Raw original screenshot preservation.
- Evidence metadata manifest.
- Trusted UTC and sequence recording.
- SHA-256 and protected chain/signature interface.
- Controlled storage and retention hooks.
- Optional report-only derivative watermark.
- Trace artefact policy.

**Acceptance:** all Section 23.6 tests pass; screenshot capture failure prevents relevant PASS; integrity verification catches modified artifacts; no “FDA compliant” claim or replacement of raw images.

**Stop:** run Phase 7 tests and obtain approval.

## Phase 8 — Deterministic verifier and outcome state machine

**Suggested modules:**

- `services/verification/assertion_engine.py`
- `services/verification/status_resolver.py`
- `services/verification/persistence_checks.py`
- `schemas/assertions.py`
- Verification tests.

**Deliverables:**

- Typed assertion library.
- Checkpoint evaluator.
- Positive/negative/compound trajectory handling.
- Persistence and file-content verification interfaces.
- PASS/FAIL/BLOCKED/NEEDS_REVIEW statuses.
- Separate execution status and functional outcome.
- No AI-only verdict.

**Acceptance:** all Section 23.5 verifier tests pass; false-positive patterns are rejected; ambiguous state cannot PASS.

**Stop:** run Phase 8 tests and obtain approval.

## Phase 9 — Reporting, template preservation and frontend/API integration

**Suggested modules:**

- `services/reporting/executed_protocol.py`
- `services/reporting/evidence_dossier.py`
- `services/reporting/audit_report.py`
- `api/routes/` for new/compatible routes.
- Frontend API adapter changes only where required.

**Deliverables:**

- Populate approved DOCX templates.
- Evidence dossier/index.
- Audit-trail/integrity report.
- Executive summary.
- Compatible FastAPI endpoints/background job status.
- Existing frontend UI wired to new contracts.
- Download/report access controls.

**Acceptance:** template formatting and controlled identifiers are preserved; every reported result traces to an assertion and evidence artifact; frontend author/upload/live-view/report flows still work.

**Stop:** run Phase 9 tests and obtain approval.

## Phase 10 — End-to-end OQ pilot, security and operational hardening

**Purpose:** validate the complete system on a small approved subset before the full protocol.

**Deliverables:**

- End-to-end Validation environment pilot with synthetic data.
- OQ subset execution report.
- Performance/manual-baseline comparison.
- Security/privacy review.
- Recovery, concurrency, backup and restore tests.
- Known limitations and operational runbook.
- Production gate design review for PQ.

**Acceptance:** no known false PASS in the approved acceptance suite; evidence completeness/integrity accepted by reviewers; protocol coverage gaps are reported; measured time savings are documented; production mutations remain blocked without formal approval.

**Stop:** request QA/technical approval before expanding scope or entering Production.

---

# 25. Definition of Done for the Platform

The platform is not “done” simply because all phases compile.

It is ready for controlled pilot only when:

- [ ] Existing frontend contract map is reviewed and the user-facing design is preserved.
- [ ] DOCX extraction preserves source content and references.
- [ ] Protocol identity conflicts are detected and block controlled runs.
- [ ] UI discovery explores authorised nested pages beyond the landing page.
- [ ] Field and dropdown option metadata are discovered and versioned.
- [ ] Discovery does not execute unapproved mutations or store PHI in the catalog.
- [ ] Mini-RAG retrieval is scoped, deduplicated and evaluated.
- [ ] Context budgeting uses the configured tokenizer and never truncates source instructions.
- [ ] Qwen output is schema-validated and uses approved data provenance.
- [ ] Credentials and PHI are excluded from Qwen and logs.
- [ ] Generator emits only the approved Python action DSL.
- [ ] Playwright runner validates locator uniqueness/actionability.
- [ ] Healer proposals require independent validation and controlled promotion.
- [ ] Evidence is captured at every required checkpoint.
- [ ] Original screenshots and artifacts remain unchanged.
- [ ] Evidence metadata, timestamp, hash and audit integrity are verifiable.
- [ ] Deterministic assertion engine handles positive, negative and compound scenarios.
- [ ] No AI-only PASS or fuzzy-similarity PASS exists.
- [ ] PASS/FAIL/BLOCKED/NEEDS_REVIEW semantics are enforced.
- [ ] Reports preserve approved templates and complete traceability.
- [ ] Concurrency, security, backup/restore and failure recovery are tested.
- [ ] Validation/QA stakeholders approve the pilot.

---

# 26. Explicitly Deferred / Out of Scope Unless Approved

Do not add these by default:

- Multiple overlapping UI RAG systems.
- An autonomous agent with unrestricted browser and shell tools.
- LLM-generated Python/JavaScript execution.
- A TypeScript browser runner alongside the Python runner.
- Direct database writes to create test records.
- Unbounded scraping of all patient/case/business records.
- Exhaustive enumeration of huge terminology/product databases when the UI exposes a search interface instead.
- Automatic Production mutations or cleanup.
- Automatic approval/signatures.
- A claim of FDA/GxP compliance based solely on architecture.
- An LLM verdict for ambiguous expected results.
- Redis/vector database/new orchestration platform without measured need.
- Rewriting the frontend UI solely for architectural preference.

---

# 27. Regulatory and Technical Reference Material

This architecture is an engineering design intended to support controlled test execution and evidence generation. It is not a legal/regulatory determination. The organisation's QA/CSV/Regulatory stakeholders must assess intended use, predicate-rule applicability, Part 11 scope, data classification, retention, electronic signatures, validation approach and applicable SOPs.

The FDA Part 11 Scope and Application guidance states that Part 11 applies to electronic records required by FDA predicate rules or submitted electronically, and discusses the Agency's interpretation/enforcement approach. Do not assume every screenshot automatically falls under every Part 11 provision; perform the organisation's documented applicability assessment.

Relevant sources (official/current documentation checked on 2026-11-03):

1. [FDA — Part 11, Electronic Records; Electronic Signatures: Scope and Application (2003 guidance)](https://www.fda.gov/regulatory-information/search-fda-guidance-documents/part-11-electronic-records-electronic-signatures-scope-and-application)
2. [eCFR — 21 CFR Part 11, including §11.10 controls for closed systems](https://www.ecfr.gov/current/title-21/chapter-I/subchapter-A/part-11)
3. [FDA — Computer Software Assurance for Production and Quality Management System Software (February 2026 guidance)](https://www.fda.gov/regulatory-information/search-fda-guidance-documents/computer-software-assurance-production-and-quality-management-system-software). Applicability to this pharmacovigilance validation automation use case must be assessed; do not automatically assume it applies to every component.
4. [FDA — General Principles of Software Validation](https://www.fda.gov/regulatory-information/search-fda-guidance-documents/general-principles-software-validation). The FDA page notes that the 2025 Computer Software Assurance guidance supersedes Section 6 of the older guidance for its stated scope; consult current guidance and applicability.
5. [Playwright Python — Page API](https://playwright.dev/python/docs/api/class-page)
6. [Playwright Python — Locator API](https://playwright.dev/python/docs/api/class-locator)
7. [Playwright Python — Auto-waiting and actionability](https://playwright.dev/python/docs/actionability)
8. [Playwright Python — Frames](https://playwright.dev/python/docs/frames)
9. [Playwright Python — Downloads](https://playwright.dev/python/docs/downloads)
10. [Playwright Python — Trace Viewer](https://playwright.dev/python/docs/trace-viewer)
11. [Playwright Python — Tracing API](https://playwright.dev/python/docs/api/class-tracing)
12. [vLLM — Structured Outputs](https://docs.vllm.ai/en/latest/features/structured_outputs/). Verify compatibility with the exact Qwen model, tokenizer and serving runtime deployed.
13. [Pydantic — Models](https://docs.pydantic.dev/latest/concepts/models/) and [JSON Schema](https://docs.pydantic.dev/latest/concepts/json_schema/).
14. [python-docx — Documentation](https://python-docx.readthedocs.io/en/latest/). Validate merged-cell and OOXML behaviour against real protocol fixtures.
15. [OWASP — Secrets Management Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html)
16. [OWASP — Logging Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html)

Do not cargo-cult API calls from these links. Check the installed library versions and exact capabilities in the target environment before implementing. Pin and test dependency versions rather than relying on an unpinned “latest” package.

---

# 28. Master Prompt for Codex / Any AI Coding Agent

Copy the prompt below after adding this file to the repository. The agent must obey the phase gate and must not begin by analysing the entire legacy codebase.

```text
You are the Principal Software Architect and Senior Implementation Engineer responsible for building the Clinevo OnePV Test & Validation Automation platform.

AUTHORITATIVE SPECIFICATION
Read `CLINEVO_TEST_VALIDATION_AUTOMATION_MASTER_SPEC.md` completely. It is the source of truth for the target architecture, safety rules, contracts, phases and acceptance criteria. The earlier `master_v5_production_spec.md` and old implementation are historical references only. If they conflict with this specification, follow this specification.

MISSION
Implement the system described in the master specification exactly and incrementally. The intended product accepts normal-English authored test cases and uploaded DOCX validation protocols, preserves their source and checkpoint semantics, discovers the authorised application UI beyond the landing page (including fields and dropdown options), retrieves bounded UI context through one primary Mini-RAG, uses Qwen to produce structured plans, executes only an allow-listed Python action DSL through deterministic Playwright, uses a controlled on-demand healer, captures checkpoint-level timestamped evidence, determines results through deterministic assertions, and generates traceable reports using approved templates.

IMPORTANT LEGACY-CODE INSTRUCTION
The existing codebase contains legacy implementation and hardcoded logic that may be poor quality. Do NOT spend tokens reading every source file or trying to understand every old implementation detail. Do NOT preserve old backend logic merely because it exists. Do NOT perform a bulk codebase audit.

First inspect only the bounded contract surfaces:
1. Repository tree, excluding generated/dependency/cache folders.
2. Dependency manifests and runtime/deployment configuration.
3. Frontend routes/layout and the AI Author Studio, upload, live execution and report UI components.
4. Frontend API client/service calls and TypeScript request/response types used by those components.
5. The exact FastAPI routes and Pydantic schemas serving those frontend calls.
6. Relevant database migrations/table schemas and document/evidence storage contracts.
7. Authentication/secret-provider interfaces (never display secret values).
8. Existing approved DOCX template paths and report download contracts.
9. Current test commands.

Use targeted searches and read only relevant code sections. Do not read all legacy `.py` or `.tsx` files. Do not inspect minified/generated files or node_modules. Produce `docs/legacy-contract-map.md` documenting what the existing frontend depends on, which data contracts must be retained/versioned, what backend pieces will be replaced, and what remains unknown. Preserve the existing frontend visual UI and user workflow wherever practical.

CLEAN-SLATE IMPLEMENTATION INTENT
The backend may be rebuilt using a clean modular structure. Reuse only sound, necessary frontend/API/data/auth/storage contracts. Do not copy brittle old modules, hardcoded dictionaries, regex-driven natural-language parsers, string-based pass/fail logic or unrestricted agent tools. Do not delete/archive legacy code or perform destructive migrations without explicit approval. Use a new branch and preserve rollback options.

NON-NEGOTIABLE ENGINEERING RULES
- Execute only the phase explicitly requested by the human.
- Never start a future phase early.
- No hardcoded OnePV-specific test data, field lists, dropdown values, clinical examples, validation messages or guessed selectors.
- Fixed framework schemas, action allow-lists, safety policies and assertion primitives are required and are not prohibited hardcoding.
- Preserve source document text and references. Never silently strip “noise” or truncate procedures/expected results.
- Use token-budget-aware batching with the configured Qwen tokenizer; do not rely on a fixed 25-step batch limit.
- Index the reachable authorised UI broadly, but retrieve only relevant deduplicated cards for each planning unit.
- Initial UI discovery must reach nested menus/screens and inspect fields, native/custom dropdown options, tabs, grids, modals and accessible frames, using read-only behaviour by default.
- Do not save/submit/delete/approve/sign/send or mutate real records during UI discovery.
- Keep PHI/PII, credentials, cookies and tokens out of Qwen prompts, UI catalog and logs.
- Authenticate and authorize protected HTTP, WebSocket and storage/report operations server-side. Resolve execution secrets through an approved runtime provider after authorization; never use browser-submitted passwords or secret defaults. Redact sensitive values and use explicit trusted-origin allow-lists for credentialed CORS.
- Preserve existing frontend/API/WebSocket contracts by default. A breaking behavior or shape change requires explicit human approval, versioning, and a documented migration/rollback plan.
- Treat the target package tree as conceptual; create each package only in the phase that implements it after that phase is explicitly authorized.
- Qwen generates typed plans only; it never executes code or determines final PASS/FAIL.
- Generator outputs a Python-compatible allow-listed action DSL, not executable TypeScript or arbitrary Python/JavaScript.
- Playwright validates locator uniqueness, role, scope and actionability before acting.
- The Healer proposes candidate recovery only; validate before execution and controlled cache promotion.
- Capture original evidence at every required expected-result checkpoint. Store raw screenshots unchanged with sidecar metadata and SHA-256. Watermarks are derivatives only.
- Use deterministic assertions as the final test oracle. Exact text comparison is allowed only when the protocol explicitly requires that text. Never use a generic “error” substring or fuzzy LLM similarity as PASS.
- Support PASS, FAIL, BLOCKED and NEEDS_REVIEW, with execution status separated from functional outcome.
- Do not blindly retry uncertain non-idempotent Save/Submit/Delete actions.
- Production mutations are blocked unless explicit organisational gates/approvals and test-data controls are satisfied.
- Do not make unsupported FDA/GxP compliance claims.

PHASE CONTROL
The human will tell you which phase to execute, e.g. “Execute Phase 0 only” or “Execute Phase 1 only.” If the requested phase is not stated, perform Phase 0 bounded inspection only and stop. For the requested phase:
1. Restate the phase objective and exact files that will be created/changed.
2. Confirm dependencies and acceptance tests.
3. Implement only that phase.
4. Run its tests plus all required preceding-phase regression tests.
5. Show exact terminal commands and actual output. Do not fabricate or summarise away failures.
6. Report changed files, tests, known issues, deviations and open decisions.
7. Stop and wait for human approval before the next phase.

Do not claim the full platform is complete after a partial phase. Do not claim regulatory compliance or production readiness without the validation and approvals required by the specification.

FIRST ACTION
Begin with Phase 0 only: perform the bounded contract inspection, create the contract map and proposed target package layout, and stop. Do not implement application logic until the human reviews and approves Phase 0.
```

---

# 29. Reusable Phase Execution Prompt

After Phase 0 is approved, reuse this prompt by replacing `N` with the approved phase number and providing any explicit phase-specific instruction.

```text
Phase 0 / prior required phases have been approved. Execute PHASE N ONLY from `CLINEVO_TEST_VALIDATION_AUTOMATION_MASTER_SPEC.md`.

Before coding:
- Read the Phase N section and its acceptance criteria.
- Review `docs/legacy-contract-map.md` and only the exact files/contracts required for this phase.
- List files you will create/change and explain why.

During implementation:
- Do not implement any later phase.
- Do not widen scope without explaining why and obtaining approval.
- Follow all non-negotiable rules in Section 0.
- Add focused unit/integration tests for this phase.
- Keep source provenance, security and failure behaviour explicit.

Before stopping:
- Run the Phase N tests.
- Run all required preceding-phase regression tests.
- Paste actual command output and report pass/fail counts.
- List changed files, design decisions, limitations and unresolved questions.
- Confirm no unapproved future-phase work was performed.

Stop and wait for human approval. Do not begin Phase N+1.
```

---

# 30. Final Architecture Lock Statement

The approved target is a **source-preserving, UI-discovery-first, context-budgeted, Qwen-assisted, deterministic Playwright test execution platform with controlled self-healing, checkpoint-based evidence and deterministic verification**.

The most important invariants are:

1. Both authored and uploaded tests converge on one canonical protocol model.
2. The complete reachable authorised UI is inventoried beyond the landing page, including actual fields and safe dropdown option discovery.
3. The UI catalog can be large; Qwen context remains small, relevant, deduplicated and token-budgeted.
4. Test data has explicit provenance and is not invented by the model.
5. Qwen plans; the Python compiler validates; Playwright executes.
6. The Healer proposes; independent checks and approval determine reuse.
7. Evidence is captured at each meaningful expected-result checkpoint, timestamped and integrity-protected.
8. Deterministic assertions determine outcomes; an LLM never grants PASS.
9. Production actions are subject to explicit authorisation and data-safety gates.
10. Implementation is phase-by-phase, test-gated and human-approved.

**This document is the implementation baseline. Do not simplify away these invariants for speed or convenience.**
