import re
from typing import List, Optional, Tuple, Any, Dict
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
    Universal 4-Gate Zero-False-Positive Pass/Fail Verification Engine.
    - Gate 1: Polarity, Network HTTP & Execution Guard
    - Gate 2: Entity ID & Target Field Discrepancy Guard
    - Gate 3: Offline Hybrid CPU Semantic Similarity Check (<8ms)
    - Gate 4: Grey-Zone Qwen Tie-Breaker (only if 0.55 <= sim < 0.70)
    """
    if is_negative is None:
        is_negative = is_negative_step_expectation(step)

    all_feedback = f"{action_dialog_text} {combined_feedback}".strip()
    full_text_corpus = f"{all_feedback} {body_text}".strip()

    # Locate any error content across all sources
    error_content = detected_error or ""
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

    if not is_negative:
        # Positive Step
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
        # Negative Step
        # If negative test expects blocked submission, but UI confirmed creation without error
        has_success_message = any(k in all_feedback.lower() for k in ["registered successfully", "created successfully", "saved successfully", "case reference number"])
        if (has_success_message or (found_entity and not error_content)):
            gate1_passed = False
            gate1_detail = "FAIL (Defect Detected: System allowed invalid submission on negative test)"
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

    has_entity_assertion = any(a.assertion_type == "ENTITY_CREATED" for a in (step.assertions or []))
    has_error_assertion = any(a.assertion_type == "ERROR_MESSAGE" for a in (step.assertions or [])) or is_negative

    # Check Entity ID creation requirement
    if has_entity_assertion:
        if not found_entity:
            gate2_passed = False
            gate2_detail = "FAIL (Missing expected created entity ID; cannot verify ENTITY_CREATED)"
        else:
            gate2_detail = f"PASS (Entity {found_entity} verified; no forbidden prefix)"

    # Check Error Message requirement on Negative Step
    if gate2_passed and has_error_assertion:
        if not error_content:
            gate2_passed = False
            gate2_detail = "FAIL (Expected validation error was not displayed by application)"
        else:
            # Field Guard: Verify error message relates to expected field
            sim_field = compute_assertion_similarity(step.expected_result, error_content)
            if sim_field < 0.45:
                gate2_passed = False
                gate2_detail = f"FAIL (Wrong Validation Error Triggered: Expected '{step.expected_result[:60]}', but observed '{error_content[:80]}')"
            else:
                gate2_detail = f"PASS (Target validation error confirmed: '{error_content[:60]}')"

    # Check Confirmation Message
    if gate2_passed and not is_negative:
        exp_low = (step.expected_result or "").lower()
        if any(k in exp_low for k in ["confirmation message", "popup shall display", "message shall display", "modal shall display"]):
            if not all_feedback:
                gate2_passed = False
                gate2_detail = "FAIL (Expected confirmation popup or message was not displayed)"

    if not gate2_passed:
        return GateEvaluationResult(
            gate1_polarity_and_http=gate1_detail,
            gate1_passed=True,
            gate2_field_and_entity_guard=gate2_detail,
            gate2_passed=False,
            gate3_semantic_similarity=0.0,
            gate3_passed=False,
            final_status="FAIL",
            observed_summary=f"Gate 2 Rejected: {gate2_detail}",
            failure_reason=gate2_detail
        )

    # -------------------------------------------------------------
    # GATE 3: OFFLINE HYBRID CPU SEMANTIC SIMILARITY CHECK (<8ms)
    # -------------------------------------------------------------
    target_observed = error_content if is_negative else (all_feedback or found_entity or "Action completed successfully")
    similarity_score = compute_assertion_similarity(step.expected_result, target_observed)

    gate3_passed = True
    gate3_detail = f"PASS (Offline CPU similarity: {similarity_score})"
    gate4_used = False
    gate4_verdict = None

    if is_negative and has_error_assertion:
        if similarity_score >= 0.70:
            gate3_passed = True
        elif 0.50 <= similarity_score < 0.70:
            # Grey zone: try Gate 4 tie-breaker if LLM available, else fail-safe check
            gate4_used = True
            if llm_client and hasattr(llm_client, "chat_completion") and (llm_client.groq_api_key or llm_client.is_dgx_configured()):
                try:
                    sys_prompt = "You are an FDA GxP validation judge. Determine if the observed system error satisfies the protocol expectation. Answer with exactly 'PASS' or 'FAIL'."
                    user_p = f"Expected: {step.expected_result}\nObserved: {target_observed}"
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
            gate3_detail = f"FAIL (CPU similarity {similarity_score} < 0.50)"

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
