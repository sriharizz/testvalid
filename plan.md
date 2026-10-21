# Master Implementation Plan: Clinevo OnePV — Validation & Execution Portal

## 0. Non-Negotiable Execution Rules for Antigravity AI IDE
1. **Execute Strictly Phase-by-Phase (Phases 1 → 2 → 3 → 4 → 5):**
   - Do NOT attempt to write the entire codebase in one pass.
   - Complete each Phase, run its mandatory verification script, fix any errors, and confirm 100% pass before starting the next Phase.
2. **Zero Hardcoded Documents (100% Dynamic `.docx` Ingestion):**
   - Do NOT hardcode scenario lists for `PQ-022` or `OQ-036`. The user will upload arbitrary OnePV `.docx` validation protocols through the UI button (`Upload Validation Protocol (.docx)`) AFTER the build is complete.
   - Every table, scenario, procedure, expected result, and `µ` screenshot checkpoint must be dynamically extracted from the uploaded `.docx` file at runtime.
3. **Live Target Web Application & DOM Grounding:**
   - The target application under test is live at **`https://mpv-two.vercel.app/login`**.
   - Because this is a separate repository, **Phase 1 MUST run a Playwright DOM Discovery script (`dom_inspector.py`) against `https://mpv-two.vercel.app/login`** to record the exact live DOM inputs, buttons, tabs, `data-testid` attributes, and modal dialogs into `backend/artifacts/dom_map.json`. Never guess selectors.
4. **Exact UI Fidelity (`image_5a8642.jpg`):**
   - The React + TypeScript frontend must strictly match the 3-column split-screen layout, color palette, component hierarchy, and interactive behaviors shown in `image_5a8642.jpg`.

---

## 1. Repository Structure & Technology Stack

```text
clinevo-validation-portal/
├── backend/
│   ├── main.py                  # FastAPI server + WebSocket/SSE live execution & browser frame streaming
│   ├── schemas.py               # Strict Pydantic v2 models shared across all pipeline stages
│   ├── dom_inspector.py         # Phase 1: Crawls https://mpv-two.vercel.app/login to build dom_map.json
│   ├── extractor.py             # Phase 1: Deep XML + python-docx parser for OQ/PQ protocols
│   ├── agents.py                # Phase 2: Planner, Generator (.spec.ts), and Healer (Groq Qwen / OpenCode)
│   ├── check_coverage.py        # Phase 2: Deterministic Coverage Checker (Gate 1 & Gate 2)
│   ├── test_coverage_gate.py    # Phase 2: Pytest suite (1 positive + 5 seeded negative fault tests)
│   ├── playwright_runner.py     # Phase 3: Real Playwright serial runner + live frame streamer + µ capture
│   ├── docx_writer.py           # Phase 3: Lossless python-docx populator (cell values + images + appendix)
│   ├── verify_e2e.py            # Phase 5: Automated end-to-end verification script
│   ├── uploads/                 # Runtime directory for uploaded .docx files
│   ├── artifacts/               # dom_map.json, plans, generated .spec.ts, screenshots, executed .docx
│   └── requirements.txt         # fastapi, uvicorn, python-docx, playwright, groq, pydantic, pytest, httpx, websockets, python-multipart
├── frontend/
│   ├── src/
│   │   ├── main.tsx
│   │   ├── App.tsx                      # Main 3-column portal layout matching image_5a8642.jpg
│   │   ├── types.ts                     # TypeScript interfaces mirroring backend/schemas.py
│   │   ├── components/
│   │   │   ├── TopHeaderBar.tsx         # Upload .docx, Sim Mode pills, Execute, Live Browser, Coverage, Download
│   │   │   ├── LeftTraceabilityPane.tsx # Credential Gate + 6-Stage Agent Timeline + Artifact Inspector Modal
│   │   │   ├── MiddleSequencePane.tsx   # Connected Series Step Cards + blue active arrow connector
│   │   │   ├── RightDocInspector.tsx    # Realistic Word Page view, synced row highlight & screenshot lightbox
│   │   │   ├── LiveBrowserModal.tsx     # Real-time browser viewport stream + headed browser trigger + live URL
│   │   │   └── ArtifactModal.tsx        # Displays Planner Markdown, .spec.ts code, Coverage JSON, & Git SHA
│   ├── index.html
│   ├── package.json
│   ├── tailwind.config.js
│   └── vite.config.ts
└── plan.md
```

