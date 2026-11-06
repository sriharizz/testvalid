# Phase 02 Context — Playwright UI Discovery

## Current phase and authorization
- Phase 2 is explicitly authorized; it is incomplete pending live discovery and a coverage report.
- Phase 3 is not authorized. Do not implement catalog persistence or later-phase work.
- The target is only the OnePV development frontend. Existing Clinevo portal/frontend/API contracts remain unchanged.
- Phase 0–2 handoff files are saved in the current worktree but remain uncommitted/unstaged. The user will create a branch and push from their IDE.

## Implementation
- `backend/app/domain/ui_discovery.py`: typed observations for screens, sections, controls/options, tables, relationships, evidence and coverage/issues.
- `backend/app/services/discovery.py`: structural DOM metadata inspection; safe tabs/expanders/dropdowns/dialog affordances; same-origin navigation; authentication boundary; 403 stop; URL sanitization; isolated Edge launch and manual-auth pause.
- `backend/tests/unit/test_ui_discovery.py`: synthetic fixture pages covering navigation, controls, options, tabs, dialogs, table structure, login boundary, 403 and record-like links.
- Live OnePV policy withholds option labels and lookup values. Table cell/row content and form values are not read. No screenshots or authenticated state are persisted.
- The CLI writes the sanitized `UIDiscoveryResult` to `backend/artifacts/ui_discovery_live.json` and prints a completion summary; it still lacks progress updates during long runs.
- Historical live settings used a 5-screen/5-navigation/5-interaction cap. The current workflow-scoped runner uses limits of 100 screens, 100 navigation visits and 300 safe interactions; these remain configurable through `DiscoveryPolicy`.

## Environment and browser diagnosis (2026-11-04)
- Execution environment: local Windows 10, not WSL/container; Python 3.11.9 at `C:\Program Files\Python311\python.exe`.
- Microsoft Edge is installed at `C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe`.
- A headed Playwright launch from a background/non-PTY command did not surface a window in the user's desktop. A corrected `tty=True` interactive launch opened `about:blank`; Playwright controlled the page, reported its URL, and the desktop window inventory confirmed an Edge window with a nonzero handle. This did not navigate to OnePV.
- For the login flow, launch from an interactive Windows terminal/PTY attached to the desktop. The terminal prompt and visible Edge window must both be available to the user.

## Live attempts and actual outcomes
1. The user supplied the development login URL in chat. A visible Edge window opened and the user authenticated manually. The run then traversed with the original high limits (100 screens/300 interactions) for several minutes without progress output or a completion summary. It was interrupted to reduce unnecessary traffic. No live coverage report was produced.
2. Limits were reduced to 5 screens/5 navigations/5 safe interactions and 1-second timeouts. The capped login page was opened again. The user indicated login was complete, but the terminal confirmation was interrupted before being delivered; that process then stopped at the auth boundary. No capped discovery was performed.
3. The login window/process has since been closed. Do not assume the user remains authenticated. A fresh run requires a fresh manual login.

## Test/check evidence
- `python -m py_compile backend/app/domain/ui_discovery.py backend/app/services/discovery.py backend/tests/unit/test_ui_discovery.py` — exit 0 before the final cap/cleanup changes.
- `python -m pytest backend/tests/unit/test_ui_discovery.py -k live_policy -q` — 1 passed, 4 deselected before the final cap/cleanup changes.
- `python -m pytest backend/tests/unit/test_ui_discovery.py -vv -s` — stalled at the first Edge fixture test; interrupted without a test result. Do not claim the Edge fixture suite passes.
- No test or compile check was run after the final cap/cleanup edits.

## Resume procedure
1. Read root `AGENTS.md`, `harness/PHASE_EXECUTION_PROTOCOL.md`, `harness/PROJECT_STATUS.md`, this file, the Phase 2 build card, and the relevant Master Spec Phase 2 sections.
2. In an interactive PowerShell terminal attached to the user's Windows desktop, set the process-only target and start the runner with a PTY:
   ```powershell
   $env:ONEPV_BASE_URL = 'https://dev.one-aipv.com/login'
   python -m backend.app.services.discovery
   ```
   Do not put credentials in the environment or project files.
