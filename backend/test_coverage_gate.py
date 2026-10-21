import os
import json
import pytest
import time
from pathlib import Path
from extractor import extract_protocol
from check_coverage import CoverageChecker
from agents import PlannerAgent, PlaywrightGeneratorAgent, HealerAgent, compute_git_baseline

UPLOADS_DIR = Path(__file__).resolve().parent / "uploads"
ARTIFACTS_DIR = Path(__file__).resolve().parent / "artifacts"

@pytest.fixture(scope="module")
def setup_pipeline():
    pq_path = UPLOADS_DIR / "CLIN-EU-PAT-OPV-1-1-PQ-022- Manual - Registering Adverse Event Case.docx"
    dom_file = ARTIFACTS_DIR / "dom_map.json"
    
    with open(dom_file, "r", encoding="utf-8") as f:
        dom_map = json.load(f)
        
    session = extract_protocol(str(pq_path))
    planner = PlannerAgent(dom_map)
    plan_steps, md_plan, plan_latency = planner.generate_plan(session)
    
    generator = PlaywrightGeneratorAgent(dom_map)
    spec_code, gen_latency = generator.generate_spec(session, plan_steps)
    spec_code = HealerAgent.verify_and_heal_selectors(spec_code, dom_map)
    
    return session, plan_steps, spec_code, dom_map

def test_1_positive_coverage_gates(setup_pipeline):
    """Test 1 (Positive): Valid 18-step protocol, plan, and .spec.ts pass Gate 1 and Gate 2 (< 50ms)"""
    session, plan_steps, spec_code, _ = setup_pipeline
    
    t0 = time.time()
    gate1_res = CoverageChecker.verify_protocol_to_plan(session.steps, plan_steps)
    gate1_latency_ms = (time.time() - t0) * 1000
    
    assert gate1_res["passed"] is True, f"Gate 1 failed: {gate1_res['violations']}"
    assert gate1_res["total_protocol_steps"] == 18
    assert gate1_res["mapped_plan_steps"] == 18
    assert gate1_res["order_verified"] is True
    assert gate1_latency_ms < 50, f"Gate 1 took {gate1_latency_ms:.2f}ms, expected < 50ms"
    
    t1 = time.time()
    gate2_res = CoverageChecker.verify_plan_to_playwright_code(plan_steps, spec_code)
    gate2_latency_ms = (time.time() - t1) * 1000
    
    assert gate2_res["passed"] is True, f"Gate 2 failed: {gate2_res['violations']}"
    assert gate2_res["total_plan_steps"] == 18
    assert gate2_res["verified_code_steps"] == 18
    assert gate2_res["order_verified"] is True
    assert gate2_latency_ms < 50, f"Gate 2 took {gate2_latency_ms:.2f}ms, expected < 50ms"
    print(f"[PASS] Test 1: Positive verification passed in {gate1_latency_ms+gate2_latency_ms:.2f}ms")

def test_2_negative_missing_step_id(setup_pipeline):
    """Test 2 (Negative — Missing Step ID): Dropping TS1-S04 fails Gate 1 & Gate 2"""
    session, plan_steps, spec_code, _ = setup_pipeline
    
    # Drop TS1-S04 from plan
    corrupted_plan = [p for p in plan_steps if p["step_id"] != "TS1-S04"]
    gate1_res = CoverageChecker.verify_protocol_to_plan(session.steps, corrupted_plan)
    assert gate1_res["passed"] is False
    assert "TS1-S04" in gate1_res["missing_step_ids"]
    
    # Gate 2 with TS1-S04 dropped from spec_code
    corrupted_spec = spec_code.replace("await test.step('TS1-S04'", "// dropped TS1-S04")
    gate2_res = CoverageChecker.verify_plan_to_playwright_code(plan_steps, corrupted_spec)
    assert gate2_res["passed"] is False
    assert "TS1-S04" in gate2_res["missing_step_blocks"]
    print("[PASS] Test 2: Missing Step ID correctly detected and rejected by Gate 1 & Gate 2")

def test_3_negative_reordered_steps(setup_pipeline):
    """Test 3 (Negative — Reordered Steps): Swapping TS1-S04 and TS1-S05 fails sequence check"""
    session, plan_steps, spec_code, _ = setup_pipeline
    
    corrupted_plan = list(plan_steps)
    # Find indices
    idx4 = next(i for i, p in enumerate(corrupted_plan) if p["step_id"] == "TS1-S04")
    idx5 = next(i for i, p in enumerate(corrupted_plan) if p["step_id"] == "TS1-S05")
    corrupted_plan[idx4], corrupted_plan[idx5] = corrupted_plan[idx5], corrupted_plan[idx4]
    
    gate1_res = CoverageChecker.verify_protocol_to_plan(session.steps, corrupted_plan)
    assert gate1_res["passed"] is False
    assert gate1_res["order_verified"] is False
    print("[PASS] Test 3: Reordered steps correctly detected and rejected by Gate 1")

def test_4_negative_silent_skip(setup_pipeline):
    """Test 4 (Negative — Silent Skip): Adding test.skip() fails Gate 2"""
    session, plan_steps, spec_code, _ = setup_pipeline
    
    corrupted_spec = spec_code.replace(
        "await test.step('TS1-S04'",
        "test.skip('Skipping TS1-S04');\n  await test.step('TS1-S04'"
    )
    gate2_res = CoverageChecker.verify_plan_to_playwright_code(plan_steps, corrupted_spec)
    assert gate2_res["passed"] is False
    assert any("Forbidden" in v for v in gate2_res["violations"])
    print("[PASS] Test 4: Silent test.skip() correctly detected and rejected by Gate 2")

def test_5_negative_weakened_assertion(setup_pipeline):
    """Test 5 (Negative — Weakened Assertion): Removing an expect() in a multi-assertion step fails Gate 2"""
    session, plan_steps, spec_code, _ = setup_pipeline
    
    # Require 3 assertions for TS1-S02 in plan
    multi_step_plan = []
    for p in plan_steps:
        copy_p = dict(p)
        if copy_p["step_id"] == "TS1-S02":
            copy_p["required_assertions_count"] = 5  # Higher than spec's expects
        multi_step_plan.append(copy_p)
        
    gate2_res = CoverageChecker.verify_plan_to_playwright_code(multi_step_plan, spec_code)
    assert gate2_res["passed"] is False
    assert any("TS1-S02" in v and "Required assertions" in v for v in gate2_res["assertion_violations"])
    print("[PASS] Test 5: Weakened assertion correctly detected and rejected by Gate 2")

def test_6_negative_missing_mu_evidence(setup_pipeline):
    """Test 6 (Negative — Missing µ Evidence): Removing captureEvidence(page, 'TS1-S04') fails Gate 2"""
    session, plan_steps, spec_code, _ = setup_pipeline
    
    corrupted_spec = spec_code.replace("await captureEvidence(page, 'TS1-S04');", "// removed evidence")
    gate2_res = CoverageChecker.verify_plan_to_playwright_code(plan_steps, corrupted_spec)
    assert gate2_res["passed"] is False
    assert any("TS1-S04" in v and "Screenshot required" in v for v in gate2_res["screenshot_violations"])
    print("[PASS] Test 6: Missing µ Evidence capture correctly detected and rejected by Gate 2")

if __name__ == "__main__":
    pytest.main(["-v", __file__])
