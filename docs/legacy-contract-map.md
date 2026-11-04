# Legacy Contract Map — Phase 0

**Inspection date:** 2026-11-03 22:44 Asia/Kolkata
**Scope:** bounded, read-only contract inspection and documentation amendment. Existing application code, dependencies, migrations, and deployment configuration were not modified.

## Repository and runtime

- Frontend: React 18 + TypeScript + Vite (`frontend/package.json`). The Vite dev server uses port 5173 and proxies `/api` to `http://localhost:8000` and `/ws` to the FastAPI backend.
- Backend: FastAPI/Uvicorn, Pydantic, `python-docx`, Playwright, Groq, pytest, HTTPX, websockets, and multipart support are listed in `backend/requirements.txt`. No Python version pin or Python package/build manifest was found in the inspected repository tree.
- No database migration/schema, SQL, ORM, Supabase/Postgres client, object-storage configuration, Docker/compose file, or deployment manifest was found in the bounded repository inventory.
- The current branch was `main` and the worktree was clean before this Phase 0 documentation work.

## Frontend experience to preserve

There is no router; the UI is a single page mounted by `frontend/src/main.tsx` and composed by `frontend/src/App.tsx`. Preserve the current dark header and three-pane validation workspace, including:

- `TopHeaderBar`: protocol upload, sample selection, execution controls and executed-DOCX download.
- `LeftTraceabilityPane`: trace stages, approval prompts and artifacts.
- `MiddleSequencePane`: ordered protocol steps and statuses.
- `RightDocInspector`: source-document preview and selected-step details.
- `LiveBrowserModal`: live Playwright viewport/WebSocket state.
- `ArtifactModal` and `ScreenshotLightboxModal`: trace/artifact and screenshot inspection.

The source DOCX is rendered in-browser with `docx-preview`. `frontend/src/types.ts` defines the public client model: `ProtocolSession`, `ProtocolStep`, `TraceStage`, `ReadinessFlag`, and `SimulationMode`. The session carries protocol metadata, aggregate counts, trace stages and steps. Each step carries source/procedure/expected-result fields, execution status, observations and screenshot URLs. Current status literals do not include the target architecture's full `NEEDS_REVIEW` outcome; any contract evolution needs an explicit compatibility/versioning plan.

## Frontend-used HTTP and WebSocket contracts

| Method / path | Request from UI | Observed response/behaviour |
|---|---|---|
| `GET /api/list-sample-protocols` | None | `{protocols: [{filename, size_kb}]}` |
| `POST /api/upload-protocol` | Multipart field `file` (DOCX) | `ProtocolSession` JSON |
| `POST /api/load-sample-protocol` | Multipart field `filename` | `ProtocolSession` JSON |
| `GET /api/raw-protocol/{session_id}` | None | Original DOCX file download for client preview |
| `POST /api/execute/{session_id}` | JSON: `sim_mode`, `username`, `password`, `enterprise`, `requires_approval`, `headless`, `max_steps` | `{status, session_id}`; execution continues asynchronously in a worker thread |
| `POST /api/approve-login/{session_id}` | Empty POST | `{status}` (`approved` or `no_event_found`) |
| `POST /api/approve-review/{session_id}` | Empty POST | `{status}` (`review_approved` or `no_event_found`) |
| `POST /api/halt-execution/{session_id}` | Empty POST | `{status: halted}` |
| `GET /api/download-executed-docx/{session_id}` | None | Executed DOCX as attachment |
| `WS /ws/session/{session_id}` | WebSocket connection | JSON events consumed by UI: `FRAME`, `STEP_UPDATE`, `WAITING_FOR_LOGIN_APPROVAL`, `HUMAN_REVIEW_REQUIRED`, `EXECUTION_COMPLETE` |

`GET /api/health`, `GET /api/session/{session_id}`, and static `/api/artifacts/screenshots/...` are also served by FastAPI. The current frontend does not call the health or session GET routes in the inspected call sites; screenshot URLs are embedded in step data and opened by the UI. Preserve or deliberately version these routes if external consumers rely on them.

