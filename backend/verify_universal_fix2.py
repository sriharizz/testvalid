import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from schemas import ProtocolStep, StepAssertion, StepCheckpoint, AppliedInputRecord
from verification_engine import evaluate_step_gates, extract_specific_constraint_tokens, is_generic_error_expectation

def test_generic_error_expectation_causal_pass():
    print("[Check 1] Testing generic error expectation with clinical validation alert via Causal 3-Signal Correlation...")
    step = ProtocolStep(
        step_id="TS1-S01",
        procedure="Click Submit without entering required fields.",
        expected_result="System shall display error message.",
        action_intent="FORM_ENTRY",
        assertions=[StepAssertion(assertion_type="ERROR_MESSAGE", description="Error message displays")]
    )
    assert is_generic_error_expectation(step.expected_result) is True
    assert len(extract_specific_constraint_tokens(step.expected_result)) == 0

    error_alert = "Validation Error: Reporter Country is required to submit the case."
    res = evaluate_step_gates(step, detected_error=error_alert)

    print(f"  -> Gate 1: {res.gate1_polarity_and_http}")
    print(f"  -> Gate 2: {res.gate2_field_and_entity_guard}")
    print(f"  -> Gate 3: sim={res.gate3_semantic_similarity}, passed={res.gate3_passed}")
    print(f"  -> Final Status: {res.final_status}")

    assert res.final_status == "PASS", f"Expected PASS for generic error, got {res.final_status}: {res.failure_reason}"
    assert res.gate3_semantic_similarity == 1.0, f"Expected 1.0 similarity for Causal 3-Signal Correlation, got {res.gate3_semantic_similarity}"
    print("  -> PASS: Generic error expectation verified via Causal 3-Signal Correlation with score = 1.0!")

def test_specific_domain_constraint_wrong_field_rejection():
    print("[Check 2] Testing specific domain constraint rejection when wrong field error is surfaced...")
    step = ProtocolStep(
        step_id="TS1-S02",
        procedure="Enter tomorrow's date for Admission Date and click Submit.",
        expected_result="System should show an error alert that Admission Date cannot be in the future.",
        action_intent="FORM_ENTRY",
        assertions=[StepAssertion(assertion_type="ERROR_MESSAGE", description="Admission date cannot be in the future")]
    )
    tokens = extract_specific_constraint_tokens(step.expected_result)
    assert "admission" in tokens and "future" in tokens
    assert is_generic_error_expectation(step.expected_result) is False

    wrong_error = "Validation Error: Reporter Country is required."
    res = evaluate_step_gates(step, detected_error=wrong_error)

    print(f"  -> Gate 1: {res.gate1_polarity_and_http}")
    print(f"  -> Gate 2: {res.gate2_field_and_entity_guard}")
    print(f"  -> Final Status: {res.final_status}")

    assert res.final_status == "FAIL", "Expected FAIL when specific constraint does not match observed error!"
    assert not res.gate2_passed, "Expected Gate 2 to reject wrong field error!"
    print("  -> PASS: Specific constraint correctly failed when wrong field error occurred!")

def test_compound_trajectory1_negative_to_positive():
    print("[Check 3] Testing Trajectory 1 (NEGATIVE -> POSITIVE compound step)...")
    # Subtest 3A: Passes when intermediate negative error is verified and final positive deletion succeeds
    step_pass = ProtocolStep(
        step_id="TS1-S03",
        procedure="Click Delete directly. (Refer expected result 1)\nEnter reason and Confirm Delete. (Refer expected result 2)",
        expected_result="Error message shall display.\n\nSystem shall delete the record successfully with confirmation message.",
        action_intent="FORM_ENTRY",
        is_compound_polarity=True,
        checkpoints=[
            StepCheckpoint(checkpoint_index=1, procedure_segment="Click Delete directly.", expected_segment="Error message shall display.", polarity="NEGATIVE"),
            StepCheckpoint(checkpoint_index=2, procedure_segment="Enter reason and Confirm Delete.", expected_segment="System shall delete the record successfully with confirmation message.", polarity="POSITIVE")
        ],
        test_data={"intermediate_negative_verified": True}
    )
    res_pass = evaluate_step_gates(step_pass, action_dialog_text="System deleted the record successfully with confirmation message.")
    assert res_pass.final_status == "PASS", f"Expected PASS for Trajectory 1 with verified intermediate error, got {res_pass.final_status}"
    print("  -> PASS: Trajectory 1 passed when intermediate negative error was verified!")

    # Subtest 3B: Strictly FAILS if the intermediate negative error never triggered
    step_fail = ProtocolStep(
        step_id="TS1-S03B",
        procedure="Click Delete directly. (Refer expected result 1)\nEnter reason and Confirm Delete. (Refer expected result 2)",
        expected_result="Error message shall display.\n\nSystem shall delete the record successfully with confirmation message.",
        action_intent="FORM_ENTRY",
        is_compound_polarity=True,
        checkpoints=[
            StepCheckpoint(checkpoint_index=1, procedure_segment="Click Delete directly.", expected_segment="Error message shall display.", polarity="NEGATIVE"),
            StepCheckpoint(checkpoint_index=2, procedure_segment="Enter reason and Confirm Delete.", expected_segment="System shall delete the record successfully with confirmation message.", polarity="POSITIVE")
        ],
        test_data={"intermediate_negative_verified": False}
    )
    res_fail = evaluate_step_gates(step_fail, action_dialog_text="System deleted the record successfully with confirmation message.")
    assert res_fail.final_status == "FAIL", "Expected FAIL for Trajectory 1 when intermediate negative error did NOT occur!"
    assert not res_fail.gate1_passed
    print("  -> PASS: Trajectory 1 correctly failed when intermediate negative error was missing!")

