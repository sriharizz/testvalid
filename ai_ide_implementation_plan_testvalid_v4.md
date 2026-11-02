# AI Coding IDE Master Implementation Plan: Universal Hybrid Guided-Micro-Agent, Zero-False-Positive & FDA 21 CFR Part 11 Validation Platform (`testvalid` v4)

> **Instructions for the AI Coding IDE (Cursor / Windsurf / Claude Code / Cline / Copilot):**
> Always follow the persistent execution rules in `AGENTS.md`. Execute **one phase at a time** (**Phase 1 through Phase 6**). At the end of each phase, run both `PYTHONPATH=backend python backend/verify_phase<N>_v4.py` and `PYTHONPATH=backend python backend/verify_v3_architecture.py`, paste the terminal output, and wait for developer approval before starting the next phase.

---

## 1. Executive Architecture Overview & Legacy Debt Elimination

### 1.1 Exact Legacy Prototype Flaws You Are Ripping Out & Replacing
1. **In-System Authoring Still Round-Trips Through `.docx` (`backend/protocol_generator.py:83-105` & `frontend/src/components/ProtocolAuthoringModal.tsx:38-62`):**
   - Currently, clicking "Generate Protocol" in the UI writes a `.docx` file to `backend/uploads/` and then re-parses it through `extractor.py`.
   - **v4 Replacement (Phase 2):** Add a direct **"Write Test Steps in System (Direct Studio — 0 Doc Upload)"** interactive table in `ProtocolAuthoringModal.tsx` and `POST /api/author-direct-session` in `main.py` that builds a live `ProtocolSession` directly in memory (`0` `.docx` upload required), while also generating a background baseline `.docx` template so `Download Executed Protocol (.docx)` and `RightDocInspector` continue to work seamlessly.
2. **200-Line Hardcoded OnePV Dictionary in `backend/agents.py` (`lines 316-550`):**
   - `synthesize_fallback_field_action()` contains hardcoded OnePV strings (`"Alexander"`, `"Fleming"`, `"450 Oxford Street"`, `if sec == "questionnaire"`).
   - **v4 Replacement (Phase 3):** Delete those hardcoded OnePV `if/elif` blocks and replace them with a clean, schema-driven synthesizer + **Mode 1 Live-DOM Guided Micro-Agent (`bind_step_with_live_dom`)** that inspects the actual `<input>` and `<select>` controls on any target website.
3. **Blind Static Compilation & Missing Dynamic Sub-Forms (`backend/aria_compiler.py:73-150`):**
   - `compile_step_to_locked_spec()` currently guesses ARIA roles from text alone without seeing the live webpage, and sets missing values to `"Default Data"` (`line 90`).
   - **v4 Replacement (Phase 3):** Add `extract_visible_dom_controls()` (`<400`-token live DOM JS snapshotter) and `bind_step_with_live_dom()` with a **DOM Mutation Diff Loop** so conditional sections (e.g., *Hospitalization Admission Date* appearing only after selecting *Seriousness = Serious*) and dropdown synonyms (`"Physician"` $\rightarrow$ `"HCP"`) are bound dynamically on Run #1 and cached in `LockedProtocolPlan` for `0`-token replay on Run #2+.
4. **Permissive False-Positive Bugs in `verify_expected_result()` (`backend/playwright_runner.py:811-857`):**
   - **Line 828 (`ENTITY_CREATED`):** `elif combined_feedback and not detected_error: passed_details.append(...)` marks `ENTITY_CREATED` as `PASS` even when **no Case ID was created at all**!
   - **Line 820 (`ENTITY_CREATED` regex):** Matches `[A-Z]{2,}-[0-9]+`, which matches `"ERR-502"` or `"HTTP-400"` as a valid Case ID!
   - **Line 838 (`ERROR_MESSAGE`):** Marks any negative test `PASS` if the word `"error"` or `"mandatory"` appears—even if the error is for the **wrong field** (e.g., `"Reporter Country is required"` when testing `"Admission Date cannot be in the future"`).
   - **Line 856 (`MESSAGE_DISPLAYED`):** `else: passed_details.append("Action executed and form data persisted successfully")` passes even when no confirmation popup/toast appeared!
   - **v4 Replacement (Phase 4):** Create `backend/verification_engine.py` implementing the **4-Gate Zero-False-Positive Engine** (Gate 1: Polarity/HTTP Guard, Gate 2: Entity/Field Guard, Gate 3: Offline CPU Semantic Similarity, Gate 4: Grey-Zone Qwen Tie-Breaker) and wire `verify_expected_result()` to it.
5. **Unbound Screenshot Files in Audit Trail & Missing Inspector Audit Certificate (`backend/audit_trail.py` & `backend/docx_writer.py`):**
   - `audit_trail.py` currently hashes text metadata only; if someone swaps or edits `TS1-S04.png` on disk after execution, `verify_audit_trail()` still returns `True`!
   - **v4 Replacement (Phases 5 & 6):** Bind raw `.png` screenshot SHA-256 bytes (`screenshot_sha256`), `locked_spec_sha256`, `inputs_applied` provenance, and 4-Gate scores into every `AuditLogEntry` hash chain, upgrade `Screenshot_Evidence_{filename}.docx` into a full **4-Section Validation Summary & RCA Dossier**, and generate a standalone human-readable **`Audit_Trail_Certificate_{filename}.docx`** with a download button in `ExecutionSummaryModal.tsx`.

---

### 1.2 End-to-End v4 Master Data Flow

```text
[Path A: Direct System UI Studio (Siva Sai Flow)]      [Path B: .docx Upload (Legacy/Client Flow)]
                      │                                                       │
                      ▼                                                       ▼
        POST /api/author-direct-session                    extractor.py + CPU Confidence Sieve
                      │                                    (Flags messy/conditional prose steps)
                      └──────────────────────────┬────────────────────────────┘
                                                 ▼
                              Canonical ProtocolSession (in memory)
                                                 │
                      ┌──────────────────────────┴──────────────────────────┐
                      │ Check PlanCacheManager (protocol_sha256)            │
                      ▼                                                     ▼
        [CACHE MISS: Mode 1 Discovery]                        [CACHE HIT: Mode 2 Locked]
  • Playwright extracts <400-token visible DOM JSON     • Loads LockedProtocolPlan in <5ms
  • CPU Semantic Matcher binds >=0.82 labels/options    • Executes deterministically (0 LLM calls)
  • Qwen Micro-Call (<=600 tokens) ONLY for missing     • Verifies DOM .input_value() readback
    mandatory dummy data or unmapped synonyms           • Stitches _form.png + _modal.png + UTC banner
  • DOM Mutation Loop resolves conditional sub-forms
  • Saves & locks LockedProtocolPlan.json
                      │                                                     │
                      └──────────────────────────┬──────────────────────────┘
                                                 ▼
                        [Stage 4: 4-Gate Zero-False-Positive Verifier]
          Gate 1 (HTTP/Polarity) -> Gate 2 (ID/Field Guard) -> Gate 3 (CPU MiniLM) -> Gate 4
                                                 │
                                                 ▼
                     [Stage 5 & 6: Part 11 Cryptographic Seal & 3 Deliverables]
       1. Executed_Protocol.docx   2. Screenshot_Evidence_Dossier.docx   3. Audit_Trail_Certificate.docx
```

---

## 2. PHASE 1: Upgraded Schemas (`backend/schemas.py`) & Offline-Safe CPU Semantic Engine (`backend/cpu_semantic_matcher.py`)

### 2.1 Exact Additions to `backend/schemas.py`
Keep all existing models in `backend/schemas.py` intact and add the following types and models:

