# UNIVERSAL REMEDIATION HARNESS: One-Fix-at-a-Time Execution Spec (`testvalid` v4.2)

> **CRITICAL DIRECTIVE FOR THE 3.8 FLASH AI IDE AGENT:**
> You are upgrading `testvalid` so that it handles **any validation protocol document on any web application** with **zero document-specific hardcoding**, while raising complex multi-table OQ/PQ protocol pass rates to **95–100%**.
>
> **NON-NEGOTIABLE RULES FOR THE AI IDE:**
> 1. **Execute Strictly ONE Fix Phase per Turn:** When instructed to run **FIX 1**, implement **ONLY FIX 1**, run `PYTHONPATH=backend python backend/verify_universal_fix1.py` and `PYTHONPATH=backend python backend/verify_v3_architecture.py`, paste the terminal output, and **STOP** for developer approval. Never implement Fix 2 or Fix 3 in the same turn!
> 2. **ZERO Document or Application Hardcoding:**
>    - You are **strictly forbidden** from hardcoding step IDs (`if step_id == "TS1-S19"`), document names (`if "OQ-036" in filename`), or application-specific field names (`if "Patient Information" in line`) in any logic.
>    - Every algorithm in `extractor.py`, `agents.py`, `verification_engine.py`, and `playwright_runner.py` must be written using **universal structural, grammatical, and DOM-topology patterns** that work on any LIMS, ERP, Safety, or Clinical web app.
> 3. **Never Truncate Step Text at `[:400]`:** Complex validation steps often exceed 800–1,200 characters. Slicing `procedure[:400]` deletes the bottom half of the test step. Preserve full step text (`[:2500]`) and use **Section-Coherent Step Batching** (`20–25` complete steps per LLM batch) so output tokens never overflow.
> 4. **Never Weaken Verification Tests:** If a test in `verify_universal_fix{1,2,3}.py` fails, fix the root cause in the backend code—never weaken or delete the test assertion.

---

## OVERVIEW OF THE 3 UNIVERSAL FIX PHASES (EXECUTE ONE AT A TIME)

| Fix Phase | Target Files | Universal Engineering Upgrade (Zero Hardcoding) | Verification Harness |
| :--- | :--- | :--- | :--- |
| **FIX 1: Universal Structural & Checkpoint-Aligned Extractor + Lossless Batching** | `backend/schemas.py`, `backend/extractor.py`, `backend/agents.py` | 1. **Universal Instructional Header Filter:** Grammar pattern that distinguishes section/context switching sentences (*"Under &lt;X&gt; section, &lt;verb&gt; the below details"*) from actual `<input>` labels on any document.<br>2. **Multi-Line Key-Instruction Pairing:** Extracts colon-less field labels followed by parenthetical instructions on the next line.<br>3. **Checkpoint-Aligned Sub-Step Graph (`StepCheckpoint`):** Decomposes any compound step containing multiple checkpoint anchors (`(Refer expected result 1..k)` or multi-paragraph expectations) into ordered sub-steps with independent `POSITIVE` / `NEGATIVE` polarity.<br>4. **Lossless Window Batching:** Removes `[:400]` slicing and batches complete steps cleanly. | `backend/verify_universal_fix1.py` |
| **FIX 2: Causal 3-Signal Verifier & Checkpoint-by-Checkpoint State Machine** | `backend/verification_engine.py`, `backend/playwright_runner.py` | 1. **Generic vs. Specific Expectation Classifier:** Automatically detects whether an expected error is a generic meta-statement (*"System shall display error message"*) or a specific constraint (*"Admission Date cannot be in the future"*).<br>2. **Causal 3-Signal Correlation:** Verifies generic negative steps via (a) Error UI/Toast presence + non-500 HTTP, (b) Blocked entity creation, and (c) Causal check that the error does not blame fields already verified filled.<br>3. **Compound Checkpoint State Machine:** Evaluates multi-checkpoint steps (`NEGATIVE -> POSITIVE` or `POSITIVE -> NEGATIVE`) at each checkpoint boundary and auto-triggers post-step cleanup actions (`Reset` / `Cancel` / `Close`). | `backend/verify_universal_fix2.py` |
| **FIX 3: Universal DOM Topology Resolver (Grid Cells, Modals, Downloads & Accordions)** | `backend/playwright_runner.py` | 1. **Table Column-Header-to-Cell Input Resolver:** When a target label matches a `<th>` column header inside a `<table>` or `[role="grid"]`, dynamically locates the interactive `<input>`/`<select>`/`<textarea>` inside the corresponding `<td>` column index of the active row.<br>2. **Stateful Option Rotation for Repeated Imports:** Tracks previously selected options in a session so repeated template/record selection steps automatically pick the next unconsumed option.<br>3. **Universal Modal Action & Download Interceptor:** Handles inline row edit triggers (`Edit`/`Update` icons), `page.expect_download()` streams, and expandable `View`/accordion links inside dialogs. | `backend/verify_universal_fix3.py` |