3. If login is required, leave the visible page open. The user enters credentials. Wait for the user's explicit “done” message, then send `AUTHENTICATED` to the waiting terminal in that same process.
4. Let the conservative capped pass finish. If it is slow, check the process/window first; do not repeatedly switch browsers or bypass access controls. If 403 appears, stop and record sanitized evidence only.
5. Review the result for actual live coverage and safety; record results and limitations in the harness. Broaden limits only after considering request volume with the user/team. Keep fixture results separate.
6. Stop after Phase 2. Do not begin Phase 3.

## Open issues
- The discovery loop currently emits a summary only at completion and lacks progress updates; quiet output cannot distinguish a slow run from a stuck run. A narrowly scoped progress indicator may be added within Phase 2 if necessary, without recording page text or sensitive values.
- The current live artifact exists but is PARTIAL: 1 screen, 0 controls, 2 navigation visits and 4 issues; it does not show that the selected workflow was reached.
- Previous build logs and the new handoff disagree on test counts/results. The latest workflow-scoped changes were not tested; Python is unavailable on PATH in this worktree.
- Safe nested navigation and deep workflow coverage still need focused automated verification and a supervised live run; inaccessible or unsafe sections remain unknown.

## Current verified handoff (2026-11-04 18:20 IST)
- Supersedes the older “no live run/tests” notes above: the user later explicitly asked to run the URL and log in. A supervised development pass was completed after manual authentication.
- Full regression command ` .\venv\Scripts\python.exe -m pytest backend/tests/ -v` — 39 passed in 46.75s. Focused Phase 2 file has 13 passing tests.
- A live pass first exposed that the actual menu trigger used `.hoverBox` without `aria-haspopup`; the safe interaction candidate selector and fixture were updated. The subsequent pass reached `Manual Case Registration` (`workflow_match_status=reached`) and returned PARTIAL: 12 screens, 954 controls, 546 option counts, 63 issues. Breakdown: 45 safe dropdown timeouts, 3 dialog, 3 expand, 3 tab timeouts, and 9 current-page navigation not activated.
- Artifact: `backend/artifacts/ui_discovery_live.json`. Discovery withheld option labels/selected values and field values. No form filling, save, submit, or other business mutation occurred. Manual authentication was not recorded; browser session closed.
- Remaining Phase 2 work: improve safe interaction reliability and explain/resolve inaccessible states, then obtain sufficient live coverage. Phase 2 is incomplete; Phase 3 remains unauthorized.

## Field-to-section mapping update (2026-11-04 18:52 IST)
- The user clarified that the immediate useful discovery artifact is all visible form fields mapped to their containing section(s). Keep the launch guidance (product URL + workflow) and workflow navigation; do not ask the user to guide each field.
- Each screen now has `form_fields` separate from general `controls`, so buttons, navigation items and tabs do not pollute the field list. Fields include value-bearing controls such as text inputs, textareas, selects/comboboxes, checkboxes, radios, switches and contenteditables.
- `UIControlObservation.label_match_status` is `associated` or `missing`; `section_path` preserves nested headings including duplicate names. Field locator recipes are semantic label/section candidates, explicitly unvalidated and free of observed-position indexes. Runtime must still validate uniqueness before action.
- Label association: standard label/ARIA relationships first, Angular Material/form wrappers next, then visible nearby label text only when geometry and wrapper scope produce a unique association. Unresolved labels are preserved as unresolved. Current values remain unobserved.
- No dropdown is opened or value selected to build the field map. Existing separate option discovery capability and navigation behavior remain in the engine.
- Verification after update: ` .\venv\Scripts\python.exe -m pytest backend/tests/unit/test_ui_discovery.py -v` — 14 passed; ` .\venv\Scripts\python.exe -m pytest backend/tests/ -v` — 40 passed; `git diff --check` — clean. The project venv required approved local execution because its configured Python could not start inside the sandbox.
- The live artifact `backend/artifacts/ui_discovery_live.json` predates this mapping change. A fresh supervised development run is still required to verify actual Angular markup coverage. Previous run reached Manual Case Registration but was PARTIAL; no Phase 3 work is authorized.

