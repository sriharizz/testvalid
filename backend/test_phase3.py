import os
import pytest
import asyncio
from pathlib import Path
import docx
from extractor import extract_protocol
from playwright_runner import PlaywrightRunner
from docx_writer import DocxWriter

UPLOADS_DIR = Path(__file__).resolve().parent / "uploads"
ARTIFACTS_DIR = Path(__file__).resolve().parent / "artifacts"
SCREENSHOTS_DIR = ARTIFACTS_DIR / "screenshots"

@pytest.mark.asyncio
async def test_phase3_live_playwright_pass_and_docx_writer():
    pq_path = UPLOADS_DIR / "CLIN-EU-PAT-OPV-1-1-PQ-022- Manual - Registering Adverse Event Case.docx"
    assert pq_path.exists()

    session = extract_protocol(str(pq_path))
    # Execute first 4 key steps (Login URL, Authenticate, Navigate MCR, Register Case)
    session.steps = session.steps[:4]

    frames_received = []
    async def mock_ws(event):
        if event.get("type") == "FRAME":
            frames_received.append(event)

    runner = PlaywrightRunner(base_url="https://mpv-two.vercel.app", headless=True)
    executed_session = await runner.run_protocol(
        session=session,
        sim_mode="PASS",
        ws_callback=mock_ws
    )

    # 1. Assert all 4 steps passed
    for step in executed_session.steps:
        assert step.status == "PASS", f"Step {step.step_id} failed: {step.observed_result}"
        assert step.pass_fail_text == "Pass"
        assert step.latency_ms is not None and step.latency_ms > 0
        if step.screenshot_required:
            assert step.screenshot_url is not None
            # Check file exists on disk
            rel_path = step.screenshot_url[5:] if step.screenshot_url.startswith("/api/") else step.screenshot_url
            ss_path = ARTIFACTS_DIR.parent / rel_path
            assert ss_path.exists(), f"Screenshot file missing at {ss_path}"

    assert len(frames_received) > 0, "Fast JPEG viewport streaming failed to emit frames"
    print(f"[PASS] Playwright live execution succeeded for 4 steps, {len(frames_received)} live frames streamed.")

    # 2. Assert Lossless DocxWriter generates valid executed document
    out_file = DocxWriter.populate_executed_docx(
        session=executed_session,
        source_docx_path=str(pq_path),
        output_filename="test_executed_PQ-022.docx"
    )
    assert Path(out_file).exists()

    # 3. Read back output docx and assert populated cells & embedded image
    doc = docx.Document(out_file)
    exec_table = doc.tables[5]
    row4 = exec_table.rows[2]  # First data row
    
    # Assert Column 4 has Pass
    assert "Pass" in row4.cells[4].text
    # Assert Column 5 has initials and image
    assert "S.H." in row4.cells[5].text
    # Check that image blip XML is present in cell 5
    has_image = bool(row4.cells[5]._tc.xpath('.//a:blip') or row4.cells[5]._tc.xpath('.//a:graphic'))
    assert has_image is True, "Embedded image blip XML not found in Column 5!"

    print("[PASS] DocxWriter populated executed .docx with bold 'Pass' and embedded screenshot thumbnail.")

@pytest.mark.asyncio
async def test_phase3_simulation_mode_blocked():
    pq_path = UPLOADS_DIR / "CLIN-EU-PAT-OPV-1-1-PQ-022- Manual - Registering Adverse Event Case.docx"
    session = extract_protocol(str(pq_path))
    session.steps = session.steps[:5]  # Steps 1 to 5

    runner = PlaywrightRunner(base_url="https://mpv-two.vercel.app", headless=True)
    executed_session = await runner.run_protocol(
        session=session,
        sim_mode="BLOCKED"
    )

    # Step 1, 2, 3 should PASS
    assert executed_session.steps[0].status == "PASS"
    assert executed_session.steps[1].status == "PASS"
    assert executed_session.steps[2].status == "PASS"

    # Step 4 (TS1-S04) should be BLOCKED (503 lock)
    assert executed_session.steps[3].status == "BLOCKED"
    assert "503" in executed_session.steps[3].observed_result

    # Step 5 (TS1-S05) should be cascade-BLOCKED
    assert executed_session.steps[4].status == "BLOCKED"
    assert "halted" in executed_session.steps[4].observed_result.lower()
    print("[PASS] BLOCKED mode correctly halts at TS1-S04 with 503 Environment Control Lock.")

@pytest.mark.asyncio
async def test_phase3_simulation_mode_fail():
    pq_path = UPLOADS_DIR / "CLIN-EU-PAT-OPV-1-1-PQ-022- Manual - Registering Adverse Event Case.docx"
    session = extract_protocol(str(pq_path))
    session.steps = session.steps[:4]  # Steps 1 to 4

    runner = PlaywrightRunner(base_url="https://mpv-two.vercel.app", headless=True)
    executed_session = await runner.run_protocol(
        session=session,
        sim_mode="FAIL"
    )

    # Step 4 should detect application defect and mark FAIL
    assert executed_session.steps[3].status == "FAIL"
    assert "Assertion Failed" in executed_session.steps[3].observed_result
    assert executed_session.steps[3].error_detail is not None
    print("[PASS] FAIL mode correctly triggers application defect detection on TS1-S04.")

if __name__ == "__main__":
    pytest.main(["-v", __file__])