---

## 2. Shared Data Contracts (`backend/schemas.py` & `frontend/src/types.ts`)

Both backend and frontend MUST implement these exact data structures so API responses and WebSocket events never mismatch:

```python
# backend/schemas.py
from pydantic import BaseModel, Field
from typing import List, Optional, Literal, Dict, Any

class ReadinessFlag(BaseModel):
    step_id: str
    flag_type: Literal["AMBIGUOUS_ERROR_MESSAGE", "RUNTIME_DATA_REQUIRED"]
    raw_text: str
    resolved_value: str

class ProtocolStep(BaseModel):
    step_id: str                        # e.g., "TS1-S01", "TS1-S02", "TS2-S01"
    step_number_display: str            # e.g., "TS1-S01"
    test_set_number: int                # 1 or 2
    test_set_title: str                 # e.g., "Test Set #1: Manual Case Registration"
    table_index: int                    # Exact table index in .docx for lossless write-back
    row_index: int                      # Exact row index in .docx table for lossless write-back
    scenario: str                       # Exact Scenario column text
    procedure: str                      # Exact Procedure column text
    expected_result: str                # Exact Expected Result column text
    screenshot_required: bool           # True if µ symbol or camera XML tag detected
    capture_before_modal_ok: bool       # True if µ appears before "Click on OK/Yes button"
    required_assertions_count: int      # Count of (Refer expected result N), minimum 1
    action_intent: str                  # Mapped semantic action key for Planner/Generator
    test_data: Dict[str, Any] = Field(default_factory=dict)
    # Runtime Execution State
    status: Literal["QUEUED", "EXECUTING", "PASS", "FAIL", "BLOCKED"] = "QUEUED"
    latency_ms: Optional[int] = None
    observed_result: Optional[str] = None
    pass_fail_text: Optional[Literal["Pass", "Fail", "Blocked"]] = None
    initials_date: Optional[str] = None
    screenshot_url: Optional[str] = None
    error_detail: Optional[str] = None

class TraceStage(BaseModel):
    stage_number: int                   # 1 to 6
    title: str                          # e.g., "1. Python Protocol Extractor"
    subtitle: str                       # e.g., "18 steps, 18 µ screenshot points"
    status: Literal["PENDING", "RUNNING", "PASS", "FAIL"] = "PENDING"
    latency_seconds: float = 0.0
    artifact_type: Literal["JSON", "MARKDOWN", "CODE", "COVERAGE", "GIT"]
    artifact_content: str = ""

class ProtocolSession(BaseModel):
    session_id: str
    filename: str
    document_no: str
    version: str
    effective_date: str
    title: str
    objective: str
    scope: str
    total_steps: int
    total_screenshots: int
    coverage_mapped: int
    coverage_skipped: int
    git_commit_sha: str
    readiness_flags: List[ReadinessFlag]
    trace_stages: List[TraceStage]
    steps: List[ProtocolStep]
```

---

## PHASE 1: Live DOM Discovery & Deep XML `.docx` Protocol Extractor

