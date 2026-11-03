import sys
import inspect
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import agents
import aria_compiler
import playwright_runner
from schemas import ProtocolSession, ProtocolStep, AppliedInputRecord, ExtractedFieldSpec
from aria_compiler import PlanCacheManager

def test_no_hardcoded_synonyms_in_runner():
    print("[Test 1] Checking playwright_runner.py for legacy hardcoded synonym dicts...")
    src = inspect.getsource(playwright_runner.safe_select_option)
    assert "synonyms.update" not in src, "SHORTCUT DETECTED: legacy synonyms.update still inside safe_select_option!"
    assert "match_dropdown_option" in src, "SHORTCUT DETECTED: match_dropdown_option is not called inside safe_select_option!"
    print("  -> PASS: safe_select_option uses match_dropdown_option with zero legacy synonym dicts.")

def test_planner_sends_raw_procedure_prose():
    print("[Test 2] Checking PlannerAgent.query_qwen_single_batch sends raw procedure prose...")
    src = inspect.getsource(agents.PlannerAgent.query_qwen_single_batch)
    assert '"procedure"' in src or "'procedure'" in src, "SHORTCUT DETECTED: query_qwen_single_batch does not send raw step procedure text!"
    print("  -> PASS: PlannerAgent sends raw procedure & expected_result prose to Qwen.")

def test_live_dom_cache_writeback():
    print("[Test 3] Checking PlanCacheManager.update_cache_with_verified_dom_inputs write-back...")
    assert hasattr(PlanCacheManager, "update_cache_with_verified_dom_inputs"), "SHORTCUT DETECTED: update_cache_with_verified_dom_inputs missing!"

    step = ProtocolStep(
        step_id="TS1-S09",
        step_number_display="9",
        table_index=0,
        row_index=9,
        scenario="Reporter Info",
        procedure="Select Reporter Type code: (Select from dropdown)",
        expected_result="Reporter saved",
        action_intent="FORM_ENTRY",
        primary_section="reporter",
        extracted_fields=[
            ExtractedFieldSpec(
                field_id="TS1-S09-F01",
                section="reporter",
                label="Reporter Type code",
                raw_instruction="(Select from dropdown)",
                control_type="select",
                explicit_value=None
            )
        ],
        applied_inputs=[
            AppliedInputRecord(
                field_label="Reporter Type code",
                selector_used="#reporter_type",
                value_applied="Physician",
                original_term="HCP",
                provenance="cpu_semantic_match",
                readback_verified=True
            )
        ]
    )
    session = ProtocolSession(
        session_id="test_wb_01",
        product_id="onepv",
        filename="test_wb.docx",
        document_no="TEST-WB-001",
        version="1.0",
        effective_date="01-Nov-2026",
        title="Writeback Test",
        objective="Test",
        scope="Test",
        steps=[step]
    )
    # Compile initial plan (will have default/synthesized value)
    initial_plan = PlanCacheManager.compile_session_plan(session)
    PlanCacheManager.save_plan_to_cache("onepv", initial_plan)

    # Now trigger post-execution live-DOM writeback
    PlanCacheManager.update_cache_with_verified_dom_inputs(session)

    # Reload from disk cache and verify 'Physician' is now locked!
    reloaded = PlanCacheManager.get_cached_plan("onepv", initial_plan.protocol_sha256)
    assert reloaded is not None
    locked_val = reloaded.steps[0].compiled_fields[0].target_value
    assert locked_val == "Physician", f"Expected locked cache value 'Physician', got '{locked_val}'"
    print(f"  -> PASS: PlanCacheManager locked live-DOM value '{locked_val}' onto disk for 0-token Warm Start replay!")

async def test_live_dom_dynamic_mutation_binding():
    print("[Test 4] Checking live Chromium DOM snapshotter & dynamic mutation binding...")
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.set_content("""
        <html><body>
          <form id="case_form">
            <label for="seriousness">Seriousness *</label>
            <select id="seriousness" required onchange="document.getElementById('hosp_div').style.display = (this.value === 'Serious' ? 'block' : 'none')">
              <option value="">Select</option>
              <option value="Serious">Serious</option>
              <option value="Non-Serious">Non-Serious</option>
            </select>
            <div id="hosp_div" style="display:none;">
              <label for="adm_date">Hospitalization Admission Date *</label>
              <input id="adm_date" type="date" required />
            </div>
          </form>
        </body></html>
        """)
        ctrls_before = await aria_compiler.extract_visible_dom_controls(page)
        labels_before = [c["label"] for c in ctrls_before]
        assert "Hospitalization Admission Date" not in labels_before, "Hidden field should not be in initial visible snapshot!"

        await page.select_option("#seriousness", "Serious")
        await page.wait_for_timeout(100)
        ctrls_after = await aria_compiler.extract_visible_dom_controls(page)
        labels_after = [c["label"] for c in ctrls_after]
        assert "Hospitalization Admission Date" in labels_after, "Newly revealed field must appear in post-mutation snapshot!"
        await browser.close()
    print("  -> PASS: Dynamic DOM mutation reveal verified in live Chromium!")

def main():
    print("=================================================================")
    print("   ANTI-SHORTCUT & LIVE-DOM WRITEBACK VERIFICATION SUITE (v4.1)")
    print("=================================================================")
    test_no_hardcoded_synonyms_in_runner()
    test_planner_sends_raw_procedure_prose()
    test_live_dom_cache_writeback()
    asyncio.run(test_live_dom_dynamic_mutation_binding())
    print("=================================================================")
    print("   ALL 4 ANTI-SHORTCUT CHECKS 100% PASSED!")
    print("=================================================================")

if __name__ == "__main__":
    main()
