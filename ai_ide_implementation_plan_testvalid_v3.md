# AI Coding IDE Master Implementation Plan: Universal, Low-Token, FDA-Compliant Test Validation Engine (`testvalid` v3)

> **Instructions for the AI Coding Agent (Cursor / Claude Code / Windsurf / OpenCode / Copilot):**
> You are refactoring the existing `testvalid` repository (`backend/` and `frontend/`) from a OnePV-coupled prototype into a **production-grade, product-agnostic, zero-false-positive, FDA 21 CFR Part 11 / CSA / GAMP 5 compliant validation platform**.
> Execute the phases in this document sequentially (**Phase 1 through Phase 6**). Do not skip any acceptance checks, and do not leave permissive fallbacks that mask test failures.

---

## 1. Architectural Overview & Core Invariants

### 1.1 Why We Are Refactoring
The current `testvalid` codebase suffers from six production blockers:
1. **OnePV Hardcoding in Document Parsing (`backend/extractor.py`):** Regexes rely on `Label: (Instruction)` formatting and hardcoded OnePV strings (`reporter`, `meddra`, `manual case`, `under seriousness`).
2. **Disconnected Execution Engines (`backend/agents.py` vs. `backend/playwright_runner.py`):** `PlaywrightGeneratorAgent` generates a `.spec.ts` file with dummy assertions (`await expect(page.locator('body')).not.toBeEmpty()`), while `PlaywrightRunner` executes a separate 700-line Python `if/elif` state machine.
3. **False Positives from Silent Field Skipping (`backend/playwright_runner.py:1255-1313`):** When `find_semantic_control()` returns `None` for a planned field, the loop silently skips the field, clicks `Save`, and marks the step `PASS`.
4. **False Positives from Blind Dropdown Fallbacks (`backend/playwright_runner.py:285-403`):** `safe_select_option()` only works on native HTML `<select>` tags (failing on React/MUI/Shadcn/AntD `[role="combobox"]` portals) and falls back to `select_option(index=1)` when a requested option is missing—selecting a random option and marking `PASS`.
5. **False Positives in Result Verification (`backend/playwright_runner.py:632-906`):**
   - `VIEW_ACTIVE` (`lines 855-890`) has `else:` branches that append to `passed_details` instead of `failed_details` when URL/header checks fail.
   - `STATE_PERSISTED` (`lines 893-898`) passes whenever no red error banner is detected, even if clicking `Save` did nothing or returned HTTP 500.
   - `TABLE_DATA` (`lines 793-818`) checks `row_count > 0` instead of checking whether a new row with the submitted data was actually added.
6. **FDA 21 CFR Part 11 & ALCOA+ Violations (`backend/playwright_runner.py` & `backend/docx_writer.py`):**
   - `playwright_runner.py:1511` hardcodes `step.tester_initials_date = "S.B. / 15-Oct-2026"`.
   - `extractor.py:616` and `schemas.py:186` hardcode `git_commit_sha = "v1.1-a8f3d"`.
   - `docx_writer.py:91-96` automatically signs off `"Reviewed By: QA / CSV Lead"` at test execution time without a separate QA signature event.
   - `stitch_two_stage_screenshots()` (`playwright_runner.py:535`) is defined but never called, so modal popups obscure populated form fields in evidence screenshots.

### 1.2 Target 4-Stage Architecture ("Compile Once via ARIA Snapshots -> Replay Free with 0 Tokens")

