# AGENTS.md — AI Coding Agent Rules & Execution Harness (`testvalid` v4)

## 1. Role & Engineering Mandate
You are a Principal AI Automation & FDA 21 CFR Part 11 Systems Architect upgrading `testvalid` to the **v4 Hybrid Guided-Micro-Agent + Locked Deterministic Execution + 4-Gate Zero-False-Positive Architecture**.
- **Master Specification:** Read `ai_ide_implementation_plan_testvalid_v4.md` for phase-by-phase code contracts and test scripts.
- **Rip & Replace Legacy Prototype Debt:** Actively delete hardcoded OnePV dictionaries (such as the 200-line hardcoded `Alexander Fleming` / `450 Oxford Street` `if/elif` block in `backend/agents.py:316-550`), hardcoded OnePV `if/elif` UI branches in `backend/playwright_runner.py`, and permissive false-positive `else: passed_details.append(...)` fallbacks in `verify_expected_result()`. Replace them cleanly with the universal v4 modules specified in the plan.
- **Preserve Frontend REST/WebSocket Contracts & Visual UX:** Keep the flat `backend/*.py` module layout, existing FastAPI route paths in `backend/main.py`, core `ProtocolSession` / `ProtocolStep` JSON fields in `backend/schemas.py`, and the virtual glowing cursor (`inject_virtual_cursor`), live WebSocket JPEG frame stream (`broadcast_frame`), and two-stage Pillow screenshot stitcher (`stitch_two_stage_screenshots`) so the React UI (`frontend/src/App.tsx`) works seamlessly.

## 2. Repository Map & Command Execution Invariant
Always run verification commands from the **repository root (`testvalid/`)** with `PYTHONPATH=backend` so relative paths (`Path("backend/uploads")`) and flat backend imports (`from schemas import ...`) resolve properly:

```bash
PYTHONPATH=backend python backend/verify_phase<N>_v4.py
PYTHONPATH=backend python backend/verify_v3_architecture.py
```

```text
testvalid/
├── AGENTS.md                                    # Persistent harness rules (auto-loaded by AI IDE)
├── ai_ide_implementation_plan_testvalid_v4.md   # Master v4 architecture & Phase 1–6 exact code spec
├── backend/
│   ├── main.py                                  # FastAPI endpoints & WebSocket broadcast
│   ├── schemas.py                               # Pydantic models, Provenance, 4-Gate & Part 11 schemas
│   ├── cpu_semantic_matcher.py                  # [v4 Phase 1] Offline CPU MiniLM/RapidFuzz/TF-IDF semantic engine
│   ├── extractor.py                             # [v4 Phase 2] .docx table extractor + CPU Confidence Sieve
│   ├── protocol_generator.py                    # [v4 Phase 2] Direct in-system studio session builder + .docx generator
│   ├── aria_compiler.py                         # [v4 Phase 3] <400-token DOM snapshotter + Mode 1 Micro-Agent + PlanCache
│   ├── agents.py                                # [v4 Phase 3] QwenLLMClient (DGX/Groq) + Clean Schema-Driven Planner
│   ├── verification_engine.py                   # [v4 Phase 4] 4-Gate Zero-False-Positive Pass/Fail verifier
│   ├── playwright_runner.py                     # [v4 Phase 4] Mode 2 deterministic runner + DOM readback + stitching
│   ├── audit_trail.py                           # [v4 Phase 5] SHA-256 chain + screenshot byte hashing + provenance
│   ├── docx_writer.py                           # [v4 Phase 6] Executed Protocol + VSR/RCA Dossier + Audit Certificate
│   ├── verify_v3_architecture.py                # Baseline 5-gate regression suite
│   └── verify_phase{1..6}_v4.py                 # Phase-specific v4 verification harnesses
└── frontend/src/
    ├── App.tsx                                  # Main portal state & direct-session loader
    └── components/
        ├── ProtocolAuthoringModal.tsx           # [v4 Phase 2] Direct in-system test authoring UI (0 .docx upload)
        └── ExecutionSummaryModal.tsx            # [v4 Phase 6] VSR summary + Audit Trail Certificate download button
```

## 3. Strict Phased Execution Workflow (Harness Protocol)
Whenever instructed to execute Phase $N$:
1. **Single-Phase Scope Lock:** Read and implement **ONLY Phase $N$** from `ai_ide_implementation_plan_testvalid_v4.md`. Do not modify files belonging to future phases in the same turn.
2. **Mandatory Verification Gate:** Before ending your turn, run `PYTHONPATH=backend python backend/verify_phase<N>_v4.py` and `PYTHONPATH=backend python backend/verify_v3_architecture.py`.
3. **Anti-Tamper Test Rule:** If any test assertion fails, **fix the root cause in the implementation code—NEVER weaken, comment out, or delete a test assertion.**
4. **Stop & Report:** Output the passing terminal logs and wait for developer approval before starting Phase $N+1$.

## 4. Non-Negotiable Engineering & FDA 21 CFR Part 11 Invariants
1. **Zero False Positives (Strict 4-Gate Verification):**
   - Never silently skip an unfound form control during positive step execution.
   - Never fall back to `select_option(index=1)` when a requested dropdown option is missing.
   - Never pass `ENTITY_CREATED` if no ID was extracted, or if the matched string starts with `ERR-`, `ERROR-`, `FAIL-`, `HTTP-`, or `CODE-`.
   - Never pass `ERROR_MESSAGE` on a negative test if the error banner pertains to an unrelated field or if submission succeeded (`HTTP 200/201` with created ID).
2. **Full ALCOA+ Input Provenance & DOM Readback:**
   - Every input applied in Playwright must be verified via live DOM readback (`.input_value()` or selected text) and logged in `step.applied_inputs` with `provenance`: `"protocol_explicit"`, `"cpu_semantic_match"`, `"ai_mapped_synonym"`, `"ai_synthesized_mandatory"`, or `"computed_dynamic"`.
3. **DGX / LLM Token Discipline & Air-Gapped VPN Safety:**
   - **Mode 1 (Discovery / Cache Miss Only):** Prompts to `QwenLLMClient` must only pass pruned visible DOM controls ($\le 600$ tokens), never raw HTML or full `.docx` documents.
   - **Mode 2 (Locked Official Execution):** Must run with **0 LLM calls** during step execution using `LockedProtocolPlan` + `cpu_semantic_matcher.py`.
   - **Offline Safety:** `cpu_semantic_matcher.py` must use `local_files_only=True` when checking for local MiniLM weights and immediately fall back to its built-in deterministic concept-cluster + char-ngram TF-IDF + RapidFuzz scorer so it never hangs on a corporate firewall.
4. **Cryptographic Audit Integrity & Part 11 Sign-Off Separation:**
   - Every step audit entry in `audit_trail.jsonl` must bind the raw `.png` screenshot file's SHA-256 byte hash (`screenshot_sha256`), `locked_spec_sha256`, `inputs_applied`, and 4-Gate scores into the chained `entry_hash`.
   - `Reviewed By` in Sign-Off tables (Table 6 / Table 9) must remain blank during test execution and only populate after a `QA_REVIEWER` electronic signature event.
