import sys
import asyncio
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from playwright.async_api import async_playwright
from schemas import ProtocolStep, StepAssertion
from verification_engine import evaluate_step_gates, extract_valid_entity_id
from playwright_runner import verify_expected_result

async def run_phase4_verification():
    print("=== PHASE 4 VERIFICATION: 4-GATE ZERO-FALSE-POSITIVE ENGINE ===")

    # TRAP 1: Positive ENTITY_CREATED + MESSAGE_DISPLAYED with "Error: Failed to create case successfully. Code: ERR-502"
    s1 = ProtocolStep(
        step_id="TS1-S01",
        table_index=2,
        row_index=1,
        scenario="Register Case Positive",
        procedure="Click Save and submit case. (µ)",
        expected_result="System shall register case successfully with confirmation message and temporary case ID shall create.",
        action_intent="FORM_ENTRY",
        primary_section="general",
        assertions=[
            StepAssertion(assertion_type="MESSAGE_DISPLAYED", description="Confirmation message"),
            StepAssertion(assertion_type="ENTITY_CREATED", description="Case ID creation", pattern=r"[A-Z0-9-]+")
        ]
    )
    g1 = evaluate_step_gates(
        step=s1,
        combined_feedback="Error: Failed to create case successfully. Code: ERR-502",
        detected_error="Error: Failed to create case successfully. Code: ERR-502"
    )
    print(f"[Trap 1] g1.final_status = {g1.final_status}, gate1={g1.gate1_polarity_and_http}, gate2={g1.gate2_field_and_entity_guard}")
    assert g1.final_status == "FAIL", "Trap 1 must fail when ERR-502 error is returned on positive step"
    assert not g1.gate1_passed or not g1.gate2_passed

    # TRAP 2: Positive ENTITY_CREATED with "Form saved." (No Case ID generated)
    s2 = ProtocolStep(
        step_id="TS1-S02",
        table_index=2,
        row_index=2,
        scenario="Register Case Positive",
        procedure="Click Save. (µ)",
        expected_result="System shall create case and display generated Case ID.",
        action_intent="FORM_ENTRY",
        primary_section="general",
        assertions=[
            StepAssertion(assertion_type="ENTITY_CREATED", description="Case ID creation", pattern=r"[A-Z0-9-]+")
        ]
    )
    g2 = evaluate_step_gates(
        step=s2,
        combined_feedback="Form saved successfully.",
        body_text="<div>Form saved successfully. Status: Ready.</div>"
    )
    print(f"[Trap 2] g2.final_status = {g2.final_status}, gate2={g2.gate2_field_and_entity_guard}")
    assert g2.final_status == "FAIL", "Trap 2 must fail when no entity ID was extracted"
    assert g2.gate2_passed is False

    # TRAP 3: Negative ERROR_MESSAGE expecting Admission Date future when UI shows "Validation Error: Reporter Country is required"
    s3 = ProtocolStep(
        step_id="TS3-S07",
        table_index=2,
        row_index=7,
        scenario="Negative Future Admission Date",
        procedure="Set admission date to tomorrow and click Save. (µ)",
        expected_result="System should block registration and show an error alert that Admission Date cannot be in the future.",
        action_intent="FORM_ENTRY",
        primary_section="event",
        assertions=[
            StepAssertion(assertion_type="ERROR_MESSAGE", description="Admission Date error", target_text="error")
        ]
    )
    g3 = evaluate_step_gates(
        step=s3,
        combined_feedback="Validation Error: Reporter Country is required.",
        detected_error="Validation Error: Reporter Country is required."
    )
    print(f"[Trap 3] g3.final_status = {g3.final_status}, gate2={g3.gate2_field_and_entity_guard}")
    assert g3.final_status == "FAIL", "Trap 3 must fail on wrong field error message"
    assert g3.gate2_passed is False

    # TRAP 4: Negative ERROR_MESSAGE expecting Admission Date future when UI shows paraphrased:
    # "Validation Failed: Date of Hospital Admission must not be later than current date."
    g4 = evaluate_step_gates(
        step=s3,
        combined_feedback="Validation Failed: Date of Hospital Admission must not be later than current date.",
        detected_error="Validation Failed: Date of Hospital Admission must not be later than current date."
    )
    print(f"[Trap 4] g4.final_status = {g4.final_status}, gate2={g4.gate2_field_and_entity_guard}, sim={g4.gate3_semantic_similarity}")
    assert g4.final_status == "PASS", "Trap 4 must pass paraphrased error message without LLM calls"
    assert g4.gate1_passed is True and g4.gate2_passed is True and g4.gate3_passed is True

    # TRAP 5: Negative step expecting blocked registration when UI accidentally saves and shows:
    # "Case registered successfully. Temporary Case ID: TMP-CASE-9912"
    g5 = evaluate_step_gates(
        step=s3,
        combined_feedback="Case registered successfully. Temporary Case ID: TMP-CASE-9912",
        body_text="Case registered successfully. Temporary Case ID: TMP-CASE-9912"
    )
    print(f"[Trap 5] g5.final_status = {g5.final_status}, gate1={g5.gate1_polarity_and_http}")
    assert g5.final_status == "FAIL", "Trap 5 must fail when invalid submission succeeded on negative test"
    assert g5.gate1_passed is False

    # 6. End-to-End Live Playwright test for verify_expected_result()
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        # Test Trap 1 in live page
        await page.set_content("<div id='toast'>Error: Failed to create case successfully. Code: ERR-502</div>")
        is_p1, obs1, fail1 = await verify_expected_result(page, s1, action_dialog_text="Error: Failed to create case successfully. Code: ERR-502")
        print(f"[Live Trap 1] is_p1={is_p1}, obs='{obs1[:60]}'")
        assert is_p1 is False, "Live Trap 1 must fail"

        # Test Trap 4 in live page
        await page.set_content("<div role='alert'>Validation Failed: Date of Hospital Admission must not be later than current date.</div>")
        is_p4, obs4, fail4 = await verify_expected_result(page, s3, action_dialog_text="Validation Failed: Date of Hospital Admission must not be later than current date.")
        print(f"[Live Trap 4] is_p4={is_p4}, obs='{obs4[:60]}'")
        assert is_p4 is True, "Live Trap 4 must pass"

        await browser.close()

    print("[PASS] ALL 5 ZERO-FALSE-POSITIVE TRAPS BLOCKED! PHASE 4 VERIFICATION COMPLETE!")

if __name__ == "__main__":
    asyncio.run(run_phase4_verification())
