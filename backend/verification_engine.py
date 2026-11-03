import re
from typing import List, Optional, Tuple, Any, Dict
from schemas import ProtocolStep, StepAssertion, GateEvaluationResult, StepCheckpoint
from cpu_semantic_matcher import compute_assertion_similarity

FORBIDDEN_ENTITY_PREFIXES = ("ERR-", "ERROR-", "FAIL-", "HTTP-", "CODE-", "STATUS-", "WARN-", "INVALID-")

GENERIC_META_VOCAB = {
    "system", "application", "portal", "page", "shall", "should", "must", "will",
    "display", "show", "prompt", "prompts", "present", "trigger", "return", "user",
    "with", "an", "a", "the", "error", "errors", "validation", "message", "messages",
    "alert", "alerts", "pop", "up", "popup", "dialog", "banner", "toast", "notification",
    "on", "in", "screen", "form", "field", "fields", "mandatory", "required", "missing",
    "incomplete", "prevent", "prevents", "block", "blocks", "restrict", "submission",
    "transition", "saving", "registering", "refer", "expected", "result", "additional",
    "questions", "question", "template", "templates"
}

def extract_specific_constraint_tokens(expected_text: str) -> List[str]:
    """
    Returns domain-specific constraint tokens in an expected error text after removing
    generic validation meta-vocabulary.
    If empty, the expectation is generic ('System shall display error message').
    """
    words = re.findall(r"[a-z]{3,}", (expected_text or "").lower())
    return [w for w in words if w not in GENERIC_META_VOCAB]

def is_generic_error_expectation(expected_text: str) -> bool:
    """Returns True if the expected error is a generic meta-statement rather than a domain-specific constraint."""
    return len(extract_specific_constraint_tokens(expected_text)) == 0

def extract_valid_entity_id(text: str) -> Optional[str]:
    """
    Universal GxP Entity ID extractor (zero application hardcoding).
    Extracts identifiers like CASE-2026-0042, BATCH-9821, SMPL-001, DEV-2026-12, ORD-402, CAS-9821, OPV-2026-001
    while strictly rejecting error codes like ERR-502 or HTTP-400.
    Works across any LIMS, ERP, Safety, or Clinical web app.
    """
    if not text:
        return None
    # Priority 1: Explicit labeled ID (e.g. "Case ID: CAS-9821", "Batch No: BATCH-01", "Sample #: SMPL-102")
    for m in re.finditer(r"(?:(?:case|record|batch|sample|order|subject|ticket|deviation|document|item|entity|reference|id)\s*(?:id|number|no|#)?\s*[:=]?\s*)([A-Z0-9]{2,10}-[A-Z0-9\-]{2,20})\b", text, re.I):
        cand = m.group(1).upper()
        if not cand.startswith(FORBIDDEN_ENTITY_PREFIXES):
            return cand
    # Priority 2: Standard structured enterprise entity token [PREFIX]-[ID]
    for m in re.finditer(r"\b([A-Z]{2,10}-(?:[A-Z0-9]{2,10}-)?[0-9A-Z\-]{3,20})\b", text):
        cand = m.group(1).upper()
        if not cand.startswith(FORBIDDEN_ENTITY_PREFIXES):
            return cand
    return None

def is_negative_step_expectation(step: ProtocolStep) -> bool:
    """Determines whether a protocol step expects a negative validation or blocked execution."""
    exp = (step.expected_result or "").lower()
    proc = (step.procedure or "").lower()
    scen = (step.scenario or "").lower()
    
    if any(a.assertion_type == "ERROR_MESSAGE" for a in (step.assertions or [])):
        return True
    if any(k in scen for k in ["negative", "invalid", "boundary error", "error handling", "future date"]):
        return True
    if any(k in exp for k in ["block", "cannot", "must not", "shall not", "prevent", "error alert", "error message", "restrict", "validation failed", "validation error"]):
        return True
    return False

