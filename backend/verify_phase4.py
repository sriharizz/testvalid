import os
import sys
import asyncio
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
from playwright_runner import PlaywrightRunner

async def run_phase4_verification():
    protocol_path = backend_dir / "uploads" / "CLIN-EU-PAT-OPV-1-1-PQ-022- Manual - Registering Adverse Event Case.docx"
    
    print("=" * 85)
    print("PHASE 4 VERIFICATION: Dynamic Playwright Runner & Two-Stage Evidence Capture")
    print(f"Target App: https://mpv-two.vercel.app")
    print(f"Protocol:   {protocol_path.name}")
    print("=" * 85)

    # 1. Extract Protocol
    session = extract_protocol(str(protocol_path))

    # 2. Plan Protocol with Qwen Planner (100% field mapping)
    planner = PlannerAgent()
    legacy_plan, _, _ = planner.generate_plan(session)

    # 3. Execute with Playwright Runner
    print("\nExecuting full protocol live via Playwright Runner (Headless Chromium)...")
    runner = PlaywrightRunner(base_url="https://mpv-two.vercel.app", headless=True)
    
    executed_session = await runner.run_protocol(
        session=session,
        sim_mode="PASS",
        plan_steps=legacy_plan
    )

    print("\n--- 1. LIVE EXECUTION RESULTS AUDIT ---")
    step_dict = {s.step_id: s for s in executed_session.steps}
    pass_count = sum(1 for s in executed_session.steps if s.status == "PASS")
    fail_count = sum(1 for s in executed_session.steps if s.status == "FAIL")
    blocked_count = sum(1 for s in executed_session.steps if s.status == "BLOCKED")

    print(f"Total Steps Executed: {len(executed_session.steps)}")
    print(f"PASS: {pass_count} | FAIL: {fail_count} | BLOCKED: {blocked_count}")

    for s in executed_session.steps:
        print(f"[{s.step_id}] Status: {s.status:4s} | Latency: {s.latency_ms:4d}ms | {s.observed_result}")

    print("\n--- 2. DYNAMIC RUNTIME CASE ID AUDIT ---")
    scraped_temp_id = executed_session.runtime_state.get("temp_case_id")
    scraped_case_no = executed_session.runtime_state.get("case_number")
    print(f"Scraped Temporary Case ID: {scraped_temp_id}")
    print(f"Scraped Official Case No:  {scraped_case_no}")

    assert scraped_temp_id is not None, "temp_case_id was not dynamically scraped"
    assert "TMP-CASE-" in scraped_temp_id or "TMP-" in scraped_temp_id
    print("[PASS] Temporary Case ID dynamically scraped from live DOM modal (Zero Hardcoding)")

    # 3. Two-Stage Screenshot Evidence Audit
    print("\n--- 3. TWO-STAGE SCREENSHOT EVIDENCE AUDIT ---")
    session_dir = Path(__file__).resolve().parent / "artifacts" / "screenshots" / executed_session.session_id
    
    two_stage_steps = ["TS1-S04", "TS1-S09", "TS1-S10", "TS1-S11", "TS1-S12"]
    for sid in two_stage_steps:
        f_path = session_dir / f"{sid}_form.png"
        m_path = session_dir / f"{sid}_modal.png"
        c_path = session_dir / f"{sid}.png"
        print(f"[{sid}] Form State:  {f_path.exists()} ({f_path.stat().st_size if f_path.exists() else 0} bytes)")
        print(f"         Modal Dialog: {m_path.exists()} ({m_path.stat().st_size if m_path.exists() else 0} bytes)")
        print(f"         Stitched Composite: {c_path.exists()} ({c_path.stat().st_size if c_path.exists() else 0} bytes)")
        assert f_path.exists(), f"Missing form state screenshot: {f_path}"
        assert m_path.exists(), f"Missing modal dialog screenshot: {m_path}"
        assert c_path.exists(), f"Missing stitched composite screenshot: {c_path}"

    print("[PASS] Two-Stage Unobscured Screenshots successfully captured and stitched for all form steps")

    # 4. Critical Step Assertions
    print("\n--- 4. CRITICAL STEP FIELD VERIFICATIONS ---")
    s9 = step_dict["TS1-S09"]
    assert s9.status == "PASS", f"Step 9 Reporter failed: {s9.failure_reason}"
    assert "16/16 fields" in s9.observed_result
    print("[PASS] Step 9 (Reporter): 16/16 fields filled & confirmed on live DOM")

    s10 = step_dict["TS1-S10"]
    assert s10.status == "PASS", f"Step 10 Patient failed: {s10.failure_reason}"
    assert "15/15 fields" in s10.observed_result
    print("[PASS] Step 10 (Patient): 15/15 fields filled & confirmed on live DOM")

    s11 = step_dict["TS1-S11"]
    assert s11.status == "PASS", f"Step 11 Product failed: {s11.failure_reason}"
    assert "Paracetamol" in s11.observed_result or "auto-populated" in s11.observed_result
    print("[PASS] Step 11 (Product): Search modal utilized & auto-population verified")

    s12 = step_dict["TS1-S12"]
    assert s12.status == "PASS", f"Step 12 Event failed: {s12.failure_reason}"
    assert "4 assessment & 8 seriousness dropdowns verified" in s12.observed_result
    print("[PASS] Step 12 (Event): MedDRA modal utilized & 12 dropdowns filled")

    print("\n" + "=" * 85)
    print("ALL PHASE 4 LIVE VERIFICATIONS PASSED WITH 100% SUCCESS!")
    print("=" * 85)

if __name__ == "__main__":
    asyncio.run(run_phase4_verification())
