import sys
import copy
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(backend_dir))

# Configure stdout for safe encoding on Windows
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from extractor import extract_protocol
from agents import PlannerAgent
from check_coverage import check_protocol_to_plan

def run_phase2_verification():
    protocol_path = backend_dir / "uploads" / "CLIN-EU-PAT-OPV-1-1-PQ-022- Manual - Registering Adverse Event Case.docx"
    
    print("=" * 85)
    print("PHASE 2 VERIFICATION: Qwen Planner Agent & Field-Level Coverage Gate 1")
    print(f"Protocol: {protocol_path.name}")
    print("=" * 85)

    # 1. Run Phase 1 Extractor
    session = extract_protocol(str(protocol_path))
    
    # 2. Run Phase 2 Qwen Planner
    planner = PlannerAgent()
    legacy_plan, md_plan, latency = planner.generate_plan(session)

    print("\n--- 1. COVERAGE GATE 1 BASELINE AUDIT ---")
    gate1 = session.gate1_report
    assert gate1 is not None, "Gate 1 report not generated"
    print(f"Gate 1 Passed:              {gate1.passed}")
    print(f"Total Steps (Proto / Plan): {gate1.total_steps_expected} / {gate1.total_steps_mapped}")
    print(f"Total Fields (Proto/ Plan): {gate1.total_fields_expected} / {gate1.total_fields_mapped}")
    print(f"Missing Steps:              {len(gate1.missing_steps)}")
    print(f"Missing Fields:             {len(gate1.missing_fields)}")
    print(f"Order Mismatches:           {len(gate1.order_mismatch_errors)}")
    assert gate1.passed, f"Gate 1 failed: {gate1.missing_fields} {gate1.order_mismatch_errors}"

    plan_dict = {p.step_id: p for p in session.planned_steps}

    # 3. Print Planned Field Tables for Critical Steps
    print("\n--- 2. DETAILED PLANNED FIELD ACTIONS AUDIT ---")
    
    # Step 9: Reporter (16 fields)
    p9 = plan_dict["TS1-S09"]
    print(f"\n[Step 9: {p9.step_id}] Scenario: {p9.scenario}")
    print(f"Planned Fields: {len(p9.field_actions)} / 16")
    for fa in p9.field_actions:
        print(f"  • {fa.field_id}: [{fa.section}] '{fa.label}' <{fa.control_type}> -> Target Value: '{fa.target_value}'")
    assert len(p9.field_actions) == 16

    # Step 10: Patient (15 fields)
    p10 = plan_dict["TS1-S10"]
    print(f"\n[Step 10: {p10.step_id}] Scenario: {p10.scenario}")
    print(f"Planned Fields: {len(p10.field_actions)} / 15")
    for fa in p10.field_actions:
        print(f"  • {fa.field_id}: [{fa.section}] '{fa.label}' <{fa.control_type}> -> Target Value: '{fa.target_value}'")
    assert len(p10.field_actions) == 15

    # Step 11: Product (4 fields)
    p11 = plan_dict["TS1-S11"]
    print(f"\n[Step 11: {p11.step_id}] Scenario: {p11.scenario}")
    print(f"Planned Fields: {len(p11.field_actions)} / 4")
    for fa in p11.field_actions:
        auto_str = " [EXPECT AUTO-POPULATED]" if fa.expect_auto_populated else ""
        print(f"  • {fa.field_id}: [{fa.section}] '{fa.label}' <{fa.control_type}> -> Target Value: '{fa.target_value}'{auto_str}")
    assert len(p11.field_actions) == 4

    # Step 12: Event (16 fields)
    p12 = plan_dict["TS1-S12"]
    print(f"\n[Step 12: {p12.step_id}] Scenario: {p12.scenario}")
    print(f"Planned Fields: {len(p12.field_actions)} / 16")
    for fa in p12.field_actions:
        print(f"  • {fa.field_id}: [{fa.section}] '{fa.label}' <{fa.control_type}> -> Target Value: '{fa.target_value}'")
    assert len(p12.field_actions) == 16

    # 4. NEGATIVE MUTATION TESTS (Auditing Gate 1 Rigor)
    print("\n" + "=" * 85)
    print("--- 3. NEGATIVE MUTATION AUDITS ON COVERAGE GATE 1 ---")

    # Mutation A: Drop 1 Reporter Field ("Fax")
    mut_session_a = copy.deepcopy(session)
    mut_p9 = next(p for p in mut_session_a.planned_steps if p.step_id == "TS1-S09")
    mut_p9.field_actions = [fa for fa in mut_p9.field_actions if fa.label != "Fax"]
    report_a = check_protocol_to_plan(mut_session_a)
    print(f"\n[Mutation A: Dropped Reporter Field 'Fax']")
    print(f"  Gate 1 Passed:  {report_a.passed} (Expected: False)")
    print(f"  Missing Fields: {report_a.missing_fields}")
    assert not report_a.passed, "Gate 1 should have failed for dropped 'Fax' field"
    assert any("TS1-S09:Fax" in mf for mf in report_a.missing_fields)
    print("  [PASS] Mutation A Detected: Gate 1 caught dropped 'Fax' field!")

    # Mutation B: Drop 1 Seriousness Dropdown ("Death")
    mut_session_b = copy.deepcopy(session)
    mut_p12 = next(p for p in mut_session_b.planned_steps if p.step_id == "TS1-S12")
    mut_p12.field_actions = [fa for fa in mut_p12.field_actions if fa.label != "Death"]
    report_b = check_protocol_to_plan(mut_session_b)
    print(f"\n[Mutation B: Dropped Seriousness Dropdown 'Death']")
    print(f"  Gate 1 Passed:  {report_b.passed} (Expected: False)")
    print(f"  Missing Fields: {report_b.missing_fields}")
    assert not report_b.passed, "Gate 1 should have failed for dropped 'Death' dropdown"
    assert any("TS1-S12:Death" in mf for mf in report_b.missing_fields)
    print("  [PASS] Mutation B Detected: Gate 1 caught dropped 'Death' dropdown!")

    # Mutation C: Swap Sequence Order of Step 4 and Step 5
    mut_session_c = copy.deepcopy(session)
    idx4 = next(i for i, p in enumerate(mut_session_c.planned_steps) if p.step_id == "TS1-S04")
    idx5 = next(i for i, p in enumerate(mut_session_c.planned_steps) if p.step_id == "TS1-S05")
    mut_session_c.planned_steps[idx4], mut_session_c.planned_steps[idx5] = mut_session_c.planned_steps[idx5], mut_session_c.planned_steps[idx4]
    report_c = check_protocol_to_plan(mut_session_c)
    print(f"\n[Mutation C: Swapped Step 4 & Step 5 Sequence Order]")
    print(f"  Gate 1 Passed:    {report_c.passed} (Expected: False)")
    print(f"  Order Violations: {report_c.order_mismatch_errors}")
    assert not report_c.passed, "Gate 1 should have failed for sequence order mismatch"
    assert len(report_c.order_mismatch_errors) > 0
    print("  [PASS] Mutation C Detected: Gate 1 caught sequence order mismatch!")

    print("\n" + "=" * 85)
    print("🎉 ALL PHASE 2 VERIFICATIONS & MUTATION TESTS PASSED WITH 100% SUCCESS!")
    print("=" * 85)

if __name__ == "__main__":
    run_phase2_verification()
