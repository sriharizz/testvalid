import sys
import asyncio
import datetime
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from playwright.async_api import async_playwright
from schemas import ProtocolStep, ExtractedFieldSpec
from aria_compiler import bind_step_with_live_dom, extract_visible_dom_controls

HTML_CONTENT = """<!DOCTYPE html>
<html>
<head><title>Conditional Clinical Sub-Form</title></head>
<body>
  <h2>Adverse Event Hospitalization Registration</h2>
  <form id="clinical_form">
    <div>
      <label for="seriousness">Seriousness</label>
      <select id="seriousness" onchange="document.getElementById('hosp_box').style.display = (this.value === 'Serious') ? 'block' : 'none';">
        <option value="">Select</option>
        <option value="Serious">Serious</option>
        <option value="Non-Serious">Non-Serious</option>
      </select>
    </div>
    <div id="hosp_box" style="display:none">
      <label for="adm_date">Hospitalization Admission Date *</label>
      <input id="adm_date" type="date" required>
    </div>
    <div>
      <label for="pat_init">Patient Initials *</label>
      <input id="pat_init" type="text" required>
    </div>
    <div>
      <label for="rep_type">Reporter Type *</label>
      <select id="rep_type" required>
        <option value="">Select</option>
        <option value="HCP">HCP</option>
        <option value="CON">Consumer</option>
      </select>
    </div>
  </form>
</body>
</html>
"""

async def run_phase3_verification():
    print("=== PHASE 3 VERIFICATION: MODE 1 GUIDED LIVE-DOM MICRO-AGENT & MUTATION LOOP ===")

    tomorrow_iso = (datetime.date.today() + datetime.timedelta(days=1)).isoformat()

    step = ProtocolStep(
        step_id="TS3-S07",
        test_set_no=3,
        step_number_display="7",
        table_index=2,
        row_index=7,
        scenario="Negative Future Hospitalization Admission Date",
        procedure="Navigate to Case Intake. Pick 'Serious' for seriousness—this opens the hospitalization sub-section. Set admission date to a future date (tomorrow), fill all other mandatory patient & reporter fields with valid dummy data, choose 'Physician' as reporter type, and try to Save. (µ)",
        expected_result="System should block registration and show an error alert that Admission Date cannot be in the future.",
        action_intent="FORM_ENTRY",
        primary_section="event",
        extracted_fields=[
            ExtractedFieldSpec(
                field_id="TS3-S07-F01",
                section="event",
                label="Seriousness",
                control_type="select",
                explicit_value="Serious"
            ),
            ExtractedFieldSpec(
                field_id="TS3-S07-F02",
                section="event",
                label="Admission Date",
                control_type="date",
                explicit_value="TODAY+1"
            ),
            ExtractedFieldSpec(
                field_id="TS3-S07-F03",
                section="reporter",
                label="Reporter Type",
                control_type="select",
                explicit_value="Physician"
            )
        ],
        cpu_parse_confidence=0.45,
        needs_mode1_discovery=True
    )

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.set_content(HTML_CONTENT)

        # 1. Initial DOM check: #adm_date must be hidden
        initial_ctrls = await extract_visible_dom_controls(page)
        initial_selectors = {c["selector"] for c in initial_ctrls}
        print(f"[Check 0] Initial visible controls: {initial_selectors}")
        assert "#adm_date" not in initial_selectors, "Hospitalization Admission Date should be hidden initially"

        # 2. Run Mode 1 Live-DOM Guided Micro-Agent
        applied_records = await bind_step_with_live_dom(page, step)
        print(f"[Check 1] Total applied input records: {len(applied_records)}")
        for rec in applied_records:
            print(f"  -> {rec.field_label} ({rec.selector_used}): '{rec.value_applied}' [provenance={rec.provenance}, orig={rec.original_term}]")

        rec_map = {r.selector_used: r for r in applied_records}

        # Check 1: Seriousness applied with protocol_explicit
        assert "#seriousness" in rec_map, "Missing #seriousness in applied records"
        r_ser = rec_map["#seriousness"]
        assert r_ser.value_applied == "Serious"
        assert r_ser.provenance == "protocol_explicit"
        print("[PASS] Check 1: Seriousness applied correctly (protocol_explicit)")

        # Check 2: DOM mutation revealed #adm_date and applied tomorrow_iso with computed_dynamic
        assert "#adm_date" in rec_map, "Missing #adm_date in applied records after DOM mutation"
        r_adm = rec_map["#adm_date"]
        assert r_adm.value_applied == tomorrow_iso
        assert r_adm.provenance == "computed_dynamic"
        print(f"[PASS] Check 2: Admission Date revealed via mutation & filled {tomorrow_iso} (computed_dynamic)")

        # Check 3: Reporter Type mapped Physician -> HCP with cpu_semantic_match
        assert "#rep_type" in rec_map, "Missing #rep_type in applied records"
        r_rep = rec_map["#rep_type"]
        assert r_rep.value_applied == "HCP"
        assert r_rep.provenance in ["cpu_semantic_match", "ai_mapped_synonym"]
        assert r_rep.original_term == "Physician"
        print("[PASS] Check 3: Reporter Type mapped Physician -> HCP (cpu_semantic_match)")

        # Check 4: Mandatory Patient Initials dummy data synthesized
        assert "#pat_init" in rec_map, "Missing mandatory #pat_init in applied records"
        r_pat = rec_map["#pat_init"]
        assert len(r_pat.value_applied) > 0
        assert r_pat.provenance == "ai_synthesized_mandatory"
        print(f"[PASS] Check 4: Mandatory Patient Initials synthesized '{r_pat.value_applied}' (ai_synthesized_mandatory)")

        # Check 5: Live DOM readback verification directly from the page elements
        live_ser = await page.locator("#seriousness").input_value()
        live_adm = await page.locator("#adm_date").input_value()
        live_rep = await page.locator("#rep_type").input_value()
        live_pat = await page.locator("#pat_init").input_value()

        print(f"[Check 5] Live DOM readbacks: seriousness='{live_ser}', adm_date='{live_adm}', rep_type='{live_rep}', pat_init='{live_pat}'")
        assert live_ser == "Serious"
        assert live_adm == tomorrow_iso
        assert live_rep == "HCP"
        assert len(live_pat) > 0
        print("[PASS] Check 5: Live DOM readback verified across all 4 form controls")

        await browser.close()

    print("[PASS] PHASE 3 VERIFICATION COMPLETE!")

if __name__ == "__main__":
    asyncio.run(run_phase3_verification())