The upload and sample endpoints return the backend's Pydantic `ProtocolSession.model_dump()` representation. The client type currently expects keys including `session_id`, `filename`, `document_no`, `version`, `effective_date`, `title`, `objective`, `scope`, totals/coverage fields, `git_commit_sha`, `readiness_flags`, `trace_stages`, and `steps`. `ExecuteRequest` currently supplies credential fields with defaults; the frontend also contains credential prefill state. This is a material security finding: credentials are currently part of the browser-to-server execution payload and defaults exist in source. Values are intentionally omitted here. Phase 0 did not change this behavior. The target contract prohibits this pattern: the authenticated client identifies the requested account/run, and the authorized backend obtains credentials from an approved secret provider only after authorization.

## Persistence and file contracts

- Active session state, plans, specs, approval events, halt flags, source paths and WebSocket connections are process-local Python dictionaries in `backend/main.py`; no durable database contract was found.
- Uploaded/sample DOCX files are stored under `backend/uploads/`.
- Generated reports and other artifacts are stored under `backend/artifacts/`; screenshots are under `backend/artifacts/screenshots/` and exposed by a `StaticFiles` mount.
- There is no observed database table/schema or object-store interface to preserve. Session persistence, restart recovery, access control, retention, concurrency and multi-process behavior remain undefined.
- `GET /api/session/{session_id}` synthesizes screenshot URLs based on files present on disk. The artifact download route populates an executed copy from the source document and returns it as a DOCX attachment.

## Authentication and secret boundary

- No authentication middleware, user/session identity provider, vault client, or explicit secret-provider interface was found in the inspected API/configuration surfaces.
- `backend/main.py` loads dotenv files and passes request-body credential fields to the Playwright runner. The frontend maintains credential form state; default values are embedded in source and omitted from this map. Do not treat dotenv loading as a secrets-management contract.
- The API currently has wildcard CORS origins/methods/headers with credentials enabled. Authentication, authorization, secret injection, redaction and allowed-origin policy require an approved design before controlled use.
- Target requirements: authenticate and authorize each protected HTTP, WebSocket, source-file, screenshot, report and storage operation server-side; scope access by role, tenant, run and environment; deny by default; audit decisions without recording secrets. Obtain scoped runtime credentials from an approved provider, never from browser-submitted passwords or source defaults. Centrally redact secrets/PHI from logs, traces, exceptions and model context. Credentialed CORS must use explicit trusted-origin allow-lists; wildcard origins are prohibited, and CORS does not replace authorization.

## Documents, templates, reports

- No separate approved DOCX template path or template registry was found. The current report endpoint takes the uploaded/sample source DOCX, copies and edits it through `backend/docx_writer.py`, then appends an evidence section where screenshots are available.
- Source documents reside in `backend/uploads/`; generated examples/artifacts reside in `backend/artifacts/`. These are runtime input/output locations, not evidence that a controlled template has been approved.
- `GET /api/download-executed-docx/{session_id}` returns `application/vnd.openxmlformats-officedocument.wordprocessingml.document` with an `Executed_...` attachment name. No evidence dossier or separate audit-integrity report contract was found.
- The output writer contains fallback values and template/table assumptions. Do not use those as target business rules or as proof of an approved template. Confirm the authoritative template/version/hash and permitted fields with the document owner/QA.

## Existing checks and test commands

- `frontend/package.json` defines `npm run build` (`tsc && vite build`), `npm run dev`, and `npm run preview`; it has no test script.
- `backend/requirements.txt` includes `pytest`. Existing test modules include `test_phase1.py`, `test_phase3.py`, `test_live_mcr.py`, `test_fail_mode.py`, `test_exec_screenshots.py`, `test_coverage_gate.py`, and `test_review_continue.py`; separate `verify_phase1.py` through `verify_phase5.py` and `verify_e2e.py` scripts are present.
- No repository-level pytest configuration, documented test command, CI workflow, or test runner script was found. `python -m pytest backend` is the conventional candidate for collecting backend `test_*.py` files, but it is not documented or verified by this read-only inspection. The `verify_*.py` scripts are not pytest-discovery tests by filename and need their intended invocation documented separately.
- Phase 0 created no test code and ran no application tests. Verification is recorded in `harness/BUILD_LOG.md`.

