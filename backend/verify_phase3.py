import sys
import copy
import re
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
from agents import PlannerAgent, PlaywrightGeneratorAgent
from check_coverage import check_plan_to_spec

def run_phase3_verification():
    protocol_path = backend_dir / "uploads" / "CLIN-EU-PAT-OPV-1-1-PQ-022- Manual - Registering Adverse Event Case.docx"
    
    print("=" * 85)
    print("PHASE 3 VERIFICATION: Playwright Spec Generator, Healer & Coverage Gate 2")
    print(f"Protocol: {protocol_path.name}")
    print("=" * 85)

    # 1. Run Phase 1 Extractor
    session = extract_protocol(str(protocol_path))

    # 2. Run Phase 2 Qwen Planner
    planner = PlannerAgent()
    legacy_plan, md_plan, _ = planner.generate_plan(session)

    # 3. Run Phase 3 Playwright Generator Agent
    generator = PlaywrightGeneratorAgent()
    spec_code, latency = generator.generate_spec(session, legacy_plan)

    print("\n--- 1. COVERAGE GATE 2 BASELINE AUDIT ---")
    gate2 = session.gate2_report
    assert gate2 is not None, "Gate 2 report was not generated"
    print(f"Gate 2 Passed:              {gate2.passed}")
    print(f"Total Steps (Plan / Spec):  {gate2.total_steps_expected} / {gate2.total_steps_mapped}")
    print(f"Total Fields (Plan / Spec): {gate2.total_fields_expected} / {gate2.total_fields_mapped}")
    print(f"Missing Steps:              {len(gate2.missing_steps)}")
    print(f"Missing Fields:             {len(gate2.missing_fields)}")
    print(f"Order Mismatches:           {len(gate2.order_mismatch_errors)}")
    print(f"Skip Violations:            {len(gate2.skip_violations)}")
    print(f"Screenshot Errors:          {len(gate2.screenshot_errors)}")
    print(f"Git Baseline Hash:          {session.git_baseline_commit}")
    assert gate2.passed, f"Gate 2 failed: {gate2.missing_fields} {gate2.skip_violations} {gate2.screenshot_errors}"

    # 4. Print Generated Code for Critical Steps
    print("\n--- 2. DETAILED GENERATED SPEC CODE AUDIT ---")

    def print_step_block(sid: str):
        pat_str = r"(// -+\s*\n\s*// " + re.escape(sid) + r":[\s\S]*?\n\s*\}\);\n)"
        pattern = re.compile(pat_str, re.MULTILINE)
        m = pattern.search(spec_code)
        if m:
            print(f"\n[Generated Code Block: {sid}]")
            for line in m.group(1).splitlines():
                print(f"  {line}")
        else:
            print(f"[ERROR] Could not find code block for {sid}")

    # Steps 9, 10, 11, 12
    print_step_block("TS1-S09")
    print_step_block("TS1-S10")
    print_step_block("TS1-S11")
    print_step_block("TS1-S12")

    # 5. NEGATIVE AUDITS ON COVERAGE GATE 2
    print("\n" + "=" * 85)
    print("--- 3. NEGATIVE MUTATION AUDITS ON COVERAGE GATE 2 ---")

    # Mutation A: Injected .skip()
    mut_session_a = copy.deepcopy(session)
    mut_session_a.generated_spec_code = spec_code.replace("await test.step('TS1-S09", "await test.step.skip('TS1-S09")
    report_a = check_plan_to_spec(mut_session_a)
    print(f"\n[Mutation A: Injected test.step.skip() into Step 9]")
    print(f"  Gate 2 Passed:   {report_a.passed} (Expected: False)")
    print(f"  Skip Violations: {report_a.skip_violations}")
    assert not report_a.passed, "Gate 2 should have caught injected .skip()"
    assert len(report_a.skip_violations) > 0
    print("  [PASS] Mutation A Detected: Gate 2 caught forbidden .skip() pattern!")

    # Mutation B: Missing Field Action (remove TS1-S09-F14 Fax from code)
    mut_session_b = copy.deepcopy(session)
    mut_session_b.generated_spec_code = re.sub(r'// \[FIELD:TS1-S09-F14\].*?\n.*?;\n', '', spec_code)
    report_b = check_plan_to_spec(mut_session_b)
    print(f"\n[Mutation B: Removed Field Action Tag TS1-S09-F14 (Fax)]")
    print(f"  Gate 2 Passed:  {report_b.passed} (Expected: False)")
    print(f"  Missing Fields: {report_b.missing_fields}")
    assert not report_b.passed, "Gate 2 should have caught missing field TS1-S09-F14"
    assert any("TS1-S09-F14" in mf for mf in report_b.missing_fields)
    print("  [PASS] Mutation B Detected: Gate 2 caught missing field tag TS1-S09-F14!")

    # Mutation C: Missing Screenshot Checkpoint (remove capture calls from Step 4)
    mut_session_c = copy.deepcopy(session)
    # Remove captureModalEvidence for Step 4
    mut_session_c.generated_spec_code = spec_code.replace("await captureModalEvidence(page, 'TS1-S04_modal');", "").replace("await captureFormState(page, 'TS1-S04_form');", "")
    report_c = check_plan_to_spec(mut_session_c)
    print(f"\n[Mutation C: Removed Screenshot Checkpoints from Step 4]")
    print(f"  Gate 2 Passed:     {report_c.passed} (Expected: False)")
    print(f"  Screenshot Errors: {report_c.screenshot_errors}")
    assert not report_c.passed, "Gate 2 should have caught missing screenshot call in Step 4"
    assert any("TS1-S04" in se for se in report_c.screenshot_errors)
    print("  [PASS] Mutation C Detected: Gate 2 caught missing screenshot checkpoint in Step 4!")

    print("\n" + "=" * 85)
    print("🎉 ALL PHASE 3 VERIFICATIONS & NEGATIVE AUDITS PASSED WITH 100% SUCCESS!")
    print("=" * 85)

if __name__ == "__main__":
    run_phase3_verification()