---

## PHASE 1 (FIX 1): Universal Structural & Checkpoint-Aligned Extractor + Lossless Batching (`backend/schemas.py`, `backend/extractor.py`, `backend/agents.py`)

### 1.1 Add Universal `StepCheckpoint` Model to `backend/schemas.py`
In `backend/schemas.py`, add `StepCheckpoint` and attach `checkpoints: List[StepCheckpoint] = Field(default_factory=list)` and `is_compound_polarity: bool = False` to `ProtocolStep`:

```python
class StepCheckpoint(BaseModel):
    checkpoint_index: int                    # 1, 2, 3... in order of execution within the step
    procedure_segment: str                   # Sub-procedure text leading up to this checkpoint
    expected_segment: str                    # Aligned expected result clause/paragraph
    polarity: Literal["POSITIVE", "NEGATIVE"] = "POSITIVE"
    verified: bool = False
    observed_detail: str = ""
```
On `ProtocolStep`, add:
```python
    checkpoints: List[StepCheckpoint] = Field(default_factory=list)
    is_compound_polarity: bool = False
```

---

### 1.2 Upgrade `extract_fields_from_procedure()` in `backend/extractor.py` (100% Universal Grammar Rules)
In `backend/extractor.py`, replace the brittle regexes in `extract_fields_from_procedure()` with these three universal grammatical rules:

1. **Universal Section-Switch & Instructional Directive Filter (Never Extract Directives as Field Labels):**
   In any qualification protocol, authors write directive headers like *"Under &lt;Container&gt; [section/tab/page], <enter/update/fill/select> the <below/following> <details/fields/data>:"*.
   At the top of the `while i < len(lines):` loop in `extract_fields_from_procedure()`, add:

```python
        # 1. Universal Section-Switch & Instructional Directive Filter
        # Matches any sentence of the form: "(Under|In|On|Go to) <Section Name> [section|tab|page] [enter|update|fill|select ...]"
        directive_match = re.match(
            r'^(?:under|in|on|go\s+to|navigate\s+to)\s+(?:the\s+)?([A-Za-z0-9\s/&-]{2,45}?)(?:\s+(?:section|tab|page|screen|panel|card|sub-section|grid|table))?(?:\s+(?:enter|update|fill|select|verify|provide|input|complete)\b.*)?[\:\.\,]?$',
            line,
            re.IGNORECASE
        )
        is_meta_directive = any(
            re.search(pat, line_l) for pat in [
                r'\b(?:enter|update|fill|select|provide)\s+(?:the\s+)?(?:below|following)\s+(?:details|fields|data|values|information)\b',
                r'\b(?:enter|update|fill)\s+(?:the\s+)?data\s+in\s+(?:the\s+)?(?:below|following)\b',
                r'^\s*\(\s*refer\s+expected\s+result',
                r'^\s*note\s*:'
            ]
        )
        if directive_match or is_meta_directive:
            if directive_match:
                cand_sec = directive_match.group(1).strip()
                # Strip trailing directive verbs/nouns if captured inside group 1
                cand_sec = re.sub(
                    r'\s+(?:section|tab|page|screen|panel|enter|update|fill|select|the|below|following|details|fields|data).*$',
                    '',
                    cand_sec,
                    flags=re.IGNORECASE
                ).strip()
                generic_containers = {
                    "left menu", "homepage", "the following", "browser", "validation",
                    "below dropdowns", "response column", "below fields", "below details"
                }
                if cand_sec and cand_sec.lower() not in generic_containers and len(cand_sec) <= 35:
                    current_section = re.sub(r'[^a-zA-Z0-9]+', '_', cand_sec.lower()).strip('_')
            i += 1
            continue
```

