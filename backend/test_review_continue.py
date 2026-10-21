import asyncio
import threading
from pathlib import Path
from extractor import extract_protocol
from playwright_runner import PlaywrightRunner

UPLOADS_DIR = Path(__file__).resolve().parent / "uploads"

async def test_human_review_continuation():
    print("Testing Human Review Acknowledge & Continue flow...")
    
    pq_path = UPLOADS_DIR / "CLIN-EU-PAT-OPV-1-1-PQ-022- Manual - Registering Adverse Event Case.docx"
    session = extract_protocol(str(pq_path))
    
    # We will test first 3 steps:
    # Step 1: NAVIGATE_LOGIN (Pass)
    # Step 2: Injected intentional discrepancy (triggers Human Review Gate)
    # Step 3: NAVIGATE_LOGIN (Continues and passes after reviewer acknowledges)
    
    # Set step 2 to REGISTER_CASE while still on login page -> triggers element timeout error
    session.steps[1].action_intent = "REGISTER_CASE"
    
    # Set step 3 to NAVIGATE_LOGIN so it can cleanly run
    session.steps[2].action_intent = "NAVIGATE_LOGIN"
    
    approval_event = threading.Event()
    halt_flag = False
    review_prompted = False

    async def ws_cb(msg):
        nonlocal review_prompted
        if msg.get("type") == "HUMAN_REVIEW_REQUIRED":
            print(f"  [Gate Triggered] {msg.get('step_id')}: {msg.get('reason')}")
            review_prompted = True
            # Simulate human reviewer reviewing discrepancy and clicking 'Acknowledge Discrepancy & Continue'
            await asyncio.sleep(0.5)
            print("  [Reviewer Action] Reviewer clicked 'Acknowledge Discrepancy & Continue'")
            approval_event.set()

    runner = PlaywrightRunner(base_url="https://mpv-two.vercel.app", headless=True)
    
    await runner.run_protocol(
        session=session,
        requires_approval=False,
        approval_event=approval_event,
        ws_callback=ws_cb,
        is_halt_requested=lambda: halt_flag,
        max_steps=3
    )
    
    print("\n--- RESULTS AUDIT ---")
    print(f"Review Gate Triggered: {review_prompted}")
    print(f"Step 1 Status: {session.steps[0].status} (Expected: PASS)")
    print(f"Step 2 Status: {session.steps[1].status} (Expected: FAIL - preserved for audit integrity)")
    print(f"Step 2 Observed: {session.steps[1].observed_result}")
    print(f"Step 3 Status: {session.steps[2].status} (Expected: PASS - continued automatically!)")
    
    assert review_prompted, "Human review gate was not triggered!"
    assert session.steps[0].status == "PASS"
    assert session.steps[1].status == "FAIL", "Step 2 must remain FAIL for GxP audit compliance!"
    assert "Reviewer Acknowledged: Continued test execution" in (session.steps[1].observed_result or "")
    assert session.steps[2].status == "PASS", "Step 3 should have executed and passed after continuation!"
    print("\n[SUCCESS] Human Review Acknowledge & Continue flow verified with 100% GxP integrity!")

if __name__ == "__main__":
    asyncio.run(test_human_review_continuation())
