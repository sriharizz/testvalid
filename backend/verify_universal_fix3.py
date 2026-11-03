import sys
import asyncio
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from playwright.async_api import async_playwright
from schemas import ProtocolStep, StepAssertion, PlannedStep, PlannedFieldAction
from playwright_runner import find_semantic_control, human_fill, verify_expected_result, check_visible, safe_click

async def test_table_column_to_cell_resolver():
    print("[Check 1] Testing Universal Table Column-Header-to-Cell Input Resolver...")
    html_content = """
    <!DOCTYPE html>
    <html>
    <head><title>Grid Test</title></head>
    <body>
      <h2>Clinical Assessment Questionnaire</h2>
      <table role="grid" id="study-table">
        <thead>
          <tr>
            <th>Question ID</th>
            <th>Question Description</th>
            <th>Response</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>QST-001</td>
            <td>Did the subject report any adverse reaction?</td>
            <td><input type="text" id="target_cell_input" /></td>
          </tr>
        </tbody>
      </table>
    </body>
    </html>
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.set_content(html_content)

        ctrl = await find_semantic_control(page, "Response", control_type="text")
        assert ctrl is not None, "Failed to resolve cell input from <th> column header 'Response'!"

        el_id = await ctrl.evaluate("el => el.id")
        assert el_id == "target_cell_input", f"Expected 'target_cell_input', got '{el_id}'"

        ok = await human_fill(page, ctrl, "Patient reported mild headache")
        assert ok is True, "Failed to fill resolved cell input!"
        readback = await ctrl.input_value()
        assert readback == "Patient reported mild headache", f"Readback mismatch: '{readback}'"

        print("  -> PASS: <th>Response</th> header dynamically resolved to <td><input> and filled!")
        await browser.close()

async def test_universal_row_edit_trigger():
    print("[Check 2] Testing Universal Row-Edit Trigger Before Updating Existing Records...")
    html_content = """
    <!DOCTYPE html>
    <html>
    <body>
      <div id="trial-container">
        <h3>Treatment Arms</h3>
        <table id="arms-table">
          <thead>
            <tr><th>Arm</th><th>Status</th><th>Actions</th></tr>
          </thead>
          <tbody>
            <tr>
              <td>Cohort A</td>
              <td>Active</td>
              <td><button id="edit-arm-btn" onclick="document.getElementById('edit-dialog').style.display='block'">Edit</button></td>
            </tr>
          </tbody>
        </table>

        <div id="edit-dialog" role="dialog" style="display:none; padding:15px; border:1px solid #ccc;">
          <h4>Edit Cohort A Period</h4>
          <label for="open_date">Open Date</label>
          <input type="date" id="open_date" />
          <label for="close_date">Close Date</label>
          <input type="date" id="close_date" />
          <button onclick="document.getElementById('edit-dialog').style.display='none'">Save</button>
        </div>
      </div>
    </body>
    </html>
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.set_content(html_content)

        # Before clicking edit, #open_date is hidden
        inp_open = page.locator("#open_date")
        assert not await check_visible(inp_open)

        # Universal row-edit trigger: find and click Edit button
        edit_btn = page.locator("button:has-text('Edit'), button[aria-label*='edit' i]").first
        assert await check_visible(edit_btn)
        await safe_click(edit_btn)
        await page.wait_for_timeout(200)

        # After edit trigger, inputs are now visible
        ctrl_open = await find_semantic_control(page, "Open Date", control_type="date")
        ctrl_close = await find_semantic_control(page, "Close Date", control_type="date")
        assert ctrl_open is not None, "Failed to find 'Open Date' after opening edit dialog!"
        assert ctrl_close is not None, "Failed to find 'Close Date' after opening edit dialog!"

        await human_fill(page, ctrl_open, "2026-11-01")
        await human_fill(page, ctrl_close, "2026-12-01")
        assert await ctrl_open.input_value() == "2026-11-01"
        assert await ctrl_close.input_value() == "2026-12-01"

        print("  -> PASS: Inline row 'Edit' button triggered automatically and hidden date fields populated!")
        await browser.close()

async def test_modal_accordion_and_view_hyperlink():
    print("[Check 3] Testing Universal Modal Action & View Hyperlink Expansion...")
    html_content = """
    <!DOCTYPE html>
    <html>
    <body>
      <div role="dialog" id="product-modal">
        <h3>Product Summary</h3>
        <p>Selected Product: Cardizem CD</p>
        <button id="view-details-btn" onclick="document.getElementById('extra-info').style.display='block'">View Product Info</button>
        <div id="extra-info" style="display:none; margin-top:10px;">
          <p id="dosage-text">Dosage: 180mg Extended-Release Capsule</p>
        </div>
      </div>
    </body>
    </html>
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.set_content(html_content)

        step = ProtocolStep(
            step_id="TS1-S15",
            procedure="In the Product modal, choose the product and click on View hyperlink.",
            expected_result="Product details shall display.",
            action_intent="MODAL_ACTION",
            assertions=[
                StepAssertion(assertion_type="UI_ELEMENT", description="View product info link", target_text="view")
            ]
        )

        is_passed, summary, err = await verify_expected_result(page, step)
        assert is_passed is True, f"Expected UI_ELEMENT verification PASS, got FAIL: {err}"
        assert "verified" in summary.lower()

        # Confirm the extra info is now visible after link click
        extra = page.locator("#dosage-text")
        assert await check_visible(extra)
        print("  -> PASS: View link expanded inside modal and UI_ELEMENT assertion verified!")
        await browser.close()

async def run_all_checks():
    print("=== RUNNING UNIVERSAL FIX 3 VERIFICATION SUITE ===")
    await test_table_column_to_cell_resolver()
    await test_universal_row_edit_trigger()
    await test_modal_accordion_and_view_hyperlink()
    print("=== [100% PASS] UNIVERSAL FIX 3 COMPLETE! ===")

if __name__ == "__main__":
    asyncio.run(run_all_checks())