| Stage | Component | Role & Token Budget | Regulatory & Engineering Guarantee |
| :--- | :--- | :--- | :--- |
| **Stage 1: Universal Ingestion** | `UniversalProtocolExtractor` (`backend/extractor.py`) | **1 Batched LLM Call (~1,500 tokens)** per new document upload (with structural table coordinate preservation). | Parses any IQ/OQ/PQ/UAT `.docx` table layout (4 to 8+ columns, multiple test tables, merged cells) into product-agnostic `IntentStep` definitions. |
| **Stage 2: ARIA Compiler & Deterministic Cache** | `AriaCompilerAgent` (`backend/aria_compiler.py` & `backend/agents.py`) | **0 AI Tokens on Cache Hit**; **~350 tokens per uncached step** using Playwright `locator.aria_snapshot()`. | Maps human step intents to live ARIA roles/names (`getByRole`, `getByLabel`), compiles a deterministic `LockedProtocolPlan`, and locks it with a SHA-256 hash prior to official execution. |
| **Stage 3: Strict Zero-Token Runner** | `PlaywrightRunner` (`backend/playwright_runner.py`) | **0 AI Tokens** during execution (100% deterministic replay of `LockedProtocolPlan`). | Enforces 100% field resolution, zero blind dropdown fallbacks, Pre/Post `aria_snapshot()` diffing, network status (`2xx` vs `4xx/5xx`) verification, and two-stage screenshot stitching (`_form.png` + `_modal.png`). |
| **Stage 4: Part 11 Dossier & Audit Trail** | `AuditTrailManager` (`backend/audit_trail.py`) & `DocxWriter` (`backend/docx_writer.py`) | **0 AI Tokens** (Optional LLM call only for failed-step Root Cause Analysis). | Stamps real-time UTC watermarks, writes back to exact source table column maps, enforces separate Tester vs. QA electronic signatures, and writes an append-only hash-chained `audit_trail.jsonl`. |

---

## 2. Phase 1: Upgrade Data Models & Schemas (`backend/schemas.py`)