## Latest live field-map outcome (2026-11-04 19:07 IST)
- A fresh headed development run reached Manual Case Registration after user login. Latest artifact: `backend/artifacts/ui_discovery_live.json`.
- Output now has 58 aggregate form fields across the workflow (deduplicated across repeated same-URL snapshots while preserving repeated field occurrences). 57 have visible labels associated; one Log search field is unresolved except for its `Search...` placeholder. Labels such as Country Code, Reporter, Patient and Event Information fields are mapped into section paths; generic `Select` is no longer treated as a field label.
- Dropdown option interactions are disabled by default for field mapping. Latest run observed zero option values and did not open/select any dropdown. `inspect_dropdown_options=True` retains explicit option-exploration capability for a separately requested need.
- The live result is still PARTIAL: 4 screen snapshots, 2 safe interactions, 20 issues (9 current-page navigation candidates; 5 dialog, 3 expand and 3 tab timeouts). These gaps mean deeper conditional UI coverage is unresolved.
- Final exact-code backend suite: ` .\venv\Scripts\python.exe -m pytest backend/tests/ -v` — 40 passed in 36.25s. Phase 2 UI suite: 14 passed. `git diff --check` exited 0. Phase 2 is still in progress; no catalog/RAG work started.

## Workflow-scoped discovery update (2026-11-04)
- The user authorized a reusable, workflow-scoped Phase 2 change: runtime product URL + one workflow name; automatically observe navigation, resolve a unique safe destination, deeply inspect that workflow, and report gaps without per-control human guidance.
- `DiscoveryPolicy.workflow_scope` and result fields `workflow_scope` / `workflow_match_status` now preserve the requested scope and whether it was reached, missing or ambiguous.
- Navigation observation resolves menu semantics from the owning ancestor (`aria-haspopup` / `.hoverBox`), deduplicates by element/target rather than label, and treats menu triggers as safe reveal interactions. Scoped runs do not follow unrelated destinations; duplicate workflow matches stop as INCOMPLETE.
- Live CLI inputs: `UI_DISCOVERY_BASE_URL`, `UI_DISCOVERY_WORKFLOW`, and `UI_DISCOVERY_ENVIRONMENT` (`development`, `validation`, or `test`); the legacy `ONEPV_BASE_URL` remains a URL fallback. Missing URL/scope/environment can be entered once at launch. Headed Edge manual authentication remains.
- Workflow limits use 100 screens / 300 safe interactions / 100 navigation visits, removing the former 2/5/2 cap. The traversal still marks coverage partial when safe-state or traversal limits are reached.
- Transition verification now compares URL and a structural fingerprint of observed UI metadata instead of reading main-page rendered text. Unlabeled value-bearing controls no longer use displayed contents as their accessible name.
- Focused regression tests were added/updated but not executed per the user-provided task constraint. Python is unavailable on PATH in this worktree, so syntax compilation could not run. `git diff --check` passed after whitespace cleanup. No live discovery was launched.
- The Phase 2 build card referenced by older records is absent. The prior live artifact exists but is PARTIAL (1 screen, 0 controls, 2 navigation visits, 4 issues) and does not prove the requested workflow was reached.
- Project cleanup is intentionally non-destructive: `.gitignore` now excludes local uploads, extracted Node runtime, pytest cache, plan cache and generated spec scratch files. Historical archive folders, live artifacts, prior user changes and uploaded files remain on disk.