```python
ValueProvenance = Literal[
    "protocol_explicit",        # Value explicitly stated in Word doc or System UI table
    "cpu_semantic_match",       # Matched to DOM label/option via local CPU matcher (>= 0.80)
    "ai_mapped_synonym",        # Mapped by Qwen against live dropdown options (e.g. "Physician" -> "HCP")
    "ai_synthesized_mandatory", # Synthesized for required form field not explicitly listed in step
    "computed_dynamic"          # Dynamic runtime token resolved (e.g. TODAY, TODAY+1)
]

class AppliedInputRecord(BaseModel):
    field_label: str
    selector_used: str = ""
    value_applied: str
    original_term: Optional[str] = None
    provenance: ValueProvenance = "protocol_explicit"
    readback_verified: bool = True

class GateEvaluationResult(BaseModel):
    gate1_polarity_and_http: str = "PASS"       # e.g. "PASS (HTTP 2xx, 0 unexpected UI errors)"
    gate1_passed: bool = True
    gate2_field_and_entity_guard: str = "PASS"  # e.g. "PASS (Entity CAS-9821 verified; no ERR- prefix)"
    gate2_passed: bool = True
    gate3_semantic_similarity: float = 1.0      # 0.0 to 1.0 from cpu_semantic_matcher
    gate3_method: str = "CPU_SEMANTIC_HYBRID"
    gate3_passed: bool = True
    gate4_llm_tiebreaker_used: bool = False
    gate4_verdict: Optional[str] = None
    final_status: Literal["PASS", "FAIL"] = "PASS"
    observed_summary: str = ""
    failure_reason: Optional[str] = None

class DirectStepInput(BaseModel):
    step_id: Optional[str] = None
    scenario: str
    procedure: str
    expected_result: str
    section: Optional[str] = "general"
    requires_screenshot: bool = True

class DirectProtocolAuthorRequest(BaseModel):
    protocol_type: Literal["OQ", "PQ", "OPS"] = "PQ"
    product_id: str = "onepv"
    system_name: str = "OnePV Safety System"
    document_no: str = "CLIN-EU-PAT-OPV-1-1-PQ-DIRECT"
    version: str = "1.0"
    title: str = "System-Authored Qualification Protocol"
    target_url: str = "https://mpv-two.vercel.app"
    steps: List[DirectStepInput]
```

Add these backward-compatible optional fields to existing classes in `backend/schemas.py`:
- In `CompiledControlLocator`:
  ```python
  provenance: ValueProvenance = "protocol_explicit"
  original_term: Optional[str] = None
  triggers_dom_mutation: bool = False
  ```
- In `PlannedFieldAction`:
  ```python
  provenance: ValueProvenance = "protocol_explicit"
  original_term: Optional[str] = None
  triggers_dom_mutation: bool = False
  ```
- In `ProtocolStep`:
  ```python
  cpu_parse_confidence: float = 1.0
  needs_mode1_discovery: bool = False
  applied_inputs: List[AppliedInputRecord] = Field(default_factory=list)
  gate_evaluation: Optional[GateEvaluationResult] = None
  screenshot_sha256: Optional[str] = None
  ```
- In `AuditLogEntry`:
  ```python
  screenshot_file: Optional[str] = None
  screenshot_sha256: Optional[str] = None
  locked_spec_sha256: Optional[str] = None
  inputs_applied: List[Dict[str, Any]] = Field(default_factory=list)
  gate_scores: Optional[Dict[str, Any]] = None
  ```
- In `ApproveReviewRequest`:
  ```python
  reviewer_username: Optional[str] = "qa.reviewer"
  ```
- In `SignatureRequest`:
  ```python
  justification: Optional[str] = None
  ```
- In `ProtocolSession`:
  ```python
  status: str = "READY"
  protocol_sha256: Optional[str] = None
  ```

---

### 2.2 Create `backend/cpu_semantic_matcher.py` (100% Offline-Safe CPU Semantic Engine)
Create `backend/cpu_semantic_matcher.py` using this complete, production-ready implementation that tries local cached `all-MiniLM-L6-v2` (`local_files_only=True` so it never hangs on a corporate firewall) and combines it with a deterministic domain-concept canonicalizer + character $n$-gram TF-IDF + sequence matcher:

```python
import re
import math
import difflib
from collections import Counter
from typing import List, Dict, Any, Optional, Tuple

_MINILM_MODEL = None
_MINILM_ATTEMPTED = False

def _get_local_minilm():
    """Loads all-MiniLM-L6-v2 from local disk cache ONLY (never hangs on network/VPN)."""
    global _MINILM_MODEL, _MINILM_ATTEMPTED
    if _MINILM_ATTEMPTED:
        return _MINILM_MODEL
    _MINILM_ATTEMPTED = True
    try:
        from sentence_transformers import SentenceTransformer
        _MINILM_MODEL = SentenceTransformer("all-MiniLM-L6-v2", device="cpu", local_files_only=True)
    except Exception:
        _MINILM_MODEL = None
    return _MINILM_MODEL

# Canonical equivalence clusters for GxP / Pharmacovigilance / Web UI validation
CONCEPT_CLUSTERS = [
    ("FUTURE_TIME", ["in the future", "future date", "later than current date", "after current date", "after today", "greater than today", "tomorrow", "future"]),
    ("PAST_TIME", ["in the past", "earlier than", "before today", "prior to", "yesterday"]),
    ("PROHIBITION", ["cannot", "must not", "shall not", "may not", "not allow", "block", "prevent", "restrict", "disallow", "prohibit", "rejected", "failed"]),
    ("ADMISSION_DATE", ["hospitalization admission date", "date of hospital admission", "hospital admission date", "admission date", "admit date"]),
    ("RECEIPT_DATE", ["company receipt date", "date of receipt", "receipt date", "received date"]),
    ("BIRTH_DATE", ["date of birth", "birth date", "dob", "patient dob"]),
    ("HCP_ROLE", ["health care professional", "healthcare professional", "physician", "medical doctor", "clinician", "hcp", "dr"]),
    ("CONSUMER_ROLE", ["consumer", "patient", "non-health care professional", "non-hcp", "lawyer"]),
    ("SERIOUS_YES", ["serious", "yes", "true", "y"]),
    ("SERIOUS_NO", ["non-serious", "not serious", "non_serious", "no", "false", "n"]),
    ("MANDATORY_REQ", ["mandatory", "required", "cannot be blank", "cannot be empty", "must be filled", "missing required"]),
    ("SUCCESS_CONFIRM", ["registered successfully", "created successfully", "saved successfully", "confirmation message", "successfully"]),
]

BOILERPLATE_PATTERNS = [
    r"\bsystem\s+shall\b", r"\bsystem\s+should\b", r"\bapplication\s+shall\b",
    r"\bverify\s+that\b", r"\bensure\s+that\b", r"\bshow\s+an?\s+error\s+alert\s+that\b",
    r"\bdisplay\s+an?\s+error\s+message\s+that\b", r"\bvalidation\s+failed\s*:\s*",
    r"\bvalidation\s+error\s*:\s*", r"\berror\s*:\s*", r"\bblock\s+registration\s+and\b",
    r"\bblock\s+save\s+and\b"
]

def normalize_and_canonicalize(text: str) -> Tuple[str, set]:
    """Strips GxP boilerplate and extracts canonical semantic concept tags."""
    low = (text or "").lower().strip()
    for pat in BOILERPLATE_PATTERNS:
        low = re.sub(pat, " ", low, flags=re.I)
    low = re.sub(r"[^a-z0-9\s]", " ", low)
    low = re.sub(r"\s+", " ", low).strip()

    active_concepts = set()
    canon_text = low
    for tag, phrases in CONCEPT_CLUSTERS:
        for ph in sorted(phrases, key=len, reverse=True):
            if re.search(rf"\b{re.escape(ph)}\b", canon_text):
                active_concepts.add(tag)
                canon_text = re.sub(rf"\b{re.escape(ph)}\b", f" {tag.lower()} ", canon_text)
    canon_text = re.sub(r"\s+", " ", canon_text).strip()
    return canon_text, active_concepts

def _char_ngram_cosine(a: str, b: str, n: int = 3) -> float:
    if not a or not b:
        return 0.0
    a_pad = f"  {a}  "
    b_pad = f"  {b}  "
    ca = Counter(a_pad[i:i+n] for i in range(max(1, len(a_pad) - n + 1)))
    cb = Counter(b_pad[i:i+n] for i in range(max(1, len(b_pad) - n + 1)))
    common = set(ca.keys()) & set(cb.keys())
    num = sum(ca[k] * cb[k] for k in common)
    den = math.sqrt(sum(v*v for v in ca.values())) * math.sqrt(sum(v*v for v in cb.values()))
    return (num / den) if den > 0 else 0.0

def _token_jaccard(a: str, b: str) -> float:
    stop = {"the", "a", "an", "to", "of", "in", "on", "for", "be", "is", "are", "was", "were", "by", "with", "as", "at"}
    ta = {t for t in a.split() if t not in stop and len(t) > 1}
    tb = {t for t in b.split() if t not in stop and len(t) > 1}
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)

def compute_assertion_similarity(expected_text: str, actual_observed_text: str) -> float:
    """
    Computes semantic similarity (0.0 to 1.0) between protocol Expected Result and Actual UI feedback.
    Runs in <8ms on CPU with 0 GPU load and 100% offline reliability.
    """
    if not expected_text or not actual_observed_text:
        return 0.0

    canon_exp, concepts_exp = normalize_and_canonicalize(expected_text)
    canon_act, concepts_act = normalize_and_canonicalize(actual_observed_text)

    # Disqualify if specific field/subject concepts conflict (e.g. ADMISSION_DATE expected, but not present and another field is)
    subject_tags = {"ADMISSION_DATE", "RECEIPT_DATE", "BIRTH_DATE", "HCP_ROLE", "CONSUMER_ROLE"}
    exp_subjects = concepts_exp & subject_tags
    act_subjects = concepts_act & subject_tags
    if exp_subjects and not (exp_subjects & act_subjects):
        # Check if raw head nouns from expected appear in actual
        raw_exp_tokens = {t for t in re.findall(r"[a-z]{4,}", expected_text.lower()) if t not in {"system", "shall", "should", "error", "alert", "message", "validation", "block", "registration", "cannot", "future", "mandatory", "required", "display", "show"}}
        raw_act_tokens = set(re.findall(r"[a-z]{4,}", actual_observed_text.lower()))
        if raw_exp_tokens and not (raw_exp_tokens & raw_act_tokens):
            return 0.20

    # Hybrid CPU score
    ngram_sim = _char_ngram_cosine(canon_exp, canon_act, n=3)
    jaccard_sim = _token_jaccard(canon_exp, canon_act)
    seq_sim = difflib.SequenceMatcher(None, canon_exp, canon_act).ratio()

    concept_Overlap = 0.0
    if concepts_exp and concepts_act:
        concept_Overlap = len(concepts_exp & concepts_act) / len(concepts_exp | concepts_act)

    hybrid_score = (0.35 * ngram_sim) + (0.30 * jaccard_sim) + (0.15 * seq_sim) + (0.20 * concept_Overlap)
    if concepts_exp and concepts_exp.issubset(concepts_act) and len(concepts_exp) >= 2:
        hybrid_score = max(hybrid_score, 0.86)

    # Optional boost/averaging with local MiniLM if cached on disk
    model = _get_local_minilm()
    if model is not None:
        try:
            emb = model.encode([canon_exp, canon_act], normalize_embeddings=True)
            minilm_sim = float(emb[0] @ emb[1])
            hybrid_score = max(hybrid_score, (0.6 * minilm_sim) + (0.4 * hybrid_score))
        except Exception:
            pass

    return round(min(1.0, max(0.0, hybrid_score)), 4)

def match_label_to_dom_candidates(
    target_label: str,
    candidates: List[Dict[str, Any]],
    threshold: float = 0.78
) -> Tuple[Optional[Dict[str, Any]], float]:
    """
    Matches a step field label (e.g. 'admission date') to live DOM control candidates
    (e.g. [{'id': '#adm_dt', 'label': 'Hospitalization Admission Date'}]).
    """
    if not target_label or not candidates:
        return None, 0.0

    tgt_clean = re.sub(r"[^a-z0-9\s]", " ", target_label.lower()).strip()
    tgt_canon, tgt_concepts = normalize_and_canonicalize(target_label)
    tgt_tokens = {t for t in tgt_clean.split() if len(t) > 1 and t not in {"code", "field", "input", "the", "for"}}

    best_cand = None
    best_score = 0.0

    for cand in candidates:
        c_label = str(cand.get("label") or cand.get("aria_label") or cand.get("placeholder") or cand.get("name") or cand.get("id") or "").strip()
        if not c_label:
            continue
        c_clean = re.sub(r"[^a-z0-9\s]", " ", c_label.lower()).strip()
        c_canon, c_concepts = normalize_and_canonicalize(c_label)
        c_tokens = {t for t in c_clean.split() if len(t) > 1 and t not in {"code", "field", "input", "the", "for"}}

        if c_clean == tgt_clean:
            return cand, 1.0

        score = 0.0
        if tgt_concepts and (tgt_concepts == c_concepts):
            score = 0.92
        elif tgt_tokens and c_tokens:
            overlap = len(tgt_tokens & c_tokens) / len(tgt_tokens)
            jaccard = len(tgt_tokens & c_tokens) / len(tgt_tokens | c_tokens)
            ngram = _char_ngram_cosine(c_canon, tgt_canon, n=3)
            score = (0.50 * overlap) + (0.25 * jaccard) + (0.25 * ngram)
            if tgt_clean in c_clean or c_clean in tgt_clean:
                score = max(score, 0.86)

        if score > best_score:
            best_score = score
            best_cand = cand

    if best_score >= threshold:
        return best_cand, round(best_score, 4)
    return None, round(best_score, 4)

def match_dropdown_option(
    target_value: str,
    options: List[Dict[str, str]],
    threshold: float = 0.78
) -> Tuple[Optional[Dict[str, str]], float, str]:
    """
    Matches a requested dropdown value (e.g. 'Physician') against live <select>/combobox options.
    Returns (matched_option_dict, confidence_score, provenance_tag).
    """
    if not target_value or not options:
        return None, 0.0, "protocol_explicit"

    tgt_clean = target_value.strip().lower().rstrip(".")
    _, tgt_concepts = normalize_and_canonicalize(target_value)

    # 1. Exact literal match
    for opt in options:
        opt_t = str(opt.get("text", "")).strip().lower().rstrip(".")
        opt_v = str(opt.get("val", opt.get("value", ""))).strip().lower().rstrip(".")
        if opt_t == tgt_clean or opt_v == tgt_clean:
            return opt, 1.0, "protocol_explicit"

    # 2. Concept cluster & semantic match (e.g. Physician -> HCP)
    best_opt = None
    best_score = 0.0
    for opt in options:
        opt_raw = str(opt.get("text") or opt.get("val") or "")
        opt_clean = opt_raw.strip().lower().rstrip(".")
        _, opt_concepts = normalize_and_canonicalize(opt_raw)

        score = 0.0
        if tgt_concepts and (tgt_concepts & opt_concepts):
            score = 0.90
        elif tgt_clean in opt_clean or opt_clean in tgt_clean:
            score = 0.85
        else:
            score = _char_ngram_cosine(tgt_clean, opt_clean, n=3)

        if score > best_score:
            best_score = score
            best_opt = opt

    if best_opt and best_score >= threshold:
        return best_opt, round(best_score, 4), "cpu_semantic_match"
    return None, round(best_score, 4), "protocol_explicit"
```