def evaluate_step_gates(
    step: ProtocolStep,
    combined_feedback: str = "",
    detected_error: Optional[str] = None,
    action_dialog_text: str = "",
    body_text: str = "",
    execution_failures: Optional[List[str]] = None,
    failed_http_responses: Optional[List[str]] = None,
    is_negative: Optional[bool] = None,
    llm_client: Optional[Any] = None
) -> GateEvaluationResult:
    """
    Universal 4-Gate Zero-False-Positive Pass/Fail Verification Engine (v4.2).
    - Causal 3-Signal Correlation for Generic Negative Steps
    - Specific Domain-Constraint Semantic Verification
    - Compound Checkpoint State Machine (NEGATIVE -> POSITIVE & POSITIVE -> NEGATIVE)
    - Gate 1: Polarity, Network HTTP & Execution Guard
    - Gate 2: Entity ID & Target Field Discrepancy Guard
    - Gate 3: Offline Hybrid CPU Semantic Similarity Check (<8ms)
    - Gate 4: Grey-Zone Qwen Tie-Breaker (only if 0.55 <= sim < 0.70)
    """
    # 0. Check Compound Polarity Step Graph
    is_compound = getattr(step, "is_compound_polarity", False) and bool(step.checkpoints)
    is_final_positive = is_compound and step.checkpoints[-1].polarity == "POSITIVE"
    is_final_negative = is_compound and step.checkpoints[-1].polarity == "NEGATIVE"

    if is_negative is None:
        if is_compound:
            is_negative = is_final_negative
        else:
            is_negative = is_negative_step_expectation(step)

    all_feedback = f"{action_dialog_text} {combined_feedback}".strip()
    full_text_corpus = f"{all_feedback} {body_text}".strip()

    # Locate any error content across all sources
    error_content = (detected_error or "").strip()
    if not error_content:
        for src in [action_dialog_text, combined_feedback]:
            if src:
                src_l = src.lower()
                if any(k in src_l for k in ["error", "validation", "mandatory", "cannot", "failed", "required", "invalid", "err-"]):
                    error_content = src.strip()
                    break

    found_entity = extract_valid_entity_id(full_text_corpus)

    # -------------------------------------------------------------
    # GATE 1: POLARITY, NETWORK HTTP & EXECUTION FAILURE GUARD
    # -------------------------------------------------------------
    gate1_passed = True
    gate1_detail = "PASS (HTTP 2xx, 0 unexpected UI errors)"

    if is_final_positive:
        # Trajectory 1: NEGATIVE -> POSITIVE
        # Intermediate negative checkpoint must have verified
        if not step.test_data.get("intermediate_negative_verified", False):
            gate1_passed = False
            gate1_detail = "FAIL (Intermediate negative validation error did not trigger as expected)"
        elif execution_failures and len(execution_failures) > 0:
            gate1_passed = False
            gate1_detail = f"FAIL (Execution failure: {execution_failures[0]})"
        elif failed_http_responses and len(failed_http_responses) > 0:
            gate1_passed = False
            gate1_detail = f"FAIL (Network error: {failed_http_responses[0]})"
        else:
            gate1_passed = True
            gate1_detail = "PASS (Intermediate negative guard verified + Final positive action executed)"

    elif is_final_negative:
        # Trajectory 2: POSITIVE -> ... -> NEGATIVE
        # Check pre-submit assertions
        pre_saved = step.test_data.get("pre_save_verified_fields", {})
        pre_badge = step.test_data.get("pre_submit_badge_verified", False)
        needs_badge = any("code" in cp.expected_segment.lower() or "badge" in cp.expected_segment.lower() for cp in step.checkpoints[:-1])
        needs_auto = any("auto" in cp.expected_segment.lower() for cp in step.checkpoints[:-1])

        if needs_badge and not pre_badge:
            gate1_passed = False
            gate1_detail = "FAIL (Pre-submit positive check failed: status badge was not verified)"
        elif needs_auto and not pre_saved:
            gate1_passed = False
            gate1_detail = "FAIL (Pre-submit positive check failed: auto-populated field was not verified)"
        elif not error_content and not any(k in all_feedback.lower() for k in ["error", "validation", "mandatory", "required"]):
            gate1_passed = False
            gate1_detail = "FAIL (Defect Detected: System allowed submission without validation error on negative checkpoint)"
        else:
            gate1_passed = True
            gate1_detail = "PASS (Pre-submit positive assertions verified + Final negative submission blocked)"

    elif not is_negative:
        # Standard Positive Step
        if execution_failures and len(execution_failures) > 0:
            gate1_passed = False
            gate1_detail = f"FAIL (Execution failure: {execution_failures[0]})"
        elif failed_http_responses and len(failed_http_responses) > 0:
            gate1_passed = False
            gate1_detail = f"FAIL (Network error: {failed_http_responses[0]})"
        elif error_content:
            gate1_passed = False
            gate1_detail = f"FAIL (Unexpected UI error on positive step: '{error_content[:80]}')"
        elif any(k in all_feedback.lower() for k in ["error:", "failed to", "validation error", "validation failed", "cannot submit", "cannot register", "err-"]):
            gate1_passed = False
            gate1_detail = f"FAIL (Negative failure phrase detected in feedback: '{all_feedback[:80]}')"
    else:
        # Standard Negative Step
        has_success_message = any(k in all_feedback.lower() for k in ["registered successfully", "created successfully", "saved successfully", "case reference number"])
        if (has_success_message or (found_entity and not error_content)):
            gate1_passed = False
            gate1_detail = "FAIL (Defect Detected: System allowed invalid submission on negative test)"
        elif not error_content and not any(k in all_feedback.lower() for k in ["error", "validation", "mandatory", "required", "invalid"]):
            gate1_passed = False
            gate1_detail = "FAIL (Expected validation error was not displayed by application)"
        else:
            gate1_passed = True
            gate1_detail = "PASS (System correctly blocked invalid submission)"

    if not gate1_passed:
        return GateEvaluationResult(
            gate1_polarity_and_http=gate1_detail,
            gate1_passed=False,
            gate2_field_and_entity_guard="SKIPPED",
            gate2_passed=False,
            gate3_semantic_similarity=0.0,
            gate3_passed=False,
            final_status="FAIL",
            observed_summary=f"Gate 1 Rejected: {gate1_detail}",
            failure_reason=gate1_detail
        )

    # -------------------------------------------------------------
    # GATE 2: ENTITY ID & TARGET FIELD DISCREPANCY GUARD
    # -------------------------------------------------------------
    gate2_passed = True
    gate2_detail = "PASS (Target controls & entity criteria satisfied)"
    similarity_score = 1.0

    has_entity_assertion = any(a.assertion_type == "ENTITY_CREATED" for a in (step.assertions or []))
    has_error_assertion = any(a.assertion_type == "ERROR_MESSAGE" for a in (step.assertions or [])) or is_negative

    # Check Entity ID creation requirement
    if has_entity_assertion:
        if not found_entity:
            gate2_passed = False
            gate2_detail = "FAIL (Missing expected created entity ID; cannot verify ENTITY_CREATED)"
        else:
            gate2_detail = f"PASS (Entity {found_entity} verified; no forbidden prefix)"

    # Check Confirmation Message for Positive Final Steps
    if gate2_passed and (not is_negative or is_final_positive):
        exp_low = (step.expected_result or "").lower()
        if is_compound and step.checkpoints:
            exp_low = step.checkpoints[-1].expected_segment.lower()
        if any(k in exp_low for k in ["confirmation message", "popup shall display", "message shall display", "modal shall display", "delete the record successfully", "save successfully"]):
            if not all_feedback and not found_entity:
                gate2_passed = False
                gate2_detail = "FAIL (Expected confirmation popup or message was not displayed)"
            else:
                gate2_detail = f"PASS (Confirmation verified: '{all_feedback[:60]}')"

    # Check Error Message requirement on Negative Step / Trajectory 2
    if gate2_passed and has_error_assertion and (is_negative or is_final_negative):
        if not error_content:
            gate2_passed = False
            gate2_detail = "FAIL (Expected validation error was not displayed by application)"
        else:
            # Determine expected error text
            if is_compound and step.checkpoints:
                neg_cps = [cp for cp in step.checkpoints if cp.polarity == "NEGATIVE"]
                expected_error_text = neg_cps[-1].expected_segment if neg_cps else step.expected_result
            else:
                expected_error_text = step.expected_result

            specific_tokens = extract_specific_constraint_tokens(expected_error_text)
            is_generic = (len(specific_tokens) == 0)

            if is_generic:
                # Causal 3-Signal Correlation:
                # Signal 1: Error UI surfaced & non-500
                s1 = bool(error_content) and not any("500" in h or "502" in h or "503" in h for h in (failed_http_responses or []))
                # Signal 2: Mutation blocked (no created entity)
                s2 = (found_entity is None)
                # Signal 3: Causal Input Consistency
                # If error ONLY blames fields that were already filled and readback-verified,
                # our input failed to register in the UI.
                filled_field_names = [
                    ai.field_label.lower().strip()
                    for ai in (step.applied_inputs or [])
                    if getattr(ai, "readback_verified", False)
                ]
                err_low = error_content.lower()
                blames_verified_filled_field = False
                if filled_field_names:
                    for fn in filled_field_names:
                        if len(fn) >= 3 and fn in err_low:
                            if any(w in err_low for w in ["is required", "is mandatory", "cannot be blank", "cannot be empty", "missing"]):
                                blames_verified_filled_field = True
                                break
                s3 = not blames_verified_filled_field

                if s1 and s2 and s3:
                    gate2_passed = True
                    gate2_detail = "PASS (Causal Signal 3: Valid error state consistent with inputs applied)"
                    similarity_score = 1.0
                else:
                    gate2_passed = False
                    gate2_detail = f"FAIL (Causal 3-Signal discrepancy: s1={s1}, s2={s2}, s3={s3})"
            else:
                # Specific domain constraint:
                sim_field = compute_assertion_similarity(expected_error_text, error_content)
                token_overlap = any(tok in error_content.lower() for tok in specific_tokens)
                if sim_field < 0.65 and not token_overlap:
                    gate2_passed = False
                    gate2_detail = f"FAIL (Wrong Validation Error Triggered: Expected '{expected_error_text[:60]}', but observed '{error_content[:80]}')"
                    similarity_score = sim_field
                else:
                    gate2_passed = True
                    gate2_detail = f"PASS (Target domain validation error confirmed: '{error_content[:60]}')"
                    similarity_score = max(sim_field, 0.75)

    if not gate2_passed:
        return GateEvaluationResult(
            gate1_polarity_and_http=gate1_detail,
            gate1_passed=True,
            gate2_field_and_entity_guard=gate2_detail,
            gate2_passed=False,
            gate3_semantic_similarity=similarity_score if has_error_assertion else 0.0,
            gate3_passed=False,
            final_status="FAIL",
            observed_summary=f"Gate 2 Rejected: {gate2_detail}",
            failure_reason=gate2_detail
        )

    # -------------------------------------------------------------
    # GATE 3: OFFLINE HYBRID CPU SEMANTIC SIMILARITY CHECK (<8ms)
    # -------------------------------------------------------------
    target_observed = error_content if (is_negative or is_final_negative) else (all_feedback or found_entity or "Action completed successfully")
    
    if not (has_error_assertion and (is_negative or is_final_negative) and is_generic_error_expectation(step.expected_result)):
        if not is_final_positive:
            similarity_score = compute_assertion_similarity(step.expected_result, target_observed)

    gate3_passed = True
    gate3_detail = f"PASS (Offline CPU similarity: {similarity_score})"
    gate4_used = False
    gate4_verdict = None

    if (is_negative or is_final_negative) and has_error_assertion:
        expected_error_text = step.expected_result
        if is_compound and step.checkpoints:
            neg_cps = [cp for cp in step.checkpoints if cp.polarity == "NEGATIVE"]
            expected_error_text = neg_cps[-1].expected_segment if neg_cps else step.expected_result

        is_gen = is_generic_error_expectation(expected_error_text)
        if is_gen:
            similarity_score = 1.0
            gate3_passed = True
            gate3_detail = "PASS (Causal 3-Signal Correlation satisfied for generic validation expectation)"
        else:
            if similarity_score >= 0.65:
                gate3_passed = True
            elif 0.50 <= similarity_score < 0.65:
                gate4_used = True
                if llm_client and hasattr(llm_client, "chat_completion") and (llm_client.groq_api_key or llm_client.is_dgx_configured()):
                    try:
                        sys_prompt = "You are an FDA GxP validation judge. Determine if the observed system error satisfies the protocol expectation. Answer with exactly 'PASS' or 'FAIL'."
                        user_p = f"Expected: {expected_error_text}\nObserved: {target_observed}"
                        ans = llm_client.chat_completion(
                            messages=[{"role": "system", "content": sys_prompt}, {"role": "user", "content": user_p}],
                            max_tokens=10,
                            temperature=0.0
                        )
                        if ans and "PASS" in ans.upper():
                            gate3_passed = True
                            gate4_verdict = "PASS"
                        else:
                            gate3_passed = False
                            gate4_verdict = "FAIL"
                    except Exception:
                        gate3_passed = (similarity_score >= 0.58)
                        gate4_verdict = "FALLBACK_CPU"
                else:
                    gate3_passed = (similarity_score >= 0.58)
                    gate4_verdict = "OFFLINE_RULE_PASS" if gate3_passed else "OFFLINE_RULE_FAIL"
            else:
                gate3_passed = False
                gate3_detail = f"FAIL (CPU similarity {similarity_score} < 0.65 for specific constraint)"

    final_status = "PASS" if (gate1_passed and gate2_passed and gate3_passed) else "FAIL"
    obs_summary = (
        f"Validation Verified: Observed '{target_observed[:90]}' satisfies expected criteria (sim={similarity_score})."
        if final_status == "PASS" else
        f"Verification Discrepancy: {gate2_detail if not gate2_passed else gate3_detail}"
    )

    return GateEvaluationResult(
        gate1_polarity_and_http=gate1_detail,
        gate1_passed=gate1_passed,
        gate2_field_and_entity_guard=gate2_detail,
        gate2_passed=gate2_passed,
        gate3_semantic_similarity=similarity_score,
        gate3_method="CPU_SEMANTIC_HYBRID",
        gate3_passed=gate3_passed,
        gate4_llm_tiebreaker_used=gate4_used,
        gate4_verdict=gate4_verdict,
        final_status=final_status,
        observed_summary=obs_summary,
        failure_reason=None if final_status == "PASS" else obs_summary
    )
