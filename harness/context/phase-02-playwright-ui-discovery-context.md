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
- The CLI currently prints only counts at completion and does not write the full `UIDiscoveryResult` to a reviewable report artifact. Add a narrowly scoped safe report output in Phase 2 before claiming the coverage-report acceptance criterion; exclude credentials, tokens, request bodies, form values, table rows and lookup data.
- Live policy is now capped at 5 screens, 5 navigation visits, 5 safe interactions, and 1-second per-interaction/navigation timeout. This is an initial sample only.

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
- The CLI does not yet serialize the complete sanitized coverage result for handoff/review.
- Browser fixture tests did not complete, so traversal behavior and the latest caps still need targeted verification.
- No live coverage report exists; inaccessible or unsafe sections remain unknown until a successful run.