---

### 2.3 Create & Run Phase 1 Verification Harness (`backend/verify_phase1_v4.py`)
```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from schemas import AppliedInputRecord, GateEvaluationResult, DirectProtocolAuthorRequest, ProtocolStep
from cpu_semantic_matcher import (
    compute_assertion_similarity,
    match_label_to_dom_candidates,
    match_dropdown_option
)

def run_phase1_verification():
    print("=== PHASE 1 VERIFICATION: SCHEMAS & OFFLINE CPU SEMANTIC ENGINE ===")

    # 1. Paraphrased negative assertion match
    exp = "System should block registration and show an error alert that Admission Date cannot be in the future."
    act_valid = "Validation Failed: Date of Hospital Admission must not be later than current date."
    sim_valid = compute_assertion_similarity(exp, act_valid)
    print(f"[Check 1] Paraphrased Admission Date similarity: {sim_valid}")
    assert sim_valid >= 0.78, f"Expected >= 0.78, got {sim_valid}"

    # 2. Wrong field negative assertion rejection
    act_wrong = "Validation Error: Reporter Country is required."
    sim_wrong = compute_assertion_similarity(exp, act_wrong)
    print(f"[Check 2] Wrong field error similarity: {sim_wrong}")
    assert sim_wrong < 0.45, f"Expected < 0.45 for wrong field error, got {sim_wrong}"

    # 3. Label to DOM candidate matching
    dom_candidates = [
        {"id": "#rep_country", "label": "Reporter Country"},
        {"id": "#adm_date", "label": "Hospitalization Admission Date"},
        {"id": "#pat_init", "label": "Patient Initials"}
    ]
    matched_ctrl, score = match_label_to_dom_candidates("admission date", dom_candidates)
    print(f"[Check 3] Matched label 'admission date' -> {matched_ctrl} (score={score})")
    assert matched_ctrl and matched_ctrl["id"] == "#adm_date" and score >= 0.82

    # 4. Dropdown synonym matching (Physician -> HCP)
    opts = [{"text": "HCP", "val": "HCP"}, {"text": "Consumer", "val": "CON"}]
    matched_opt, opt_score, prov = match_dropdown_option("Physician", opts)
    print(f"[Check 4] Matched dropdown 'Physician' -> {matched_opt} (score={opt_score}, provenance={prov})")
    assert matched_opt and matched_opt["val"] == "HCP" and prov == "cpu_semantic_match"

    print("[PASS] PHASE 1 VERIFICATION COMPLETE!")

if __name__ == "__main__":
    run_phase1_verification()
```

---

## 3. PHASE 2: Dual Ingestion — In-System Direct Studio Authoring (Siva Sai's Flow) + `.docx` CPU Confidence Sieve

### 3.1 Upgrade `backend/extractor.py` with Prose Clause Extraction & CPU Confidence Sieve
In `backend/extractor.py`, add `extract_prose_fields_fallback()` and `score_step_parseability()` and call them inside `extract_protocol()` for every extracted `ProtocolStep`:

```python
def extract_prose_fields_fallback(step_id: str, primary_section: SectionType, procedure_text: str, existing_fields: List[ExtractedFieldSpec]) -> List[ExtractedFieldSpec]:
    """
    Catches natural-language prose instructions that do not use 'Label: Value' colons, e.g.:
    - "Pick 'Serious' for seriousness"
    - "choose 'Physician' as reporter type"
    - "Set admission date to a future date (tomorrow)"
    """
    existing_labels = {ef.label.lower() for ef in existing_fields}
    fields = list(existing_fields)
    counter = len(fields)

    # Pattern 1: pick/select/choose 'VAL' for/as/in LABEL
    for m in re.finditer(r"(?:pick|select|choose)\s+['\"]([^'\"]+)['\"]\s+(?:for|as|in)\s+([a-zA-Z0-9\s/_-]+?)(?:[\.,;—\-]|and\b|this\b|$)", procedure_text, re.I):
        val, lbl = m.group(1).strip(), m.group(2).strip().title()
        if lbl.lower() not in existing_labels and len(lbl) <= 35:
            counter += 1
            existing_labels.add(lbl.lower())
            fields.append(ExtractedFieldSpec(
                field_id=f"{step_id}-F{counter:02d}",
                section=primary_section,
                label=lbl,
                raw_instruction=f"(Prose select '{val}')",
                control_type="select",
                explicit_value=val
            ))

    # Pattern 2: set/enter LABEL to/as VALUE
    for m in re.finditer(r"(?:set|enter)\s+([a-zA-Z0-9\s/_-]+?)\s+to\s+(a future date(?:\s*\([^\)]+\))?|tomorrow|yesterday|today|['\"][^'\"]+['\"]|\d{4}-\d{2}-\d{2})", procedure_text, re.I):
        lbl, raw_val = m.group(1).strip().title(), m.group(2).strip().strip("'\"")
        if lbl.lower() not in existing_labels and len(lbl) <= 35:
            counter += 1
            existing_labels.add(lbl.lower())
            is_date = "date" in lbl.lower() or any(k in raw_val.lower() for k in ["future", "tomorrow", "yesterday", "today"])
            norm_val = "TODAY+1" if ("future" in raw_val.lower() or "tomorrow" in raw_val.lower()) else ("TODAY-1" if "yesterday" in raw_val.lower() else raw_val)
            fields.append(ExtractedFieldSpec(
                field_id=f"{step_id}-F{counter:02d}",
                section=primary_section,
                label=lbl,
                raw_instruction=f"(Prose set '{raw_val}')",
                control_type="date" if is_date else "text",
                explicit_value=norm_val
            ))

    return fields

def score_step_parseability(procedure_text: str, extracted_fields: List[ExtractedFieldSpec], action_intent: str) -> Tuple[float, bool]:
    """
    CPU Confidence Sieve:
    Returns (cpu_parse_confidence: float, needs_mode1_discovery: bool).
    Flags steps that contain dynamic DOM conditions, unstated mandatory fields, or unextracted prose verbs.
    """
    proc_l = (procedure_text or "").lower()
    dynamic_or_vague_markers = [
        "all other mandatory", "mandatory fields", "dummy data", "valid data",
        "opens the", "sub-section", "subsection", "if visible", "when prompted",
        "dynamically", "future date", "tomorrow"
    ]
    if any(m in proc_l for m in dynamic_or_vague_markers):
        return 0.45, True

    has_entry_verbs = any(v in proc_l for v in ["enter ", "fill ", "select ", "choose ", "pick ", "set "])
    if action_intent == "FORM_ENTRY" and has_entry_verbs and len(extracted_fields) == 0:
        return 0.30, True

    return 1.0, False
```
Wire both functions into `extract_protocol()` in `backend/extractor.py` right after `extracted_fields = extract_fields_from_procedure(...)`:
```python
extracted_fields = extract_prose_fields_fallback(step_id, primary_section, procedure_text, extracted_fields)
cpu_conf, needs_discovery = score_step_parseability(procedure_text, extracted_fields, action_intent)
```
and pass `cpu_parse_confidence=cpu_conf, needs_mode1_discovery=needs_discovery` when constructing `ProtocolStep`.

