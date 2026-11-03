# AGENTS.md — Strict Anti-Shortcut AI IDE Harness (`testvalid` v4.1)

## 1. Hard Prohibitions Against Lazy AI Shortcuts (READ EVERY TURN)
You are running on a fast coding model (3.8 Flash). You have a tendency to take lazy shortcuts unless strictly constrained. **You MUST obey these 5 rules on every single turn:**
1. **NO REGEX-ONLY EXTRACTION:** Never rely solely on `extractor.py` regexes to understand test steps. `PlannerAgent.query_qwen_single_batch()` MUST always receive the raw `procedure` and `expected_result` prose of every step so the LLM extracts fields and intents even when `extractor.py` extracts `0` fields.
2. **NO UNCALLED DEAD FUNCTIONS:** Never create a helper function (like `extract_visible_dom_controls`, `bind_step_with_live_dom`, or `match_dropdown_option`) without wiring it into the active runtime execution path in `playwright_runner.py` and `agents.py`.
3. **NO STALE OFFLINE CACHE:** After Cold-Start execution (`PlaywrightRunner.run_protocol`), you MUST write the actual live-DOM-verified selectors and dropdown option texts (`step.applied_inputs`) back into `PlanCacheManager` (`update_cache_with_verified_dom_inputs`) so Warm-Start runs use the real website's vocabulary (e.g. `'Physician'`, `'United States'`).
4. **NO FAKE PASS FALLBACKS:** Never use `else: passed_details.append(...)`, never select `index=1` when an explicit protocol option (`ef.explicit_value is not None`) is missing, and never weaken a test assertion in `verify_*.py` to make a failing test pass.
5. **FLAT MODULE LAYOUT & REPO-ROOT EXECUTION:** Keep all backend Python files directly inside `backend/*.py` (never move them into subdirectories). Always run verification commands from the repository root (`testvalid/`):
   ```bash
   PYTHONPATH=backend python backend/verify_no_shortcuts_v4.py
   PYTHONPATH=backend python backend/verify_v3_architecture.py
   ```

## 2. Active Architecture Invariants
- **Stage 1 & 2 (Hybrid Prose + Regex Ingestion):** `extractor.py` extracts table coordinates (`TableColumnMap`) and explicit `Label: Value` candidates; `PlannerAgent` sends all step `procedure` + `expected_result` text in **1 batched JSON call** to `QwenLLMClient` (`temperature=0.0`, `json_mode=True`) and merges LLM-discovered fields with regex fields.
- **Stage 3 (Live-DOM Binding & Cache Write-Back):** `playwright_runner.py` calls `match_dropdown_option()` from `cpu_semantic_matcher.py` inside `safe_select_option()`, calls `bind_step_with_live_dom()` when a step has `needs_mode1_discovery=True` or unmapped fields, verifies pre-save `FIELD_VALUE` auto-population before clicking `Save`, and updates `LockedProtocolPlan` on disk after execution.
- **Stage 4 (4-Gate Zero-False-Positive Verifier):** Every step is verified by `verification_engine.py` (Gate 1: HTTP/Polarity, Gate 2: Entity ID/Target Field Guard, Gate 3: Offline CPU Semantic Similarity, Gate 4: Grey-Zone Qwen Tie-Breaker).
- **Stage 5 & 6 (21 CFR Part 11 Cryptographic Audit & 3 Deliverables):** `audit_trail.py` binds raw `.png` screenshot SHA-256 bytes (`screenshot_sha256`), `inputs_applied` provenance, and 4-Gate scores into `entry_hash`. `main.py` caches `session_summary_cache` so post-run reporting makes at most 1 LLM call.