2. **Guard `field_match` Against Long Sentence Clauses:**
   Inside `if field_match:` (where `Label: Value` is matched), reject any `label_candidate` where:
   - `len(label_candidate) > 42` or `len(label_candidate.split()) > 6`, OR
   - `re.search(r'\b(enter|update|fill|click|navigate|refer|below|following|section|page)\b', lc)` is True.

3. **Universal Multi-Line Label + Parenthetical Instruction Rule (Colon-Less Fields):**
   Many protocol templates format fields across two lines without a colon:
   ```text
   Field Label Name
        (Enter the data / Update the value from dropdown / Select date)
   ```
   Right after the `if field_match:` block inside `extract_fields_from_procedure()`, add this universal two-line lookahead parser:

```python
        # 4. Universal Two-Line Colon-Less Field Pattern:
        # Line i: Short noun-phrase field label (no colon, <= 5 words)
        # Line i+1: Parenthetical instruction e.g. "(Enter the data)", "(Update the date)", "(Select from dropdown)"
        if ":" not in line and i + 1 < len(lines):
            next_line = lines[i + 1].strip()
            is_parenthetical_inst = (
                next_line.startswith("(")
                and next_line.endswith(")")
                and "refer expected" not in next_line.lower()
                and "µ" not in next_line
            )
            is_valid_field_noun = (
                re.match(r'^[A-Za-z][A-Za-z0-9\s/&\-\(\)]{1,35}$', line) is not None
                and len(line.split()) <= 5
                and not re.match(r'^(?:click|open|navigate|from|in|under|on|directly|verify|check|press|note)\b', line_l)
            )
            if is_parenthetical_inst and is_valid_field_noun:
                label = line.strip()
                raw_inst = next_line
                inst_l = raw_inst.lower()
                lbl_l = label.lower()

                ctrl_type: ControlType = "text"
                search_trigger = False
                auto_pop = False
                if "search icon" in inst_l or ("search" in inst_l and ("select" in inst_l or "modal" in inst_l)):
                    ctrl_type = "modal_search_select"
                    search_trigger = True
                elif "auto-populate" in inst_l or "auto populate" in inst_l:
                    ctrl_type = "auto_populate_verify"
                    auto_pop = True
                elif "toggle" in inst_l or "switch" in inst_l:
                    ctrl_type = "toggle"
                elif "date" in lbl_l or "birth" in lbl_l or "dob" in lbl_l or "date" in inst_l or "calendar" in inst_l:
                    ctrl_type = "date"
                elif any(k in inst_l for k in ["dropdown", "select from", "choose", "value from dropdown", "from dropdown"]):
                    ctrl_type = "select"

                field_counter += 1
                extracted_fields.append(ExtractedFieldSpec(
                    field_id=f"{step_id}-F{field_counter:02d}",
                    section=current_section,
                    label=label,
                    raw_instruction=raw_inst,
                    control_type=ctrl_type,
                    explicit_value=None,
                    search_trigger_icon=search_trigger,
                    auto_populated=auto_pop
                ))
                i += 2
                continue
```

---

### 1.3 Add Universal Checkpoint-Aligned Sub-Step Decomposition in `backend/extractor.py`
In any protocol where a single step contains multiple verification checkpoints (marked by `(Refer expected result 1)`, `(Refer expected result 2)` or multiple expected result paragraphs), add `extract_step_checkpoints(procedure: str, expected_result: str) -> Tuple[List[StepCheckpoint], bool]` in `backend/extractor.py`:

```python
def classify_segment_polarity(expected_segment: str) -> Literal["POSITIVE", "NEGATIVE"]:
    low = (expected_segment or "").lower()
    neg_terms = [
        "error message", "validation error", "shall not allow", "cannot ", "must not",
        "block", "prevent", "reject", "invalid", "mandatory", "required field"
    ]
    pos_terms = [
        "successfully", "confirmation message", "shall save", "shall add", "shall update",
        "shall delete", "shall create", "auto populate", "auto-populate", "shall display"
    ]
    has_neg = any(k in low for k in neg_terms)
    if has_neg and not any(p in low for p in ["delete the", "save successfully", "update successfully", "register case successfully"]):
        return "NEGATIVE"
    return "POSITIVE"

def extract_step_checkpoints(procedure: str, expected_result: str) -> Tuple[List[StepCheckpoint], bool]:
    """
    Universal Checkpoint Decomposer (LangGraph-style Sub-Step Alignment):
    Splits a multi-part procedure at '(Refer expected result [k])' anchors and aligns each
    sub-procedure with its corresponding paragraph in expected_result.
    """
    exp_paragraphs = [p.strip() for p in re.split(r'\n\s*\n|\n+', (expected_result or "").strip()) if p.strip()]
    ref_pattern = re.compile(r'\(\s*refer\s+expected\s+result\s*(\d+)?\s*\)', re.IGNORECASE)
    matches = list(ref_pattern.finditer(procedure or ""))

    checkpoints: List[StepCheckpoint] = []
    if len(matches) >= 2 and len(exp_paragraphs) >= 2:
        last_idx = 0
        for idx, m in enumerate(matches):
            proc_seg = (procedure[last_idx:m.start()] or "").strip()
            last_idx = m.end()
            # Map explicit number if present (e.g. 'Refer expected result 2' -> index 1), else sequential
            explicit_num = int(m.group(1)) - 1 if (m.group(1) and m.group(1).isdigit()) else idx
            exp_idx = max(0, min(explicit_num, len(exp_paragraphs) - 1))
            exp_seg = exp_paragraphs[exp_idx]
            checkpoints.append(StepCheckpoint(
                checkpoint_index=idx + 1,
                procedure_segment=proc_seg,
                expected_segment=exp_seg,
                polarity=classify_segment_polarity(exp_seg)
            ))
    elif len(exp_paragraphs) >= 2:
        # Even without explicit '(Refer expected result k)' tags, check if expected_result has mixed polarity paragraphs
        pols = [classify_segment_polarity(p) for p in exp_paragraphs]
        if len(set(pols)) > 1:
            for idx, exp_seg in enumerate(exp_paragraphs):
                checkpoints.append(StepCheckpoint(
                    checkpoint_index=idx + 1,
                    procedure_segment=(procedure or "").strip(),
                    expected_segment=exp_seg,
                    polarity=pols[idx]
                ))

    if not checkpoints:
        checkpoints.append(StepCheckpoint(
            checkpoint_index=1,
            procedure_segment=(procedure or "").strip(),
            expected_segment=(expected_result or "").strip(),
            polarity=classify_segment_polarity(expected_result or "")
        ))

    is_compound = len({cp.polarity for cp in checkpoints}) > 1
    return checkpoints, is_compound
```
Wire `checkpoints, is_compound = extract_step_checkpoints(procedure_text, expected_text)` into `extract_protocol()` in `backend/extractor.py` and pass `checkpoints=checkpoints, is_compound_polarity=is_compound` to `ProtocolStep(...)`.

---

### 1.4 Remove `[:400]` Slicing & Implement Lossless Step-Batching in `backend/agents.py`
In `backend/agents.py` inside `PlannerAgent.query_qwen_single_batch()`:
1. **Remove `[:400]` character slicing!** Pass full `s.procedure[:2500]` and `s.expected_result[:800]`.
2. **Batch by 25 steps maximum per call (`BATCH_SIZE = 25`):**
   - For an 18-step protocol, `math.ceil(18 / 25) == 1` call.
   - For a 50-step protocol, `math.ceil(50 / 25) == 2` calls (`max_allowed_calls = max(1, math.ceil(len(session.steps) / 25))`), preventing JSON output truncation while keeping the entire 50-step protocol under ~4,500 tokens total!

---

### 1.5 Create & Run Fix 1 Verification Harness (`backend/verify_universal_fix1.py`)
Create `backend/verify_universal_fix1.py` testing both **synthetic universal prose/multi-line protocols** AND the uploaded protocols in `backend/uploads/`:

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from extractor import extract_fields_from_procedure, extract_step_checkpoints, extract_protocol