---

### 3.2 Add Direct In-System Session Builder in `backend/protocol_generator.py` & `backend/main.py`
1. In `backend/protocol_generator.py`, add `ProtocolGenerator.create_direct_session(req: DirectProtocolAuthorRequest) -> Tuple[ProtocolSession, str]`:
   - Builds a background `.docx` via `ProtocolGenerator._build_docx(...)` saved to `UPLOADS_DIR / f"{req.document_no} - Direct Studio Protocol.docx"` so `RightDocInspector` and `download_executed_docx` have a valid table coordinate map (`TableColumnMap(table_index=3, header_row_index=0, step_col=0, scenario_col=1, procedure_col=2, expected_col=3, pass_fail_col=4, initials_col=5, signoff_table_index=4)`).
   - Directly constructs `ProtocolStep` objects in memory from `req.steps` using `classify_action_intent`, `extract_fields_from_procedure`, `extract_prose_fields_fallback`, `score_step_parseability`, and `synthesize_step_assertions`—returning `(session, str(out_path))`.
2. In `backend/main.py`, add `POST /api/author-direct-session`:
   ```python
   @app.post("/api/author-direct-session")
   def author_direct_session(req: DirectProtocolAuthorRequest):
       session, docx_path = ProtocolGenerator.create_direct_session(req)
       sessions[session.session_id] = session
       session_file_paths[session.session_id] = docx_path
       AuditTrailManager.log_event(
           session_id=session.session_id,
           actor_username="system",
           actor_role="SYSTEM",
           event_type="PROTOCOL_UPLOADED",
           details=f"Direct In-System Protocol '{req.document_no}' authored in Studio ({len(session.steps)} steps, 0 .docx parsing overhead)"
       )
       planner = PlannerAgent(get_dom_map())
       plan_steps, md_plan, plan_latency = planner.generate_plan(session)
       session_plans[session.session_id] = plan_steps
       add_protocol_to_catalog(req.product_id, {
           "filename": session.filename,
           "document_no": session.document_no,
           "protocol_type": req.protocol_type,
           "size_kb": round(Path(docx_path).stat().st_size / 1024, 1),
           "step_count": len(session.steps),
           "updated_at": "Just now (Studio)",
           "product_id": req.product_id
       })
       return session.model_dump()
   ```
3. In `frontend/src/components/ProtocolAuthoringModal.tsx` and `frontend/src/App.tsx`:
   - Add an optional prop `onLoadDirectSession?: (sessionData: any) => void` to `ProtocolAuthoringModalProps`.
   - Add a top tab bar inside `ProtocolAuthoringModal.tsx` switching between:
     - **`"Direct Step Studio (Write In-System — 0 Doc Upload)"`**: Interactive table where the user can edit/add steps (`Scenario`, `Procedure`, `Expected Result`), pre-seeded with realistic editable rows, and a button **"Compile & Launch Directly in System"** that calls `POST /api/author-direct-session` and passes the returned `ProtocolSession` directly into `App.tsx` (which also fetches `/api/raw-protocol/${data.session_id}` for the right pane preview).
     - **`"AI Template Generator (FDS / URS)"`**: Existing template generator.

---

### 3.3 Create & Run Phase 2 Verification Harness (`backend/verify_phase2_v4.py`)
```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from schemas import DirectProtocolAuthorRequest, DirectStepInput
from protocol_generator import ProtocolGenerator

def run_phase2_verification():
    print("=== PHASE 2 VERIFICATION: DIRECT STUDIO AUTHORING & CPU CONFIDENCE SIEVE ===")
    req = DirectProtocolAuthorRequest(
        protocol_type="PQ",
        product_id="onepv",
        document_no="CLIN-PQ-STUDIO-001",
        title="Direct Studio Pharmacovigilance Qualification",
        steps=[
            DirectStepInput(
                step_id="TS1-S01",
                scenario="Register Adverse Event Case",
                procedure="In Manual Case Registration, under General Information, enter:\nCase Classifications Code: Adverse Event\nCase Intake Source Code: HCP\nCompany Receipt Date: 2023-10-15\nClick Save. (µ)",
                expected_result="System shall register case successfully with confirmation message and temporary case ID shall create."
            ),
            DirectStepInput(
                step_id="TS3-S07",
                scenario="Negative Future Hospitalization Admission Date",
                procedure="Navigate to Case Intake. Pick 'Serious' for seriousness—this opens the hospitalization sub-section. Set admission date to a future date (tomorrow), fill all other mandatory patient & reporter fields with valid dummy data, choose 'Physician' as reporter type, and try to Save. (µ)",
                expected_result="System should block registration and show an error alert that Admission Date cannot be in the future."
            )
        ]
    )
    session, docx_path = ProtocolGenerator.create_direct_session(req)
    assert len(session.steps) == 2
    s1, s2 = session.steps[0], session.steps[1]
    print(f"[Step 1] fields={len(s1.extracted_fields)}, conf={s1.cpu_parse_confidence}, discovery={s1.needs_mode1_discovery}")
    assert s1.cpu_parse_confidence >= 0.90 and not s1.needs_mode1_discovery

    print(f"[Step 2] fields={[(f.label, f.explicit_value) for f in s2.extracted_fields]}, conf={s2.cpu_parse_confidence}, discovery={s2.needs_mode1_discovery}")
    assert s2.needs_mode1_discovery is True
    extracted_map = {f.label.lower(): f.explicit_value for f in s2.extracted_fields}
    assert extracted_map.get("seriousness") == "Serious"
    assert extracted_map.get("reporter type") == "Physician"
    assert extracted_map.get("admission date") == "TODAY+1"
    print("[PASS] PHASE 2 VERIFICATION COMPLETE!")

if __name__ == "__main__":
    run_phase2_verification()
```

---

## 4. PHASE 3: Mode 1 — Guided Live-DOM Micro-Agent, Dynamic DOM Mutation Loop & Clean Planner (`backend/aria_compiler.py` & `backend/agents.py`)

### 4.1 Add `<400`-Token Live DOM Control Snapshotter & Mode 1 Binder in `backend/aria_compiler.py`
In `backend/aria_compiler.py`, add `extract_visible_dom_controls(page, container=None)` and `bind_step_with_live_dom(page, step, planned_step=None, container=None, llm_client=None)`:

1. **`extract_visible_dom_controls(page: Any, container: Optional[Any] = None) -> List[Dict[str, Any]]`:**
   Executes an in-browser JS query over `input, select, textarea, button, [role="combobox"], [role="switch"], [role="checkbox"]`, filtering out hidden/disabled elements (`rect.width === 0 || style.display === 'none' || style.visibility === 'hidden'`), resolving each control's associated `<label for="...">` or ancestor `<label>`, reading `required` (`el.required || el.getAttribute('aria-required') === 'true' || label.includes('*')`), and extracting `options` (`[{text, val}]`) for `<select>` elements.