def test_compound_trajectory2_positive_to_negative():
    print("[Check 4] Testing Trajectory 2 (POSITIVE -> POSITIVE -> NEGATIVE compound step)...")
    # Subtest 4A: Passes when pre-submit assertions + final negative validation error all succeed
    step_pass = ProtocolStep(
        step_id="TS1-S04",
        procedure="Select Drug (Refer expected result 1).\nCode term (Refer expected result 2).\nClick Submit (Refer expected result 3).",
        expected_result="Generic name shall auto populate.\n\nTerm shall code successfully.\n\nSystem shall display error message.",
        action_intent="FORM_ENTRY",
        is_compound_polarity=True,
        checkpoints=[
            StepCheckpoint(checkpoint_index=1, procedure_segment="Select Drug", expected_segment="Generic name shall auto populate.", polarity="POSITIVE"),
            StepCheckpoint(checkpoint_index=2, procedure_segment="Code term", expected_segment="Term shall code successfully.", polarity="POSITIVE"),
            StepCheckpoint(checkpoint_index=3, procedure_segment="Click Submit", expected_segment="System shall display error message.", polarity="NEGATIVE")
        ],
        test_data={
            "pre_save_verified_fields": {"Generic Name": "Aspirin"},
            "pre_submit_badge_verified": True
        }
    )
    res_pass = evaluate_step_gates(step_pass, detected_error="Validation Error: Mandatory fields cannot be empty.")
    assert res_pass.final_status == "PASS", f"Expected PASS for Trajectory 2, got {res_pass.final_status}: {res_pass.failure_reason}"
    print("  -> PASS: Trajectory 2 passed when pre-submit badge & fields and final negative error succeeded!")

    # Subtest 4B: Strictly FAILS if pre-submit badge was missing
    step_fail = ProtocolStep(
        step_id="TS1-S04B",
        procedure="Select Drug (Refer expected result 1).\nCode term (Refer expected result 2).\nClick Submit (Refer expected result 3).",
        expected_result="Generic name shall auto populate.\n\nTerm shall code successfully.\n\nSystem shall display error message.",
        action_intent="FORM_ENTRY",
        is_compound_polarity=True,
        checkpoints=[
            StepCheckpoint(checkpoint_index=1, procedure_segment="Select Drug", expected_segment="Generic name shall auto populate.", polarity="POSITIVE"),
            StepCheckpoint(checkpoint_index=2, procedure_segment="Code term", expected_segment="Term shall code successfully.", polarity="POSITIVE"),
            StepCheckpoint(checkpoint_index=3, procedure_segment="Click Submit", expected_segment="System shall display error message.", polarity="NEGATIVE")
        ],
        test_data={
            "pre_save_verified_fields": {"Generic Name": "Aspirin"},
            "pre_submit_badge_verified": False
        }
    )
    res_fail = evaluate_step_gates(step_fail, detected_error="Validation Error: Mandatory fields cannot be empty.")
    assert res_fail.final_status == "FAIL", "Expected FAIL for Trajectory 2 when pre-submit badge check failed!"
    assert not res_fail.gate1_passed
    print("  -> PASS: Trajectory 2 correctly failed when pre-submit badge check failed!")

if __name__ == "__main__":
    print("=== RUNNING UNIVERSAL FIX 2 VERIFICATION SUITE ===")
    test_generic_error_expectation_causal_pass()
    test_specific_domain_constraint_wrong_field_rejection()
    test_compound_trajectory1_negative_to_positive()
    test_compound_trajectory2_positive_to_negative()
    print("=== [100% PASS] UNIVERSAL FIX 2 COMPLETE! ===")