def test_universal_directive_filtering_and_multiline_fields():
    print("[Check 1] Testing universal section directive filter & colon-less 2-line field extraction...")
    sample_proc = """
    In the Clinical Portal page, enter the data in below fields,
    Under Subject Demographics section enter the below details:
    Subject Initials
         (Enter the data)
    Enrollment Status: Active
         (Select from the dropdown)
    Birth Date
         (Select date)
    Under Lab Assessment Section Update the below details:
    Primary Lab Country
         (Update the value from dropdown)
    Click on Save button.
    """
    fields = extract_fields_from_procedure("TEST-S01", "general", sample_proc)
    labels = [f.label for f in fields]
    sections = {f.label: f.section for f in fields}
    types = {f.label: f.control_type for f in fields}
    print(f"  -> Extracted fields: {[(f.label, f.section, f.control_type) for f in fields]}")

    assert len(fields) == 4, f"Expected exactly 4 fields, got {len(fields)}: {labels}"
    assert "Subject Initials" in labels and types["Subject Initials"] == "text"
    assert "Enrollment Status" in labels and types["Enrollment Status"] == "select"
    assert "Birth Date" in labels and types["Birth Date"] == "date"
    assert "Primary Lab Country" in labels and types["Primary Lab Country"] == "select"
    assert sections["Subject Initials"] == "subject_demographics"
    assert sections["Primary Lab Country"] == "lab_assessment"
    print("  -> PASS: Directives filtered cleanly, sections tracked, and colon-less 2-line fields extracted!")

def test_universal_checkpoint_decomposition():
    print("[Check 2] Testing universal checkpoint sub-step decomposition...")
    proc_a = (
        "Open record list and click Delete icon.\n"
        "Directly click on Confirm Delete button.\n(Refer expected result 1)\n"
        "Enter audit reason for deletion.\n"
        "Click on Confirm Delete button.\n(Refer expected result 2)"
    )
    exp_a = "Error message shall display.\n\nSystem shall delete the record successfully with confirmation message."
    cps_a, is_comp_a = extract_step_checkpoints(proc_a, exp_a)
    assert is_comp_a is True and len(cps_a) == 2
    assert cps_a[0].polarity == "NEGATIVE" and cps_a[1].polarity == "POSITIVE"
    print(f"  -> PASS: Pattern A (NEGATIVE -> POSITIVE) decomposed into {len(cps_a)} checkpoints.")

    proc_b = (
        "Under Product section select Drug X (Refer expected result 1).\n"
        "Under Event section code term (Refer expected result 2).\n"
        "Leave Reporter blank and click Submit (Refer expected result 3)."
    )
    exp_b = (
        "Generic name shall auto populate.\n\n"
        "Term shall code successfully.\n\n"
        "System shall display error message."
    )
    cps_b, is_comp_b = extract_step_checkpoints(proc_b, exp_b)
    assert is_comp_b is True and len(cps_b) == 3
    assert [c.polarity for c in cps_b] == ["POSITIVE", "POSITIVE", "NEGATIVE"]
    print(f"  -> PASS: Pattern B (POSITIVE -> POSITIVE -> NEGATIVE) decomposed into {len(cps_b)} checkpoints.")

def test_uploaded_protocols_zero_header_leakage():
    print("[Check 3] Verifying zero directive/header leakage across all .docx protocols in uploads/...")
    uploads = list(Path("backend/uploads").glob("*Manual*.docx")) or list(Path("uploads").glob("*Manual*.docx"))
    for docx_file in uploads:
        session = extract_protocol(str(docx_file))
        for s in session.steps:
            for ef in s.extracted_fields:
                low = ef.label.lower()
                assert "below details" not in low and "below fields" not in low, (
                    f"Directive leaked as field in {docx_file.name} [{s.step_id}]: '{ef.label}'"
                )
        print(f"  -> Verified {docx_file.name}: {len(session.steps)} steps, 0 directive leaks.")

if __name__ == "__main__":
    print("=== RUNNING UNIVERSAL FIX 1 VERIFICATION SUITE ===")
    test_universal_directive_filtering_and_multiline_fields()
    test_universal_checkpoint_decomposition()
    test_uploaded_protocols_zero_header_leakage()
    print("=== [100% PASS] UNIVERSAL FIX 1 COMPLETE! ===")
```