2. **`resolve_dynamic_value(raw_val: Optional[str], control_type: str, label: str, options: List[Dict[str, str]]) -> Tuple[str, ValueProvenance, Optional[str]]`:**
   - Resolves `"TODAY"` $\rightarrow$ `datetime.date.today().isoformat()` (`provenance="computed_dynamic"`).
   - Resolves `"TODAY+1"` / `"tomorrow"` / `"future date"` $\rightarrow$ `(datetime.date.today() + datetime.timedelta(days=1)).isoformat()` (`provenance="computed_dynamic"`).
   - Resolves `"TODAY-1"` / `"yesterday"` $\rightarrow$ `(datetime.date.today() - datetime.timedelta(days=1)).isoformat()` (`provenance="computed_dynamic"`).
   - For `select` controls with `options`, uses `match_dropdown_option(raw_val, options)` from `cpu_semantic_matcher.py` to map synonyms like `"Physician"` $\rightarrow$ `"HCP"` (`provenance="cpu_semantic_match"`, `original_term="Physician"`).
3. **`bind_step_with_live_dom(...)` with Dynamic DOM Mutation Diff Loop:**
   - Captures `initial_controls = await extract_visible_dom_controls(page, container)`.
   - Matches all known `step.extracted_fields` (and `planned_step.field_actions`) against `initial_controls` using `match_label_to_dom_candidates()`.
   - Executes matched visible controls first (e.g., selecting `"Serious"` on `#seriousness`).
   - **DOM Mutation Check:** Waits `250ms` after any `<select>` or toggle interaction and calls `post_controls = await extract_visible_dom_controls(page, container)`.
   - Any control in `post_controls` that was not in `initial_controls` (such as `#adm_date` *"Hospitalization Admission Date"* revealed after selecting *"Serious"*) is immediately matched against remaining unmatched step fields!
   - **Mandatory Dummy Data Synthesis (`ai_synthesized_mandatory`):** If the step procedure instructs to fill mandatory fields (or if `step.needs_mode1_discovery` is True on a positive/conditional form fill), inspects all visible `required: True` controls that have not yet been filled and synthesizes valid type-appropriate clinical values (calling `QwenLLMClient` with a $\le 500$-token JSON prompt if configured, or deterministic schema-aware synthesis by control type/label if offline), tagging every synthesized field with `provenance="ai_synthesized_mandatory"`.
   - Updates the step's `LockedStepSpec` inside `PlanCacheManager` so future runs execute deterministically with `0` discovery overhead.

### 4.2 Clean Up `backend/agents.py` (Delete Hardcoded OnePV Dictionary)
In `backend/agents.py`:
- Replace the 200-line hardcoded OnePV `if/elif` block in `synthesize_fallback_field_action()` (`lines 351-530`) with a clean, universal, type-and-pattern-based synthesizer that tags `provenance` accurately (`"protocol_explicit"` when `ef.explicit_value` is present, `"computed_dynamic"` for relative dates, and `"ai_synthesized_mandatory"` when synthesized).

---

### 4.3 Create & Run Phase 3 Verification Harness (`backend/verify_phase3_v4.py`)
Create `backend/verify_phase3_v4.py` spinning up a real headless Chromium page via `async_playwright()` with an HTML form where:
- Selecting `"Serious"` in `<select id="seriousness">` triggers an `onchange` handler that unhides `<div id="hosp_box" style="display:none"><label for="adm_date">Hospitalization Admission Date *</label><input id="adm_date" type="date" required></div>`.
- The form also contains `<label for="pat_init">Patient Initials *</label><input id="pat_init" type="text" required>` and `<label for="rep_type">Reporter Type *</label><select id="rep_type" required><option value="">Select</option><option value="HCP">HCP</option><option value="CON">Consumer</option></select>`.
- Assert that running `bind_step_with_live_dom()` on step `TS3-S07` (*"Pick 'Serious' for seriousness—this opens the hospitalization sub-section. Set admission date to a future date (tomorrow), fill all other mandatory patient & reporter fields with valid dummy data, choose 'Physician' as reporter type"*):
  1. Selects `"Serious"` in `#seriousness` (`provenance == "protocol_explicit"`),
  2. Automatically reveals `#hosp_box` and fills tomorrow's ISO date into `#adm_date` (`provenance == "computed_dynamic"`),
  3. Maps `"Physician"` $\rightarrow$ `"HCP"` in `#rep_type` (`provenance in ["cpu_semantic_match", "ai_mapped_synonym"]`, `original_term == "Physician"`),
  4. Synthesizes non-empty dummy data for mandatory `#pat_init` (`provenance == "ai_synthesized_mandatory"`),
  5. Verifies via DOM `.input_value()` that all 4 controls on the live page hold those exact values!

---

## 5. PHASE 4: Mode 2 — 4-Gate Zero-False-Positive Verification Engine (`backend/verification_engine.py` & `backend/playwright_runner.py`)

### 5.1 Create `backend/verification_engine.py`
Create `backend/verification_engine.py` implementing `evaluate_step_gates(...) -> GateEvaluationResult`:

```python
import re
from typing import List, Optional, Tuple
from schemas import ProtocolStep, StepAssertion, GateEvaluationResult
from cpu_semantic_matcher import compute_assertion_similarity

FORBIDDEN_ENTITY_PREFIXES = ("ERR-", "ERROR-", "FAIL-", "HTTP-", "CODE-", "STATUS-", "WARN-", "INVALID-")

def extract_valid_entity_id(text: str) -> Optional[str]:
    """
    Strictly extracts a created GxP entity ID (e.g. CASE-2026-0042, TMP-CASE-9821, OPV-2026-001, CAS-9821)
    while rejecting error codes like ERR-502 or HTTP-400.
    """
    if not text:
        return None
    # Priority 1: Explicit labeled ID
    for m in re.finditer(r"(?:case\s*(?:id|number|no|#)\s*[:=]?\s*|temporary\s*case\s*(?:id|number|#)?\s*[:=]?\s*|id\s*[:=]\s*)([A-Z]{2,10}-[A-Z0-9\-]{2,20})\b", text, re.I):
        cand = m.group(1).upper()
        if not cand.startswith(FORBIDDEN_ENTITY_PREFIXES):
            return cand
    # Priority 2: Standard entity token
    for m in re.finditer(r"\b(CASE-[0-9A-Z\-]+|OPV-[0-9]{4}-[0-9]+|TMP-[A-Z0-9\-]+|CAS-[0-9]+)\b", text):
        cand = m.group(1).upper()
        if not cand.startswith(FORBIDDEN_ENTITY_PREFIXES):
            return cand
    return None
```

Enforce all **4 Gates** inside `evaluate_step_gates()`:
1. **Gate 1 (Polarity, Network & Execution Guard):**
   - On **Positive Steps (`is_negative == False`)**: If `execution_failures` is non-empty, OR `failed_http_responses` is non-empty, OR any visible UI error/invalid state is present, OR `combined_feedback` contains negative failure phrases (`"error:"`, `"failed to"`, `"validation error"`, `"validation failed"`, `"cannot "`, `"unable to"`, `"err-"`), immediately fail Gate 1 (`gate1_passed = False`, `final_status = "FAIL"`).
   - On **Negative Steps (`is_negative == True`)**: If the step expects blocked registration/submission (`"block"`, `"shall not allow"`, `"cannot"`, `"prevent"`, `"error"`) AND the application instead displayed a positive creation confirmation (`"registered successfully"`, `"saved successfully"`, or generated a valid `CASE-`/`TMP-`/`CAS-` ID without an error alert), immediately fail Gate 1 (`"Defect Detected: System allowed invalid submission on negative test"`).