### Step 1.1: Live Target DOM Discovery (`backend/dom_inspector.py`)
Before writing any test generation or runner logic, write and execute `backend/dom_inspector.py` using Playwright against **`https://mpv-two.vercel.app/login`**:
1. Open `https://mpv-two.vercel.app/login` in headless Chromium.
2. Inspect and record all input selectors (`id`, `name`, `placeholder`, `data-testid`, `label` text) and button selectors on `/login`.
3. Log in with `sirihari.banda` / `Clinevo@2026` / `Clinevo` and inspect the post-login shell:
   - Header username and timestamp `data-testid`s, Exit icon, User Profile / Logout menu, and Simulation Control Bar (`?simMode=pass`, `?simMode=fail`, `?simMode=blocked`).
   - Left sidebar navigation links (`Intake` -> `Manual Case Registration`, `Open Case`, `Reports` -> `Audit History`).
   - All section headers, inputs, dropdowns, search icon buttons, modals (`role="dialog"`), and `Save` / `Submit` / `Save and Submit` / `Reset` buttons on `/intake/manual-case-registration`, `/intake/open-case`, and `/reports/audit-history`.
4. Save the complete discovered selector dictionary to `backend/artifacts/dom_map.json`.

### Step 1.2: Deep XML `.docx` Extractor (`backend/extractor.py`)
Build `extractor.py` to parse any uploaded Clinevo OQ or PQ `.docx` document with 100% accuracy:
1. **Header & Metadata Parsing:**
   - Extract `document_no` (regex `CLIN-[A-Z0-9-]+`), `version` (default `1.0`), `effective_date` (default `01-Oct-2026`), `title`, `objective` (under `1.0 OBJECTIVE`), and `scope` (under `2.0 SCOPE`).
2. **Accurate Execution Table Identification:**
   - Iterate through `doc.tables` with `enumerate(doc.tables)`.
   - A table is an Execution Table ONLY if its header row (Row 0) contains cells matching `Step`, `Scenario`, `Procedure`, and `Expected Result`. (Ignore repeating page-header tables that contain `Document ID` and `Page No.`).
   - Track `test_set_number` (`1` for the first execution table, `2` for the second execution table, etc.).
3. **Row Filtering (Crucial — Exclude Merged Footer Rows):**
   - Inside each Execution Table, iterate over rows starting at index `1`.
   - **Skip footer rows** if the row's first cell text starts with `"Comments"`, `"Deviations"`, `"Executed By"`, `"Verified By"`, or if all cells in the row are horizontally merged (`row.cells[0]._tc == row.cells[-1]._tc`). Record those footer row indices separately so `docx_writer.py` can populate `Comments / Deviations` and `Executed By` later.
4. **Auto-Numbered `Step #` & Merged `Scenario` Handling:**
   - Word protocols use `<w:numPr>` list numbering in Column 0, so `row.cells[0].text.strip()` is often `""`. Generate deterministic sequential IDs: `f"TS{test_set_number}-S{step_counter:02d}"` (`TS1-S01`, `TS1-S02`, ..., `TS2-S01`).
   - If `row.cells[1].text.strip()` (`Scenario`) is empty due to vertical cell merging in Word, inherit the `Scenario` title from the immediately preceding row.
5. **Deep XML Screenshot (`µ`) & Multi-Assertion Detection:**
   - To detect `µ` screenshot checkpoints reliably in `.docx`, check BOTH:
     - Character presence: `any(ch in procedure_text for ch in ['µ', '\u00b5', '\uf0b5', '📷'])`
     - Word XML symbol tag presence: `bool(row.cells[2]._tc.xpath('.//w:sym'))`
   - Normalize any detected XML `<w:sym>` or `\uf0b5` in the extracted `procedure` display string to `(µ)` so it renders cleanly in the UI.
   - Set `capture_before_modal_ok = True` if `µ` appears in the text before `"Click on OK"` or `"Click on Yes"`, or whenever the Expected Result checks for an error/confirmation message pop-up.
   - Count occurrences of `re.findall(r'Refer expected result\s*\d+', procedure_text, re.I)`. Set `required_assertions_count = max(1, len(matches))`.
6. **Semantic Action Intent Classification:**
   - Classify each extracted row into its exact `action_intent` based on keywords in `Scenario`, `Procedure`, and `Expected Result` so both the 18-step `PQ-022` and 50-step `OQ-036` (and any subset/variant) map deterministically to the live OnePV workflows.