## Compatibility strategy

Keep the React UI and its core workflow. Preserve current route paths, methods, request/response fields, status meanings, WebSocket event names/payloads, download behavior and workflow by default. Do not break or remove an existing contract unless a human explicitly approves the change; an approved breaking change needs a versioned migration, compatibility window and rollback plan. Prefer stable protocol/run/evidence resources and asynchronous job status while preserving compatibility endpoints during migration. The observed contracts are compatibility requirements, not a reason to preserve legacy internals. Introduce durable persistence and controlled document storage only after the responsible service and retention/access controls are approved; no current DB/storage service has been established by this inspection.

## Legacy implementation not selected as target architecture

The existing files are retained unchanged. The following are legacy implementation surfaces, not approved target design components:

- `backend/main.py`: monolithic route/orchestration module, process-local dictionaries and worker-thread run orchestration.
- `backend/schemas.py`: mixed extraction/planning/runtime compatibility models and legacy status literals.
- `backend/extractor.py`: current extraction heuristics and hardcoded fallback metadata; not a source-preserving canonical model.
- `backend/agents.py` and `backend/check_coverage.py`: legacy planning/generation/gating surfaces requiring targeted replacement review; model configuration and authorization boundaries are unconfirmed.
- `backend/playwright_runner.py`: legacy execution implementation; not a source of the target action-DSL/security contract.
- `backend/docx_writer.py`: current report population logic with inferred table conventions and fallback values; not an identified approved template/report contract.

This is a contract-level disposition, not a line-by-line audit. No other legacy files were bulk-read.

## Open decisions and unknowns

1. Confirm the approved DOCX template(s), controlled identifiers, template versions/hashes, and permitted report changes.
2. Select the approved durable database and binary evidence storage services, including retention, backup, access and tenancy boundaries.
3. Define authentication/authorization, approved secret injection, credential rotation, CORS and role/environment authorization.
4. Decide how current sessions and WebSocket events map to durable protocol/run/job resources. Preserve all observed contracts by default; if an external contract change is proposed, identify affected consumers and obtain explicit approval for its versioned migration/compatibility window/rollback.
5. Approve identity-provider, role mapping, secret-provider interface, secret rotation/audit, redaction policy and allowed CORS origins; address the observed browser/source credential pattern in a separately authorized implementation phase.
6. Establish documented backend test and `verify_*.py` invocation commands and CI coverage.
7. Identify supported Python/Node runtimes and deployment topology; no pins/manifests were found in the bounded inventory.
8. Confirm report download authorization and screenshot/evidence access controls (part of the server-side authorization boundary).

## Responsibility boundaries

- **Discovery** observes authorized live UI and returns observations, coverage and candidate metadata. It does not execute protocol scenarios or own durable catalog promotion.
- **Catalog** validates, versions and persists eligible UI metadata and lifecycle state.
- **Mini-RAG** retrieves scoped catalog records for planning; it does not crawl the UI or mutate the catalog.
- **Planning** reads canonical protocol/fixture/UI context and proposes a typed plan; it does not compile or execute browser actions.
- **Compilation** validates and converts an approved plan to the allow-listed Python DSL.
- **Execution** alone runs validated DSL actions through Playwright; it does not perform catalog discovery or promotion.

## Phase 1 source-preservation requirements

Retain original document bytes and SHA-256, exact original text for every extracted source segment, stated test-set/test-case/scenario/step/checkpoint identities, structural source references, parser/version/method/confidence/warnings, and source-to-canonical mappings. Store normalized identities separately. Preserve and flag ambiguity, conflicts, unsupported structures and unmapped content rather than silently resolving or discarding them.