2. **Gate 2 (Entity ID & Target Field Guard):**
   - For `ENTITY_CREATED`: Call `extract_valid_entity_id(combined_feedback + " " + body_text)`. If `None`, **`gate2_passed = False`** (`"Missing expected created entity ID"`). Never pass `ENTITY_CREATED` merely because `combined_feedback` is non-empty!
   - For `MESSAGE_DISPLAYED`: Require non-empty positive confirmation feedback (`combined_feedback`) when the expected result specifies a confirmation message/popup.
   - For `ERROR_MESSAGE` (Negative Validation): Require an active error message (`error_content`). Furthermore, if `step.expected_result` specifies a particular field or condition (e.g., `"Admission Date"`, `"future"`), check `compute_assertion_similarity(step.expected_result, error_content)`—if similarity is $< 0.55$, fail Gate 2 (`f"Wrong Validation Error Triggered: Expected '{step.expected_result[:60]}', but observed '{error_content[:80]}'"`).
3. **Gate 3 (Offline CPU Semantic Similarity Check):**
   - Compute `sim = compute_assertion_similarity(step.expected_result, combined_feedback or observed_text)`.
   - Record `gate3_semantic_similarity = sim`. For specific prose message assertions, require `sim >= 0.70` (or Gate 4 tie-breaker if `0.55 <= sim < 0.70`).
4. **Gate 4 (Grey-Zone Qwen Tie-Breaker):**
   - Only invoked if Gates 1 & 2 passed and `0.55 <= sim < 0.70` and `QwenLLMClient` is online.

### 5.2 Wire `verification_engine.py` & DOM Readback into `backend/playwright_runner.py`
1. In `backend/playwright_runner.py`, update `human_fill()` and `safe_select_option()` to verify live DOM readback (`await loc.input_value()` or selected option text) and append an `AppliedInputRecord` to `step.applied_inputs`.
2. In `verify_expected_result()` (`playwright_runner.py:722`), call `evaluate_step_gates()` from `verification_engine.py`, store `step.gate_evaluation = gate_res`, and fix the buggy `ENTITY_CREATED`, `ERROR_MESSAGE`, and `MESSAGE_DISPLAYED` branches so all 5 false-positive traps are blocked.

---

### 5.3 Create & Run Phase 4 Verification Harness (`backend/verify_phase4_v4.py`)
Test all 5 false-positive traps in `backend/verify_phase4_v4.py`:
1. **Trap 1:** Positive `ENTITY_CREATED` + `MESSAGE_DISPLAYED` with `"Error: Failed to create case successfully. Code: ERR-502"` $\rightarrow$ asserts `is_passed is False`.
2. **Trap 2:** Positive `ENTITY_CREATED` with `"Form saved."` (no Case ID generated) $\rightarrow$ asserts `is_passed is False`.
3. **Trap 3:** Negative `ERROR_MESSAGE` expecting `"System should block registration and show an error alert that Admission Date cannot be in the future"` when UI shows `"Validation Error: Reporter Country is required"` $\rightarrow$ asserts `is_passed is False`.
4. **Trap 4:** Negative `ERROR_MESSAGE` expecting `"System should block registration and show an error alert that Admission Date cannot be in the future"` when UI shows `"Validation Failed: Date of Hospital Admission must not be later than current date."` $\rightarrow$ asserts `is_passed is True` with `0` LLM calls.
5. **Trap 5:** Negative step expecting blocked registration when UI accidentally saves and shows `"Case registered successfully. Temporary Case ID: TMP-CASE-9912"` $\rightarrow$ asserts `is_passed is False`.

---

## 6. PHASE 5: FDA 21 CFR Part 11 Cryptographic Image-Bound Audit Trail (`backend/audit_trail.py`)

### 6.1 Upgrade `backend/audit_trail.py`
Upgrade `AuditTrailManager.log_event()` and `AuditTrailManager.verify_audit_trail()`:
1. Add optional kwargs to `log_event()`:
   ```python
   screenshot_path: Optional[str] = None,
   locked_spec_sha256: Optional[str] = None,
   inputs_applied: Optional[List[Dict[str, Any]]] = None,
   gate_scores: Optional[Dict[str, Any]] = None
   ```
2. When `screenshot_path` is provided and exists on disk:
   - Compute `screenshot_sha256 = hashlib.sha256(Path(screenshot_path).read_bytes()).hexdigest()`.
   - Store `screenshot_file = str(Path(screenshot_path).resolve())`.
3. Include canonical JSON of `screenshot_sha256`, `locked_spec_sha256`, `inputs_applied`, and `gate_scores` in the SHA-256 `payload` formula:
   ```python
   inputs_json = json.dumps(inputs_applied or [], sort_keys=True)
   gates_json = json.dumps(gate_scores or {}, sort_keys=True)
   payload = (
       f"{sequence_no}|{now_utc}|{session_id}|{actor_username}|{event_type}|"
       f"{details}|{screenshot_sha256 or ''}|{locked_spec_sha256 or ''}|"
       f"{inputs_json}|{gates_json}|{prev_hash}"
   )
   ```
4. In `verify_audit_trail(session_id: str)`:
   - Recompute the exact `payload` hash for every line.
   - If an entry has `screenshot_file` and `screenshot_sha256` and `Path(screenshot_file).exists()`, recompute `actual_img_sha = hashlib.sha256(Path(screenshot_file).read_bytes()).hexdigest()`. If `actual_img_sha != entry["screenshot_sha256"]`, immediately return `(False, f"Line {line_idx}: Screenshot image tampering detected on '{Path(screenshot_file).name}' (expected SHA-256 {entry['screenshot_sha256'][:12]}..., got {actual_img_sha[:12]}...)")`.
5. In `backend/playwright_runner.py` (where `STEP_PASSED` / `STEP_FAILED` are logged to `AuditTrailManager.log_event`), pass `screenshot_path=step.combined_screenshot_path`, `locked_spec_sha256=session.plan_locked_sha256`, `inputs_applied=[i.model_dump() for i in step.applied_inputs]`, and `gate_scores=step.gate_evaluation.model_dump() if step.gate_evaluation else None`.

---

### 6.2 Create & Run Phase 5 Verification Harness (`backend/verify_phase5_v4.py`)
Verify in `backend/verify_phase5_v4.py`:
1. Logging a step with a real `.png` screenshot file, `inputs_applied` provenance list, and `gate_scores` dict produces a valid chain (`verify_audit_trail() == (True, None)`).
2. Modifying 1 byte of the `.png` file on disk without editing `audit_trail.jsonl` causes `verify_audit_trail()` to return `(False, ...)` citing `"Screenshot image tampering detected"`.
3. Modifying 1 character of `inputs_applied` in `audit_trail.jsonl` causes `verify_audit_trail()` to return `(False, ...)` citing `"Tampering detected: entry_hash mismatch"`.

---

## 7. PHASE 6: Full VSR + RCA + Provenance Dossier & Standalone `Audit_Trail_Certificate.docx` (`backend/docx_writer.py`, `backend/main.py`, `frontend/`)

### 7.1 Upgrade `backend/docx_writer.py`
1. **In `DocxWriter.populate_executed_docx()`:**
   - If `step.applied_inputs` contains any entry with `provenance != "protocol_explicit"`, append a concise provenance disclosure to the `Observed Result` text stamped into the Word table:
     ```python
     non_explicit = [
         f"{inp.field_label}='{inp.value_applied}' ({inp.provenance.replace('_', ' ')}"
         + (f" from '{inp.original_term}'" if inp.original_term else "") + ")"
         for inp in (step.applied_inputs or [])
         if inp.provenance != "protocol_explicit"
     ]
     ```