### Phase 1 Verification Gate
- Run `python backend/dom_inspector.py` and verify `backend/artifacts/dom_map.json` exists and contains verified selectors from `https://mpv-two.vercel.app/login`.
- Run a self-test of `backend/extractor.py` using a generated multi-table `.docx` (including empty auto-numbered Step cells, `µ` symbols, and footer rows `Comments / Deviations:`) and verify 100% accurate extraction.

---

## PHASE 2: Planner, Generator, Healer & Deterministic Coverage Checker

### Step 2.1: Planner Agent (`backend/agents.py`)
- Takes `ProtocolSession` + `dom_map.json`.
- Supports calling Groq API (`qwen/qwen3-32b` if `GROQ_API_KEY` is set) or OpenCode endpoint to generate rich step descriptions, while deterministically binding each `ProtocolStep` (`TS1-S01`..`TSn-Sm`) to its target URL, verified DOM locators from `dom_map.json`, controlled runtime test data, assertion targets, and `captureEvidence` timing.
- Outputs `test_plan.json` and formatted `test_plan.md` (stored in `TraceStage` #2 with recorded latency).

### Step 2.2: Deterministic Coverage Checker (`backend/check_coverage.py`)
Pure Python static verification (zero LLM calls):
1. **Gate 1 (`verify_protocol_to_plan(protocol_steps, plan_steps)`):**
   - Checks `missing_ids = set(protocol_ids) - set(plan_ids)`.
   - Checks `extra_ids = set(plan_ids) - set(protocol_ids)`.
   - Checks strict sequence preservation: `protocol_ids == plan_ids`.
   - Returns structured JSON report (`passed: bool`, `total_steps`, `mapped_steps`, `order_verified: bool`, `violations: list`).
2. **Gate 2 (`verify_plan_to_playwright_code(plan_steps, spec_ts_code)`):**
   - Parses the generated Playwright TypeScript `.spec.ts` code and verifies for every `step_id`:
     - Exact `await test.step('TSx-Sxx', async () => { ... })` block exists in matching order.
     - Zero occurrences of `.skip(`, `.fixme(`, `test.todo(`, or commented-out `// await expect(`.
     - Inside each `test.step` block, counts `await expect(` calls and verifies `actual_expects >= step.required_assertions_count`.
     - If `step.screenshot_required` is `True`, verifies `await captureEvidence(page, 'TSx-Sxx')` is present inside that step block (and precedes any modal dismissal click when `capture_before_modal_ok` is `True`).
   - Returns structured JSON report stored in `TraceStage` #5.

### Step 2.3: Playwright TypeScript Generator, Healer & Git Baseline (`backend/agents.py`)
- Generates a complete, valid, human-reviewable Playwright TypeScript file (`artifacts/generated_<session_id>.spec.ts`) using `test.describe.serial` and clean helper functions (`loginToOnePV`, `captureEvidence`, `dismissModal`).
- Includes a `HealerAgent.verify_and_heal_selectors(spec_ts, dom_map)` pass that checks if any locator in `.spec.ts` drifted from `dom_map.json`, repairs the locator without touching any `expect()` or `captureEvidence()` line, and immediately re-runs **Coverage Gate 2**.
- Computes the Git Commit / Artifact SHA baseline (`v1.1-<sha256[:5]>`, e.g., `v1.1-a8f3d`) for `TraceStage` #6.

### Phase 2 Verification Gate (`backend/test_coverage_gate.py`)
- Run `pytest backend/test_coverage_gate.py` verifying:
  - Test 1 (Positive): Valid 18-step protocol, plan, and `.spec.ts` pass Gate 1 and Gate 2 (`< 50ms`).
  - Test 2 (Negative — Missing Step ID): Dropping `TS1-S04` fails Gate 1 & Gate 2.
  - Test 3 (Negative — Reordered Steps): Swapping `TS1-S04` and `TS1-S05` fails sequence check.
  - Test 4 (Negative — Silent Skip): Adding `test.skip()` fails Gate 2.
  - Test 5 (Negative — Weakened Assertion): Removing an `expect()` in a multi-assertion step fails Gate 2.
  - Test 6 (Negative — Missing `µ` Evidence): Removing `captureEvidence(page, 'TS1-S04')` fails Gate 2.
- All 6 pytest tests MUST pass before proceeding to Phase 3.

---

## PHASE 3: Live Playwright Execution Engine, Live Browser Stream & Lossless `.docx` Writer

### Step 3.1: Real Playwright Serial Executor (`backend/playwright_runner.py`)
Executes the protocol steps in a connected serial browser session against **`https://mpv-two.vercel.app/login`**:
1. **Browser Launch & Live Viewport Streaming:**
   - Launches Playwright Chromium (`viewport={"width": 1366, "height": 768}`). Support a toggle to launch `headless=False` (so a visible browser window opens on the user's desktop during local runs) AND after every sub-action, capture a fast JPEG frame (`page.screenshot(type="jpeg", quality=65)`) and broadcast it over WebSocket (`/ws/session/{session_id}`) so the Portal UI's **`👁️ Watch Live Browser`** window updates live at 5–10 FPS!
2. **Simulation Mode Synchronization (`PASS` | `FAIL` | `BLOCKED`):**
   - At the start of the run, navigate to `https://mpv-two.vercel.app/login?simMode=<mode>` and set `window.localStorage.setItem('simMode', mode)` (using the exact key discovered in `dom_map.json`).
   - Enforce deterministic mode behavior during execution:
     - **`PASS` Mode:** Executes every step in the uploaded protocol sequentially, verifying modals/fields, capturing high-res PNG screenshots (`artifacts/screenshots/{session_id}/{step_id}.png`) **while confirmation/error modals are open on screen**, and marking each step `PASS` with its measured latency (e.g., `0.8s`, `1.4s`, `1.7s`) and a crisp verification summary (e.g., `"Verified: Case ID TMP-CASE-1001 created"`).
     - **`FAIL` Mode (Application Defect Detection):** Executes steps normally until the target validation/auto-population step (e.g., `TS1-S04` or Product auto-population), triggers the app defect on `https://mpv-two.vercel.app`, captures the real screenshot of the defective screen, marks the step 🔴 **`FAIL`** with observed mismatch text (`"Assertion Failed: Expected mandatory validation error modal or auto-populated field, but observed application defect"`), and records the deviation.
     - **`BLOCKED` Mode (Environment / Control Blocker):** Executes Steps 1–3 (`PASS`), then when attempting `TS1-S04` (`Registering the Case`), triggers the `503 Service Unavailable - Control Locked` blocker on `https://mpv-two.vercel.app`, captures the screenshot of the locked screen, marks `TS1-S04` as 🟠 **`BLOCKED`**, immediately halts the browser series, and marks all subsequent dependent steps (`TS1-S05`..end) as 🟠 **`BLOCKED`** (`"Blocked: Prerequisite step TS1-S04 halted by 503 Environment Control Lock"`).
3. **Credential Gate Enforcement:**
   - Injects the exact `User Name`, `Password`, and `Enterprise` from the Left Sidebar UI into Step 2 (`User Authentication`).
   - If `Requires Tester Approval before login` is checked in the UI, pauses at Step 2 after filling credentials, emits WebSocket state `WAITING_FOR_LOGIN_APPROVAL`, and waits until the user clicks `Login to OnePV` / `Approve Login` in the Left Sidebar before clicking the Login button!

### Step 3.2: Lossless `.docx` Populator (`backend/docx_writer.py`)
When a run completes (or when the user clicks `Download Executed .docx`), populate a cloned copy of the **exact uploaded `.docx` file**:
1. Copy `uploads/{session_id}_{filename}` to `artifacts/executed_{filename}`.
2. Open with `python-docx`. Do NOT alter document styles, margins, headers, or original text in Columns 1, 2, or 3.
3. For each `ProtocolStep` using its exact `(table_index, row_index)`:
   - **Column 0 (`Step #`):** If `cell.text.strip()` is empty, write `step.step_id` (e.g., `TS1-S01`) in 9pt Arial/Calibri.
   - **Column 4 (`Does Observed Result Match Expected Result? (Pass/Fail)`):** Write **`Pass`**, **`Fail`**, or **`Blocked`** in bold full text, followed on a new line by `step.observed_result`.
   - **Column 5 (`Initials / Date`):** Write `f"{initials} / {date_str}"` (e.g., `S.H. / 14-Oct-2026`) and, if `step.screenshot_url` exists on disk, add a new paragraph inside the cell and embed the PNG screenshot scaled to **`width=Inches(1.15)`** so it fits cleanly inside the Word column without stretching the table!
4. **Populate Footer Rows (`Comments / Deviations`, `Executed By`):**
   - In the recorded footer rows of each execution table, write `Comments / Deviations: None` (if all steps passed) or list the exact failed/blocked step IDs and mismatch details. Fill `Executed By` with `f"{username} ({initials}) / {date_str}"`.
5. **High-Resolution Evidence Appendix:**
   - At the end of the document, append a clean section titled `Execution Evidence Log (Captured Checkpoints)` containing larger (`width=Inches(4.5)`) high-resolution copies of every step screenshot labeled with its `Step ID`, `Scenario`, and timestamp so QA reviewers can read every modal message effortlessly.

### Phase 3 Verification Gate
- Run an automated test script that passes a sample `.docx` through `extractor.py` -> `playwright_runner.py` (against `https://mpv-two.vercel.app/login`) -> `docx_writer.py`, and assert that all PNG screenshots exist on disk and the output `.docx` opens cleanly in `python-docx` with `Pass` and embedded images in the cells.

---

## PHASE 4: Pixel-Accurate 3-Column React + TypeScript Frontend (`image_5a8642.jpg`)

Build the frontend in `frontend/` matching **`image_5a8642.jpg`** down to every visual detail:

### 1. Top Header Bar (`TopHeaderBar.tsx`)
- Full-width dark navy gradient header (`bg-gradient-to-r from-[#0b192c] via-[#102542] to-[#0b192c] text-white h-14 px-4 flex items-center justify-between shadow-md`):
  - **Left:** Glowing blue brain-circuit icon + bold title `Clinevo OnePV — Validation & Execution Portal`.
  - **Upload Button:** Blue button (`bg-[#1d63dc] hover:bg-blue-600`) with upload icon: `Upload Validation Protocol (.docx)` (triggers hidden `<input type="file" accept=".docx" />`). Also include a subtle dropdown arrow next to it allowing instant 1-click loading of any previously uploaded `.docx` in `uploads/`.
  - **Simulation Mode Selector:** Label `Simulation Mode:` with 3 pill buttons inside a dark rounded container:
    - `🟢 PASS`
    - `🔴 FAIL`
    - `🟠 BLOCKED`
  - **Execute Button:** Bright blue button (`bg-[#1d63dc] hover:bg-blue-500 font-semibold`) with lightning bolt icon: `⚡ Execute Automation Series`.
  - **Watch Live Browser Button:** Button `👁️ Live Browser` that opens the live real-time browser stream overlay / pop-out window.
  - **Coverage Gate Pill:** Dark slate badge (`bg-slate-800/90 border border-slate-600 px-3 py-1 rounded text-xs`):
    - Top line: `Coverage Gate:`
    - Bottom line: `18/18 Mapped | 0 Skipped` (dynamically updates to `50/50 Mapped | 0 Skipped` for OQ-036!).
  - **Download Button:** Emerald green button (`bg-[#22a047] hover:bg-green-600 font-semibold`) with document icon: `Download Executed .docx`.

### 2. Column 1 — Left Sidebar (`LeftTraceabilityPane.tsx` — Width `310px`)
- Section Header: `AGENT PIPELINE & TRACEABILITY` (uppercase bold navy tracking-wider with blue underline bar).
- **Card 1: `🔒 Credential Gate` (`bg-white rounded-xl border border-slate-200 shadow-sm p-3.5 mb-3`):**
  - Input `User Name`: pre-filled with `sirihari.banda`
  - Input `Password`: masked password dots with working eye icon button
  - Input `Enterprise`: `Clinevo` (light slate background)
  - Checkbox (checked by default or toggleable): `Requires Tester Approval before login`
  - Full-width blue button: `Login to OnePV` (when execution pauses for tester login approval, this button pulses bright amber/green: `Approve & Inject Login Now`).
- **Card 2: `6-Stage Agent Traceability Timeline` (`bg-white rounded-xl border border-slate-200 shadow-sm p-3.5 flex-1 overflow-y-auto`):**
  - Displays a subtle phase badge separating **Phase 1: AI Authoring & Coverage (Run Once)** and **Phase 2: Deterministic Replay (0 LLM Calls)**.
  - Vertical connected timeline with green checkmark circles (`✓`) on the left and green latency pills (`bg-emerald-50 text-emerald-700 border border-emerald-200`) on the right:
    1. **`1. Python Protocol Extractor`** | Pill: `0.3s` | Subtitle: `<N> steps, <M> µ screenshot points`
    2. **`2. Qwen Planner Agent`** | Pill: `1.4s` | Subtitle: `Plan mapped via OpenCode`
    3. **`3. Coverage Checker Gate 1`** | Pill: `0.1s` | Subtitle: `<N>/<N> IDs & Order Verified`
    4. **`4. Playwright Generator & Healer`** | Pill: `1.8s` | Subtitle: `Serial .spec.ts ready`
    5. **`5. Coverage Checker Gate 2`** | Pill: `0.1s` | Subtitle: `<N>/<N> Assertions & µ Captures`
    6. **`6. Frozen Git Baseline`** | Green Lock Icon Pill (`🔒`) | Subtitle: `Commit: v1.1-a8f3d`
  - **Click-to-Inspect:** Clicking any of the 6 stages opens `ArtifactModal.tsx` showing the real extracted JSON, Readiness Flags, Markdown Plan, Coverage Gate 1/2 JSON verification report, generated Playwright `.spec.ts` code, or Git Commit metadata.

### 3. Column 2 — Middle Panel (`MiddleSequencePane.tsx` — Width `400px`)
- Section Header: `LIVE TEST SEQUENCE (Connected Series — <Doc Short Code>)` (e.g., `PQ-022` or `OQ-036`).
- Vertical connected timeline with numbered blue/grey circles (`1`, `2`, `3`, `4`...) connected by a vertical line.
- Each Step Card displays:
  - Bold blue/navy title: `<Step ID> | <Scenario>` (e.g., `TS1-S04 | Register Adverse Event Case & Generate ID`)
  - Subtitle: concise procedure text (truncated cleanly to 2 lines).
  - Status pill on the right:
    - `🟢 PASS - 1.7s` (`bg-emerald-50 text-emerald-700 border-emerald-200`)
    - `🔴 FAIL - 1.4s` (`bg-red-50 text-red-700 border-red-200`)
    - `🟠 BLOCKED` (`bg-amber-50 text-amber-700 border-amber-200`)
    - `⏳ Executing...` (`bg-blue-50 text-blue-700 border-blue-200 animate-pulse`)
    - `⌛ Queued` (`bg-slate-100 text-slate-600 border-slate-200`)
- **Active Blue Selection Box & Right-Pointing Connector Arrow (`image_5a8642.jpg`):**
  - The currently selected or executing step card has a thick bright-blue rounded border (`border-2 border-[#1d63dc] shadow-md bg-blue-50/30`) with a solid blue arrow (`→`) extending from its right edge pointing directly at the Active Document Inspector in Column 3!

### 4. Column 3 — Right Panel (`RightDocInspector.tsx` — Flex-1 Remaining Width)
- Section Header: `ACTIVE PROTOCOL DOCUMENT INSPECTOR — <Uploaded Filename.docx>`
- Grey document viewer bar (`bg-slate-200/80 border-b border-slate-300 px-3 py-1.5 flex items-center justify-between text-xs text-slate-700`):
  - Page indicator (`1 / 12`), zoom selector (`100%`), search icon, expand icon, and print icon.
- **Realistic White Microsoft Word Document Page (`bg-white shadow-lg border border-slate-300 mx-auto my-3 p-6 max-w-4xl`):**
  - **Formal 3-Column Word Header Box (`border border-slate-400 mb-4`):**
    - Left cell: Circular blue `OnePV by Clinevo Technologies` logo.
    - Center cell: Bold title `Clinevo OnePV` + `<Performance/Operational Qualification Protocol>` + subtitle `Registering Adverse Event Case`.
    - Right cell (4 rows): `Document No: <doc_no>`, `Version: 1.0`, `Effective Date: 01-Oct-2026`, `Page: 4 of 12`.
  - **Protocol Sections:**
    - `1. Objective` (displays extracted objective text)
    - `2. Scope` (displays extracted scope text)
    - `3. Test Steps`
  - **The 6-Column Word Execution Table (`w-full border-collapse border border-slate-300 text-xs`):**
    - Dark navy header row (`bg-[#102542] text-white font-semibold`):
      `Step #` | `Scenario` | `Procedure` | `Expected Result` | `Pass / Fail` | `Initials / Date & Evidence`
    - Renders every extracted step row dynamically.
    - **Synchronized Blue Row Highlight (`image_5a8642.jpg`):** The row matching the selected step in Column 2 is wrapped in a bright blue highlight box (`ring-2 ring-[#1d63dc] bg-blue-50/25`) and automatically scrolls into the center of the document viewer (`scrollIntoView({ behavior: 'smooth', block: 'center' })`)!
    - **Live Cell Population:**
      - When a step completes, the `Pass / Fail` cell shows bold green `Pass` (or red `Fail` / amber `Blocked`) + the green verification text below it (e.g., `Verified: Case ID TMP-CASE-1001 created`).
      - The `Initials / Date & Evidence` cell shows `S.H. / 14-Oct-2026` at the top and the **real captured screenshot thumbnail** below it with a dark camera badge icon (`📷`) in the bottom-right corner!
      - Clicking any screenshot thumbnail opens a full-resolution modal preview of that screenshot with step details.

### 5. Live Browser Stream Drawer / Modal (`LiveBrowserModal.tsx`)
- When the user clicks `👁️ Live Browser` (or automatically as a Picture-in-Picture corner window during execution), displays:
  - The real-time JPEG viewport stream coming from Playwright as it types, opens modals, and clicks through `https://mpv-two.vercel.app`.
  - The current active URL (`https://mpv-two.vercel.app/intake/manual-case-registration`), current action label, and a checkbox `Launch Visible Local Chromium Window` so the user can also pop open the real Chromium browser window on their desktop during screen recording.

---

## PHASE 5: End-to-End Verification & User Handover (`backend/verify_e2e.py`)

Before finishing, write and run `python backend/verify_e2e.py`:
1. Start the FastAPI backend on port `8000` and Vite frontend on port `5173`.
2. Create a realistic multi-step test `.docx` protocol and upload it to `POST http://localhost:8000/api/upload-protocol`.
3. Assert that all 6 Traceability Stages complete (`status == "PASS"`) and Coverage Gate 1 & Gate 2 report `0` violations.
4. Trigger an execution run against `https://mpv-two.vercel.app/login` and verify that every step transitions `QUEUED -> EXECUTING -> PASS`, screenshots are saved and served over HTTP, and `GET /api/download-executed-docx/{session_id}` returns a populated `.docx` file with embedded screenshots.
5. Keep both backend (`http://localhost:8000`) and frontend (`http://localhost:5173`) running and print the final URL for the user.