### Goal
Replace loose dictionary structures with strict Pydantic models that represent table column coordinates, atomic UI actions, verifiable pre/post assertions, locked deterministic plans, and [21 CFR Part 11](https://www.ecfr.gov/current/title-21/chapter-I/subchapter-A/part-11) audit/signature records.

### Exact Changes to Make in `backend/schemas.py`
1. **Add `TableColumnMap` Model** so `extractor.py` and `docx_writer.py` never guess column numbers:
   ```python
   class TableColumnMap(BaseModel):
       table_index: int
       header_row_index: int
       step_col: int = 0
       scenario_col: Optional[int] = None
       procedure_col: int = 1
       expected_col: int = 2
       observed_col: Optional[int] = None
       pass_fail_col: int = 3
       initials_col: int = 4
       signoff_table_index: Optional[int] = None
   ```
2. **Expand `AssertionType` and `StepAssertion`** to support deterministic Pre/Post ARIA & Network checks:
   ```python
   AssertionType = Literal[
       "ENTITY_CREATED",        # Regex pattern match for generated ID in dialog/DOM
       "MESSAGE_DISPLAYED",     # Positive confirmation modal/toast with target_text
       "ERROR_MESSAGE",         # Negative test validation alert/dialog/aria-invalid
       "VIEW_ACTIVE",           # URL substring/regex AND visible heading/landmark
       "FIELD_VALUE",           # Specific control has expected_value or non-empty auto-populated value
       "STATUS_BADGE",          # Visible coding/status badge inside target section
       "TABLE_ROW_ADDED",       # Table row count increased by >=1 AND new row contains expected cell values
       "TABLE_ROW_DELETED",     # Table row count decreased or target row text no longer present
       "UI_ELEMENT",            # Visible link, accordion, or control
       "FILE_DOWNLOAD",         # Verified via page.expect_download() with file size > 0
       "ARIA_STATE_CHANGED"     # Post-action aria_snapshot differs from pre-action snapshot + HTTP 2xx
   ]

   class StepAssertion(BaseModel):
       assertion_type: AssertionType
       description: str
       target_text: Optional[str] = None
       pattern: Optional[str] = None
       field_label: Optional[str] = None
       expected_value: Optional[str] = None
       must_contain_values: List[str] = Field(default_factory=list)
   ```
3. **Add `CompiledControlLocator` and `LockedStepSpec`** for the Stage 2 Cache:
   ```python
   class CompiledControlLocator(BaseModel):
       field_id: str
       section_hint: str
       label: str
       control_type: ControlType
       aria_role: Optional[str] = None          # e.g., "textbox", "combobox", "checkbox", "button"
       accessible_name: Optional[str] = None    # Exact or regex name from aria_snapshot()
       fallback_css: Optional[str] = None       # Scoped fallback selector if needed
       target_value: str
       is_optional: bool = False
       expect_auto_populated: bool = False

   class LockedStepSpec(BaseModel):
       step_id: str
       scenario: str
       action_intent: str
       primary_section: str
       navigation_url: Optional[str] = None
       pre_sub_actions: List[SubActionSpec] = Field(default_factory=list)
       compiled_fields: List[CompiledControlLocator] = Field(default_factory=list)
       submit_button_name: Optional[str] = None # e.g., "Save", "Save and Submit", "Select", "Login"
       modal_confirm_button: Optional[str] = None # e.g., "OK", "Yes"
       assertions: List[StepAssertion] = Field(default_factory=list)
       requires_form_screenshot: bool = False
       requires_modal_screenshot: bool = False
       aria_structure_hash: Optional[str] = None
   ```
4. **Add `ElectronicSignatureRecord` and `AuditLogEntry`** for 21 CFR Part 11 compliance:
   ```python
   class ElectronicSignatureRecord(BaseModel):
       signer_username: str
       signer_full_name: str
       signer_initials: str
       signer_role: Literal["TEST_EXECUTOR", "QA_REVIEWER", "APPROVER"]
       signature_meaning: str                   # e.g., "I have executed this protocol and verified the recorded observations."
       signed_at_utc: str                       # ISO-8601 UTC timestamp
       signature_hash: str                      # SHA-256 of (session_id + protocol_hash + signer + timestamp)

   class AuditLogEntry(BaseModel):
       sequence_no: int
       timestamp_utc: str
       session_id: str
       actor_username: str
       actor_role: str
       event_type: Literal[
           "PROTOCOL_UPLOADED",
           "PLAN_COMPILED",
           "PLAN_PRE_APPROVED",
           "EXECUTION_STARTED",
           "STEP_PASSED",
           "STEP_FAILED",
           "HUMAN_REVIEW_CONTINUED",
           "EXECUTION_HALTED",
           "HEALER_LOCATOR_UPDATED",
           "ELECTRONIC_SIGNATURE_APPLIED",
           "DOSSIER_ARCHIVED"
       ]
       step_id: Optional[str] = None
       details: str
       justification: Optional[str] = None
       prev_hash: str
       entry_hash: str
   ```
5. **Update `ProtocolStep` and `ProtocolSession`:**
   - Remove the hardcoded default `git_commit_sha: str = "v1.1-a8f3d"`; compute it dynamically.
   - Add `col_map: Optional[TableColumnMap] = None` to `ProtocolStep`.
   - Add `signatures: List[ElectronicSignatureRecord] = Field(default_factory=list)` and `plan_locked_sha256: Optional[str] = None` to `ProtocolSession`.

---

## 3. Phase 2: Universal Document Extractor (`backend/extractor.py`)

### Goal
Make `extractor.py` parse **any** Word (`.docx`) qualification protocol from any company or product without relying on OnePV-specific keywords.

### Step-by-Step Refactoring Instructions
1. **Upgrade `is_execution_table()` and Header Mapping (`extractor.py:160-179` & `432-458`):**
   - Inspect the first 4 rows of every table in `doc.tables` (handling merged title banners in rows 0–2, as seen in `OQ-036` Tables 5 & 8).
   - Match columns dynamically using header synonyms:
     - `step_col`: `"step"`, `"test step"`, `"no."`, `"#"`
     - `scenario_col`: `"scenario"`, `"objective"`, `"test case"`, `"requirement"`
     - `procedure_col`: `"procedure"`, `"action"`, `"steps to be followed"`, `"instruction"`, `"description"`, `"input"`
     - `expected_col`: `"expected"`, `"acceptance criteria"`, `"expected result"`
     - `observed_col`: `"actual"`, `"observed"`, `"actual result"` (if separate from Pass/Fail)
     - `pass_fail_col`: `"pass/fail"`, `"pass / fail"`, `"status"`, `"result"`, `"does observed result match"`
     - `initials_col`: `"initials"`, `"performed by"`, `"executed by"`, `"date"`, `"sign"`
   - Link each execution table to its immediately following Sign-Off / Acceptance Criteria table (`signoff_table_index`) so multi-table protocols (like `OQ-036`, which has Table 6 for Test Set 1 and Table 9 for Test Set 2) update both sign-off tables accurately.
2. **Replace OnePV-Hardcoded `classify_action_intent()` and `extract_fields_from_procedure()` with a Two-Tier Universal Extractor:**
   - **Tier 1 (Deterministic Structural Pre-Parser):**
     - Extract numbered/bulleted sub-instructions, `Label: Value (Instruction)` pairs, quoted literal values (`'Paracetamol'`, `"Headache"`), and screenshot symbols (`µ`, `📷`, `w:sym`, `[Screenshot]`).
     - Detect whether the screenshot marker `(µ)` appears *before* or *after* modal confirmation instructions (`"Click OK"`, `"Click Yes"`). If a step fills form fields AND clicks `Save`/`Submit` with a confirmation popup, set **both** `requires_form_screenshot = True` and `requires_modal_screenshot = True` so two-stage stitching is triggered automatically.
   - **Tier 2 (Single-Batch LLM Structured Intent Extraction):**
     - Send all raw step rows (`step_id`, `scenario`, `procedure`, `expected_result`) in **one single batched JSON call** to `QwenLLMClient` (`temperature=0.0`, `json_mode=True`).
     - Prompt the LLM to return a strict JSON object mapping each `step_id` to:
       ```json
       {
         "primary_section": "Human-readable section or tab name from the step (e.g. 'Patient Information')",
         "action_intent": "AUTHENTICATE | NAVIGATE | FORM_ENTRY | MODAL_ACTION | TABLE_INLINE_EDIT | VERIFY_ONLY | EXPORT_DOWNLOAD | SESSION_EXIT",
         "pre_actions": [{"action_type": "click_button", "target_label": "Add Questions"}],
         "fields": [
           {
             "label": "Exact UI field label",
             "control_type": "text | select | date | toggle | modal_search_select | auto_populate_verify",
             "explicit_value": "Literal value from doc if specified, else null",
             "synthesized_value": "Realistic clinical/domain value if explicit_value is null",
             "expect_auto_populated": false
           }
         ],
         "submit_button": "Save | Save and Submit | Select | Login | Delete | null",
         "modal_confirm_button": "OK | Yes | Confirm | null",
         "assertions": [
           {
             "assertion_type": "MESSAGE_DISPLAYED | ENTITY_CREATED | FIELD_VALUE | STATUS_BADGE | TABLE_ROW_ADDED | TABLE_ROW_DELETED | ERROR_MESSAGE | VIEW_ACTIVE | FILE_DOWNLOAD | ARIA_STATE_CHANGED",
             "target_text": "Expected text or badge label",
             "field_label": "Field label if asserting FIELD_VALUE",
             "expected_value": "Expected field value if specified"
           }
         ]
       }
       ```
     - Merge Tier 1 and Tier 2 outputs so that 100% of explicit fields in the Word table are preserved (guaranteed Gate 1 parity) while prose instructions (like *"Attempt submission without required dates"* in `OQ-036`) are accurately translated without any hardcoded OnePV `if/else` rules.

---

## 4. Phase 3: ARIA-Snapshot Compiler & Deterministic Action Cache (`backend/aria_compiler.py` & `backend/agents.py`)

### Goal
Eliminate repeated LLM calls and make Playwright adapt to any website by compiling step intents against Playwright's `locator.aria_snapshot()` YAML tree and caching the compiled `LockedProtocolPlan` on disk.

### Step-by-Step Implementation Instructions
1. **Create `backend/aria_compiler.py`:**
   - Implement `capture_scoped_aria_snapshot(page: Page, container: Optional[Locator] = None) -> str`:
     ```python
     async def capture_scoped_aria_snapshot(page: Page, container: Optional[Locator] = None) -> str:
         target = container if (container and await container.is_visible()) else page.locator("body")
         # Playwright's native YAML accessibility tree snapshot (~300-600 tokens)
         return await target.aria_snapshot()
     ```
   - Implement `PlanCacheManager`:
     - Store cached plans under `backend/artifacts/plan_cache/{product_id}/{protocol_sha256}.json`.
     - Compute `protocol_sha256` from the normalized text of all protocol steps (`step_id + procedure + expected_result`).
     - **Cache Hit Path (0 AI Tokens):** When a protocol with a matching `protocol_sha256` is loaded, return the saved `LockedProtocolPlan` immediately in `0.01s` with `0` LLM calls.
     - **Cache Miss / New UI Path:** Compile the `LockedProtocolPlan` from the Stage 1 extraction and save it to disk.
   - Implement **Runtime JIT Healer (`heal_step_locator_with_aria`)**:
     - During execution, if a `CompiledControlLocator` cannot be found on the page (because the application UI changed or uses non-standard labels), capture the current section's `aria_snapshot()` (~300 tokens) and make **1 targeted LLM repair call** asking:
       *"Given this step field `{label}` (`{control_type}`) and the current live ARIA YAML snapshot below, return the exact `aria_role` and `accessible_name` from the snapshot that corresponds to `{label}`. If no matching element exists in the snapshot, return `null`."*
     - Log the healer action in `audit_trail.jsonl` (`HEALER_LOCATOR_UPDATED`) and update the cached plan if verified.
2. **Unify `PlaywrightGeneratorAgent` (`backend/agents.py:626-787`):**
   - Refactor `PlaywrightGeneratorAgent.generate_spec()` so it generates `.spec.ts` directly from `session.planned_steps` (`LockedStepSpec`) and emits **real Playwright assertions** instead of `await expect(page.locator('body')).not.toBeEmpty();`:
     - `FIELD_VALUE` $\rightarrow$ `await expect(page.getByLabel('Generic Name')).not.toBeEmpty();`
     - `STATUS_BADGE` $\rightarrow$ `await expect(page.getByText('MedDRA')).toBeVisible();`
     - `MESSAGE_DISPLAYED` $\rightarrow$ `await expect(page.getByRole('dialog')).toContainText(/successfully|saved/i);`
     - `VIEW_ACTIVE` $\rightarrow$ `await expect(page).toHaveURL(/.../i);`
     - `ARIA_STATE_CHANGED` $\rightarrow$ `await expect(page.locator('main')).toMatchAriaSnapshot(...);`

---

## 5. Phase 4: Zero-False-Positive Playwright Runner (`backend/playwright_runner.py`)

### Goal
Refactor `backend/playwright_runner.py` so that:
1. It works on **any web UI framework** (native HTML, React, Angular, MUI, Ant Design, Shadcn/Radix, Salesforce/Veeva iframes).
2. It **never** produces a false positive (every skipped field, unmatched dropdown option, silent HTTP error, or failed navigation immediately marks the step `FAIL`).
3. It produces **two-stage stitched evidence screenshots** (`Form State` + `Modal Confirmation State`).

### Exact Code Fixes to Implement in `backend/playwright_runner.py`

#### 5.1 Fix `find_semantic_control()` to Support Iframes & ARIA Snapshots (`lines 170-225`)
- Search in order: `[active_modal, active_section_container, page.main_frame, *page.frames]`.
- Match using:
  1. `scope.get_by_role(compiled.aria_role, name=compiled.accessible_name)` (when compiled from ARIA snapshot)
  2. `scope.get_by_label(clean_label, exact=True)` and regex prefix match
  3. `scope.get_by_role("textbox" | "combobox" | "spinbutton" | "switch" | "checkbox", name=...)`
  4. Custom framework label-to-control XPath (supporting MUI `.MuiFormControl-root`, AntD `.ant-form-item`, Bootstrap `.form-group`, and standard `<label>` siblings/ancestors)
  5. `scope.get_by_placeholder(clean_label, exact=False)`

#### 5.2 Upgrade `safe_select_option()` for Custom Dropdowns & Remove Blind `index=1` Fallback (`lines 285-403`)
Replace the current `safe_select_option()` with a universal implementation:
```python
async def safe_select_option(
    page: Page,
    loc: Locator,
    target: str,
    allow_any_default: bool = False,
    broadcast_fn=None,
    label: str = ""
) -> Tuple[bool, str]:
    """
    Universal dropdown selector supporting native <select> AND custom ARIA/React/MUI/AntD comboboxes.
    Returns (success: bool, selected_text_or_error: str).
    NEVER falls back to index=1 when an explicit target value is required.
    """
    if not await check_visible(loc):
        return False, f"Dropdown '{label}' is not visible"

    tag = await loc.evaluate("el => el.tagName.toLowerCase()")
    target_clean = (target or "").strip()

    # CASE A: Native HTML <select>
    if tag == "select":
        options = await loc.evaluate(
            "el => Array.from(el.options).map((o, idx) => ({idx, text: o.text.trim(), val: o.value}))"
        )
        valid_options = [o for o in options if o["val"] != "" and not o["text"].lower().startswith("select")]

        if (not target_clean or target_clean.startswith("(")) and allow_any_default:
            if valid_options:
                chosen = valid_options[0]
                await loc.select_option(value=chosen["val"], timeout=2000)
                return True, chosen["text"]
            return False, f"Dropdown '{label}' has no selectable options"

        # Exact or normalized match
        tgt_l = target_clean.lower().rstrip(".")
        synonyms = {tgt_l}
        if tgt_l in ["serious", "y", "yes", "true"]:
            synonyms.update(["serious", "yes", "y", "true"])
        elif tgt_l in ["non-serious", "not serious", "n", "no", "false"]:
            synonyms.update(["non-serious", "not serious", "no", "n", "false"])

        for opt in valid_options:
            opt_t = opt["text"].lower().rstrip(".")
            opt_v = opt["val"].lower().rstrip(".")
            if opt_t in synonyms or opt_v in synonyms or tgt_l in opt_t or opt_t in tgt_l:
                await loc.select_option(value=opt["val"], timeout=2000)
                return True, opt["text"]

        # STRICT FAILURE: Do NOT select index=1 when target was not found!
        available_str = ", ".join(o["text"] for o in valid_options[:8])
        return False, f"Option '{target_clean}' not found in '{label}'. Available: [{available_str}]"

    # CASE B: Custom UI Framework Combobox / Div / Button Portal (MUI, AntD, Radix, React-Select)
    await safe_click(loc, broadcast_fn=broadcast_fn, label=f"Open {label} dropdown")
    await page.wait_for_timeout(250)

    portal_options = page.locator(
        "[role='listbox'] [role='option'], [role='menu'] [role='menuitem'], "
        ".ant-select-item-option, .MuiMenuItem-root, .select__option"
    )
    count = await portal_options.count()
    if count == 0:
        return False, f"Custom combobox '{label}' did not open any option list"

    if (not target_clean or target_clean.startswith("(")) and allow_any_default:
        first_opt = portal_options.first
        txt = (await first_opt.inner_text()).strip()
        await safe_click(first_opt, broadcast_fn=broadcast_fn, label=f"Selected {txt}")
        return True, txt

    tgt_l = target_clean.lower()
    for i in range(count):
        opt_loc = portal_options.nth(i)
        if not await check_visible(opt_loc):
            continue
        opt_txt = (await opt_loc.inner_text()).strip()
        if opt_txt.lower() == tgt_l or tgt_l in opt_txt.lower():
            await safe_click(opt_loc, broadcast_fn=broadcast_fn, label=f"Selected {opt_txt}")
            return True, opt_txt

    await page.keyboard.press("Escape")
    return False, f"Option '{target_clean}' not found in custom combobox '{label}'"
```

#### 5.3 Enforce 100% Field Execution Parity in Step Loop (`lines 1255-1314`)
Replace the permissive `if loc:` loop so missing or un-populated fields immediately record a failure:
```python
missing_or_failed_fields: List[str] = []

for fa in (planned_step.field_actions if planned_step else []):
    if fa.control_type == "auto_populate_verify" or fa.expect_auto_populated:
        continue  # Verified in post-action assertion phase

    loc = await find_semantic_control(page, fa.label, fa.control_type, section_hint=fa.section, container=scope_target)
    if not loc:
        # Attempt 1 JIT ARIA Healer lookup before failing
        loc = await heal_step_locator_with_aria(page, step, fa, scope_target)

    if not loc:
        missing_or_failed_fields.append(f"Control '{fa.label}' ({fa.control_type}) not found on screen")
        continue

    if fa.control_type in ["text", "date"]:
        ok = await human_fill(page, loc, val, broadcast_fn=broadcast_frame, label=fa.label)
        if not ok:
            missing_or_failed_fields.append(f"Failed to fill '{fa.label}' with '{val}'")
        else:
            filled_count += 1
    elif fa.control_type == "select":
        allow_any = not bool(fa.target_value) or fa.target_value.startswith("(")
        ok, detail = await safe_select_option(page, loc, fa.target_value, allow_any_default=allow_any, broadcast_fn=broadcast_frame, label=fa.label)
        if not ok:
            missing_or_failed_fields.append(detail)
        else:
            filled_count += 1
```
If `missing_or_failed_fields` is non-empty on a positive test step, immediately mark the step `FAIL` with the exact list of missing/failed controls.

#### 5.4 Wire Up Two-Stage Screenshot Stitching (`lines 535-569` & `1436-1454`)
Whenever a step populates form fields AND clicks an action/submit button (`Save`, `Save and Submit`, `Register`, `Select`, `Delete`):
1. **Before clicking `Save`/`Submit`:** Capture `form_img = await capture_evidence(step.step_id, "_form", stamp_banner=False)`.
2. **Click `Save`/`Submit` and wait for confirmation dialog/toast:** Capture `modal_img = await capture_evidence(step.step_id, "_modal", stamp_banner=False)`.
3. **Stitch & Stamp:** Call `stitch_two_stage_screenshots(Path(form_img), Path(modal_img), combined_path)` and then call `stamp_gxp_metadata_banner(combined_path, step_id=step.step_id, case_id=..., tester=...)`.
4. Call `assign_step_screenshots(step, session.session_id, form_img, modal_img, combined_path)`.

#### 5.5 Fix `verify_expected_result()` to Eliminate All False Positives (`lines 632-906`)
1. **Capture Pre-Step Snapshot & Network Status:**
   - Before executing the step's actions, capture:
     - `pre_aria = await capture_scoped_aria_snapshot(page, sec_container)`
     - `pre_table_rows = await count_data_rows(sec_container or page)`
     - Attach a temporary listener `failed_http_responses = []` (`page.on("response", ...)` for `status >= 400` on XHR/fetch requests).
2. **Disqualify Any Positive Step with HTTP/Console/ARIA Invalid Errors:**
   - Check `post_aria` for `[invalid]` (`aria-invalid="true"`), check DOM for `:invalid`, `.Mui-error`, `.ant-form-item-explain-error`, `[role="alert"]`, and check `failed_http_responses`. If any are present during a positive test step, return `(False, f"Discrepancy: UI/API error detected: {err}", err)`.
3. **Fix `VIEW_ACTIVE` (`lines 855-890`):**
   - Change every `else:` branch in `VIEW_ACTIVE` from `passed_details.append(...)` to `failed_details.append(f"Expected view '{tgt}' not active at URL {page.url}")`.
4. **Fix `TABLE_DATA` (`lines 793-818`):**
   - For row additions, require `post_table_rows > pre_table_rows` **AND** verify that at least one visible row in `tbody` contains the non-empty values entered during this step.
   - For row deletions, require `post_table_rows < pre_table_rows` (or `post_table_rows == 0` when 1 row existed previously).
5. **Fix `FILE_DOWNLOAD` (`lines 842-853`):**
   - Wrap export/download button clicks in `async with page.expect_download(timeout=10000) as download_info:` and verify `download = await download_info.value` has a valid filename and non-zero file size on disk.

---

## 6. Phase 5: FDA 21 CFR Part 11, CSA & ALCOA+ Compliance (`backend/audit_trail.py`, `backend/docx_writer.py`, `backend/main.py`)

### Goal
Ensure every generated record, timestamp, screenshot watermark, and Word document sign-off satisfies [FDA 21 CFR Part 11](https://www.ecfr.gov/current/title-21/chapter-I/subchapter-A/part-11), [FDA Computer Software Assurance (CSA)](https://www.fda.gov/regulatory-information/search-fda-guidance-documents/computer-software-assurance-production-and-quality-management-system-software), and [ISPE GAMP 5 ALCOA+](https://valkit.ai/blog/gamp-5-data-integrity).

### Step-by-Step Implementation Instructions
1. **Remove All Hardcoded Dates & Static SHAs:**
   - In `playwright_runner.py:1511-1512`, replace `"S.B. / 15-Oct-2026"` with:
     ```python
     now_utc_str = datetime.datetime.now(datetime.timezone.utc).strftime("%d-%b-%Y %H:%M UTC")
     tester_initials = compute_initials(creds.get("username", "Tester"))
     step.tester_initials_date = f"{tester_initials} / {now_utc_str}"
     step.initials_date = step.tester_initials_date
     ```
   - In `extractor.py:616` and `main.py:134`, compute the actual Git commit SHA via `subprocess.check_output(["git", "rev-parse", "--short", "HEAD"])` combined with the first 8 characters of the uploaded `.docx` file's SHA-256 hash.
2. **Create `backend/audit_trail.py` (Hash-Chained Append-Only Audit Log):**
   - Write every lifecycle event (`PROTOCOL_UPLOADED`, `PLAN_COMPILED`, `EXECUTION_STARTED`, `STEP_PASSED`, `STEP_FAILED`, `HUMAN_REVIEW_CONTINUED`, `ELECTRONIC_SIGNATURE_APPLIED`, `DOSSIER_ARCHIVED`) to `backend/artifacts/archive/{session_id}/audit_trail.jsonl`.
   - Each entry computes `entry_hash = sha256(f"{sequence_no}|{timestamp_utc}|{session_id}|{actor_username}|{event_type}|{details}|{prev_hash}")`.
   - Update `/api/approve-review/{session_id}` in `main.py` to require a `justification: str` field in the request body whenever a human reviewer acknowledges a failed step and continues execution.
3. **Fix `backend/docx_writer.py` for Multi-Table Write-Back & Part 11 Signature Separation:**
   - Use `step.col_map` (discovered in Phase 2) instead of hardcoded `col_pass_fail = 4` and `col_initials = 5`. If the protocol table has a separate `Actual / Observed Result` column (`col_map.observed_col is not None`), write `step.observed_result` into `observed_col` and `"Pass"` / `"Fail"` into `pass_fail_col`. If they share a column, write both into `pass_fail_col`.
   - Remove hardcoded `"TMP-CASE-1001"`, `"TMP-CASE-7214"`, and `"CASE-2026-0042"` replacements at lines 210–225.
   - **Critical Part 11 Fix (`lines 91-96`):** Do **not** auto-populate `"QA / CSV Lead"` into the `Reviewed By` row of Table 6 / Table 9 during test execution! Leave `Reviewed By` blank until a user with `role="QA_REVIEWER"` calls the new `POST /api/sign-protocol/{session_id}` endpoint with their credentials and signature meaning.

---

## 7. Phase 6: Automated Verification & Acceptance Script (`backend/verify_v3_architecture.py`)

After implementing Phases 1–5, create and run `backend/verify_v3_architecture.py` to verify all five acceptance gates:

1. **Gate A — Multi-Format Extraction Parity:** Run `extract_protocol()` on both `CLIN-EU-PAT-OPV-1-1-PQ-022` (1 execution table, 18 steps) and `CLIN-EU-VAL-OPV-1-1-OQ-036` (2 execution tables, 2 sign-off tables). Assert 100% step and field extraction with accurate `TableColumnMap` indices.
2. **Gate B — Zero-Token Cache Replay:** Run `generate_plan()` twice on the same protocol. Assert that Run #1 compiles and caches `locked_plan.json`, and Run #2 completes in `< 50ms` with `llm_call_count == 0`.
3. **Gate C — Zero False Positives (Negative & Sabotage Tests):**
   - Pass a bogus dropdown option (`"NonExistentOption_XYZ"`) to `safe_select_option()` and assert it returns `(False, ...)` instead of selecting `index=1`.
   - Pass a non-existent field label (`"NonExistentField_999"`) in `planned_step.field_actions` and assert the step status is `"FAIL"`.
   - Trigger `verify_expected_result()` with `VIEW_ACTIVE` (`target_text="case processing"`) while on `/login` and assert it returns `is_passed == False`.
4. **Gate D — Two-Stage Stitched Screenshot Verification:** Execute a form-save step with `requires_form_screenshot=True` and `requires_modal_screenshot=True`. Assert that `{step_id}_form.png`, `{step_id}_modal.png`, and the stitched `{step_id}.png` all exist on disk, and that `{step_id}.png` height equals `form_height + modal_height + 36` (the 36px 21 CFR Part 11 UTC watermark banner).
5. **Gate E — 21 CFR Part 11 Signature & Audit Trail Verification:** Generate the executed `.docx` before QA sign-off and assert `Reviewed By` is empty; then invoke `/api/sign-protocol/{session_id}` as `QA_REVIEWER`, regenerate `.docx`, and assert `Reviewed By` is populated and `audit_trail.jsonl` passes SHA-256 hash-chain verification.