2. **In `DocxWriter.generate_companion_evidence_docx()`:**
   Upgrade the Evidence Dossier so it includes:
   - **Section 1: Validation Summary Report (VSR) & Qualification Verdict** (Total Steps, Passed, Failed, Blocked, Pass Rate %, Locked Plan SHA-256, and Executive Summary).
   - **Section 2: ALCOA+ Input Data Provenance & Synonym Mapping Matrix** (Table listing Step ID, Field Label, Applied Value, Provenance Source, and DOM Readback Verified status).
   - **Section 3: Deviation Registry & AI Root Cause Analysis (RCA) Table** (For any failed/blocked steps, or a `"Zero Deviations Recorded"` confirmation block when all pass).
   - **Section 4: Stamped Visual Evidence & Cryptographic Image Hashes** (Each step's stitched screenshot + `screenshot_sha256` + 4-Gate evaluation summary).
3. **Add `DocxWriter.generate_audit_trail_certificate_docx(session: ProtocolSession, output_filename: Optional[str] = None) -> str`:**
   - Generates a presentable, FDA-inspector-ready **`Audit_Trail_Certificate_{clean_name}.docx`**.
   - **Section 1 (Cryptographic Integrity Verification Banner):** Displays Session ID, Protocol Document No, Chain Verification Verdict (`VERIFIED INTACT — 0 TAMPER EVENTS` vs `TAMPER ALERT`), Total Logged Events, Genesis Hash (`0000...`), and Final Sealed Root Hash.
   - **Section 2 (21 CFR Part 11 Hash-Chained Event Table):** A clean 6-column grid (`Seq #`, `Timestamp (UTC)`, `Actor & Role`, `Event & Step ID`, `Details & Provenance`, `Evidence SHA-256 & Entry Hash`).
   - **Section 3 (Electronic Signature Registry):** Lists all applied `ElectronicSignatureRecord` items (`TEST_EXECUTOR`, `QA_REVIEWER`) or states `"Awaiting QA Reviewer Electronic Signature"`.

### 7.2 Add Audit Certificate Download Endpoint (`backend/main.py` & `frontend/src/components/ExecutionSummaryModal.tsx`)
1. In `backend/main.py`, add:
   ```python
   @app.get("/api/download-audit-certificate/{session_id}")
   def download_audit_certificate(session_id: str):
       if session_id not in sessions:
           raise HTTPException(status_code=404, detail="Session not found")
       session = sessions[session_id]
       cert_docx = DocxWriter.generate_audit_trail_certificate_docx(session=session)
       clean_name = session.filename[:-5] if session.filename.endswith(".docx") else session.filename
       return FileResponse(
           cert_docx,
           media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
           filename=f"Audit_Trail_Certificate_{clean_name}.docx"
       )
   ```
   Also include `Audit_Trail_Certificate` in `archive_session()` (`main.py:638`) so `manifest.sha256` seals all 3 Word deliverables.
2. In `frontend/src/components/ExecutionSummaryModal.tsx`, add a **"Download Audit Certificate (.docx)"** button (`window.location.href = `/api/download-audit-certificate/${summary.session_id}``) in the modal footer right alongside **"Download Protocol (.docx)"** and **"Download Evidence Dossier (.docx)"**.

---

### 7.3 Create & Run Phase 6 Master End-to-End Verification Harness (`backend/verify_phase6_v4.py`)
Create and run `backend/verify_phase6_v4.py` asserting:
1. Full end-to-end creation and simulated execution of a `ProtocolSession` containing both `TS1-S04` (positive step) and `TS3-S07` (messy conditional negative step with `ai_synthesized_mandatory`, `cpu_semantic_match`, and `computed_dynamic` inputs).
2. `DocxWriter.populate_executed_docx()` stamps the provenance disclosure into the `Observed Result` cell and leaves `Reviewed By` blank prior to QA signature.
3. `DocxWriter.generate_companion_evidence_docx()` generates the 4-section VSR + Provenance + RCA + Evidence Dossier `.docx`.
4. `DocxWriter.generate_audit_trail_certificate_docx()` generates the human-readable `Audit_Trail_Certificate.docx` containing the verified root hash and all chained events.
5. All 6 phase verification scripts (`verify_phase1_v4.py` .. `verify_phase6_v4.py`) and `verify_v3_architecture.py` pass 100%.

---

## 8. Copy-Paste Prompts for Your AI IDE (Phase by Phase)

Use these exact prompts one at a time in Cursor, Windsurf, Claude Code, or Cline:

- **Phase 1 Kickoff Prompt:**
  > Read `AGENTS.md` and Section 2 (**PHASE 1**) of `ai_ide_implementation_plan_testvalid_v4.md`. Implement Phase 1 ONLY (`backend/schemas.py`, `backend/cpu_semantic_matcher.py`, and `backend/verify_phase1_v4.py`). Run `PYTHONPATH=backend python backend/verify_phase1_v4.py` and `PYTHONPATH=backend python backend/verify_v3_architecture.py`, paste the output, and wait for my approval.

- **Phase 2 Kickoff Prompt:**
  > Phase 1 is approved. Read Section 3 (**PHASE 2**) of `ai_ide_implementation_plan_testvalid_v4.md`. Implement Phase 2 ONLY (`backend/extractor.py`, `backend/protocol_generator.py`, `backend/main.py`, `frontend/src/components/ProtocolAuthoringModal.tsx`, `frontend/src/App.tsx`, and `backend/verify_phase2_v4.py`). Run `PYTHONPATH=backend python backend/verify_phase2_v4.py` and `PYTHONPATH=backend python backend/verify_v3_architecture.py`, paste the output, and wait for my approval.

- **Phase 3 Kickoff Prompt:**
  > Phase 2 is approved. Read Section 4 (**PHASE 3**) of `ai_ide_implementation_plan_testvalid_v4.md`. Implement Phase 3 ONLY (`backend/aria_compiler.py`, `backend/agents.py`, and `backend/verify_phase3_v4.py`). Rip out the hardcoded OnePV field dictionary in `agents.py` and replace it with the clean v4 synthesizer and live-DOM micro-agent. Run `PYTHONPATH=backend python backend/verify_phase3_v4.py` and `PYTHONPATH=backend python backend/verify_v3_architecture.py`, paste the output, and wait for my approval.

- **Phase 4 Kickoff Prompt:**
  > Phase 3 is approved. Read Section 5 (**PHASE 4**) of `ai_ide_implementation_plan_testvalid_v4.md`. Implement Phase 4 ONLY (`backend/verification_engine.py`, `backend/playwright_runner.py`, and `backend/verify_phase4_v4.py`). Run `PYTHONPATH=backend python backend/verify_phase4_v4.py` and `PYTHONPATH=backend python backend/verify_v3_architecture.py`, paste the output, and wait for my approval.

- **Phase 5 Kickoff Prompt:**
  > Phase 4 is approved. Read Section 6 (**PHASE 5**) of `ai_ide_implementation_plan_testvalid_v4.md`. Implement Phase 5 ONLY (`backend/audit_trail.py`, `backend/playwright_runner.py` audit logging call, and `backend/verify_phase5_v4.py`). Run `PYTHONPATH=backend python backend/verify_phase5_v4.py` and `PYTHONPATH=backend python backend/verify_v3_architecture.py`, paste the output, and wait for my approval.

- **Phase 6 Kickoff Prompt:**
  > Phase 5 is approved. Read Section 7 (**PHASE 6**) of `ai_ide_implementation_plan_testvalid_v4.md`. Implement Phase 6 ONLY (`backend/docx_writer.py`, `backend/main.py`, `frontend/src/components/ExecutionSummaryModal.tsx`, and `backend/verify_phase6_v4.py`). Run all verification scripts (`verify_phase1_v4.py` through `verify_phase6_v4.py` and `verify_v3_architecture.py`) and show me the final results.
