import os
import sys
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

def run_phase1_verification():
    protocol_path = backend_dir / "uploads" / "CLIN-EU-PAT-OPV-1-1-PQ-022- Manual - Registering Adverse Event Case.docx"
    
    print("=" * 85)
    print("PHASE 1 VERIFICATION: Deep Protocol & Field Extractor Engine")
    print(f"Protocol: {protocol_path.name}")
    print("=" * 85)

    if not protocol_path.exists():
        print(f"ERROR: Protocol file not found at {protocol_path}")
        sys.exit(1)

    session = extract_protocol(str(protocol_path))

    print("\n--- 1. DOCUMENT METADATA ---")
    print(f"Document No:    {session.document_no}")
    print(f"Version:        {session.version}")
    print(f"Effective Date: {session.effective_date}")
    print(f"Title:          {session.title}")
    print(f"Objective:      {session.objective[:75]}...")
    print(f"Total Steps:    {session.total_steps}")
    print(f"Total (µ) Pts:  {session.total_screenshots}")

    print("\n--- 2. STEP-BY-STEP EXTRACTED FIELDS AUDIT ---")
    step_dict = {s.step_id: s for s in session.steps}
    
    total_fields_extracted = 0
    for s in session.steps:
        mu_indicator = "[µ CAPTURE]" if s.screenshot_required else "           "
        print(f"\n[{s.step_id}] {mu_indicator} [{s.primary_section.upper()}] Intent: {s.action_intent}")
        print(f"        Scenario: {s.scenario[:70]}")
        print(f"        Fields Extracted: {len(s.extracted_fields)}")
        total_fields_extracted += len(s.extracted_fields)
        for ef in s.extracted_fields:
            explicit_str = f" [explicit='{ef.explicit_value}']" if ef.explicit_value else ""
            auto_str = " [AUTO-POPULATE]" if ef.auto_populated else ""
            search_str = " [MODAL-SEARCH]" if ef.search_trigger_icon else ""
            print(f"          • {ef.field_id}: '{ef.label}' | Type: <{ef.control_type}> | Section: <{ef.section}>{explicit_str}{auto_str}{search_str}")

    print("\n" + "=" * 85)
    print("--- 3. PHASE 1 GxP SPECIFICATION ASSERTIONS ---")
    
    # Assertion 1: Total Steps
    assert session.total_steps == 18, f"Expected 18 steps, got {session.total_steps}"
    print("[PASS] Assertion 1: Total Steps = 18/18 Verified")

    # Assertion 2: Total Screenshots
    assert session.total_screenshots >= 18, f"Expected >= 18 screenshots, got {session.total_screenshots}"
    print(f"[PASS] Assertion 2: Total Screenshot Checkpoints = {session.total_screenshots} Verified")

    # Assertion 3: Step 4 (Register Case) -> 4 fields
    s4 = step_dict["TS1-S04"]
    assert len(s4.extracted_fields) == 4, f"Step 4 expected 4 fields, got {len(s4.extracted_fields)}"
    s4_labels = [f.label for f in s4.extracted_fields]
    assert "Case Classifications Code" in s4_labels
    assert "Case Intake Source Code" in s4_labels
    assert "Company Receipt Date" in s4_labels
    assert "Processing Center Received Date" in s4_labels
    assert s4.extracted_fields[0].explicit_value == "Adverse Event"
    print("[PASS] Assertion 3: Step 4 (Register Case) = 4/4 Fields Verified (Explicit Value: 'Adverse Event')")

    # Assertion 4: Step 5 (Add Questionnaire Manual) -> 2 fields
    s5 = step_dict["TS1-S05"]
    assert len(s5.extracted_fields) == 2, f"Step 5 expected 2 fields, got {len(s5.extracted_fields)}"
    s5_labels = [f.label for f in s5.extracted_fields]
    assert "Field Type" in s5_labels
    assert "Question" in s5_labels
    print("[PASS] Assertion 4: Step 5 (Add Questionnaire) = 2/2 Fields Verified ('Field Type', 'Question')")

    # Assertion 5: Step 6 (Respond Questionnaire) -> 1 field
    s6 = step_dict["TS1-S06"]
    assert len(s6.extracted_fields) == 1, f"Step 6 expected 1 field, got {len(s6.extracted_fields)}"
    assert s6.extracted_fields[0].label == "Response"
    print("[PASS] Assertion 5: Step 6 (Respond Questionnaire) = 1/1 Field Verified ('Response')")

    # Assertion 6: Step 9 (Add Reporter) -> 16 fields
    s9 = step_dict["TS1-S09"]
    assert len(s9.extracted_fields) == 16, f"Step 9 expected 16 fields, got {len(s9.extracted_fields)}"
    s9_labels = [f.label for f in s9.extracted_fields]
    expected_s9 = [
        "Title", "First Name", "Last Name", "Sex code", "Relationship With Patient Code",
        "Reporter Type code", "Is Reporter Health Care Professional", "Address1", "Address2",
        "City", "State", "Country code", "Zipcode", "Fax", "Contact Number", "Email Address"
    ]
    for exp in expected_s9:
        assert exp in s9_labels, f"Step 9 missing field: {exp}"
    assert any(f.control_type == "toggle" for f in s9.extracted_fields if f.label == "Is Reporter Health Care Professional")
    print("[PASS] Assertion 6: Step 9 (Add Reporter) = 16/16 Fields Verified (Including Toggle & Dropdowns)")

    # Assertion 7: Step 10 (Add Patient) -> 15 fields
    s10 = step_dict["TS1-S10"]
    assert len(s10.extracted_fields) == 15, f"Step 10 expected 15 fields, got {len(s10.extracted_fields)}"
    s10_labels = [f.label for f in s10.extracted_fields]
    expected_s10 = [
        "Initials", "Is Reporter As Patient", "Title", "First Name", "Last Name",
        "Occupation", "Date of Birth", "Sex Code", "Address 1", "Address 2",
        "State", "Country Code", "Zip Code", "Contact Number", "Email Address"
    ]
    for exp in expected_s10:
        assert exp in s10_labels, f"Step 10 missing field: {exp}"
    assert any(f.explicit_value == "No" for f in s10.extracted_fields if f.label == "Is Reporter As Patient")
    print("[PASS] Assertion 7: Step 10 (Add Patient) = 15/15 Fields Verified (Explicit Value 'No' for Is Reporter As Patient)")

    # Assertion 8: Step 11 (Product Information) -> 4 fields
    s11 = step_dict["TS1-S11"]
    assert len(s11.extracted_fields) == 4, f"Step 11 expected 4 fields, got {len(s11.extracted_fields)}"
    prod_name_f = next(f for f in s11.extracted_fields if f.label == "Product Name")
    generic_f = next(f for f in s11.extracted_fields if f.label == "Generic Name")
    form_f = next(f for f in s11.extracted_fields if f.label == "Formulation Code")
    add_drug_f = next(f for f in s11.extracted_fields if f.label == "Additional Drug Information")
    assert prod_name_f.control_type == "modal_search_select" and prod_name_f.search_trigger_icon
    assert generic_f.control_type == "auto_populate_verify" and generic_f.auto_populated
    assert form_f.control_type == "auto_populate_verify" and form_f.auto_populated
    assert add_drug_f.control_type == "text"
    print("[PASS] Assertion 8: Step 11 (Product) = 4/4 Fields Verified (Modal Search & Auto-Populate Flags Active)")

    # Assertion 9: Step 12 (Event Information) -> 16 fields
    s12 = step_dict["TS1-S12"]
    assert len(s12.extracted_fields) == 16, f"Step 12 expected 16 fields, got {len(s12.extracted_fields)}"
    s12_labels = [f.label for f in s12.extracted_fields]
    rep_term_f = next(f for f in s12.extracted_fields if f.label == "Reported Term")
    assert rep_term_f.control_type == "modal_search_select" and rep_term_f.search_trigger_icon
    
    # 4 Assessment dropdowns
    expected_assessment = ["Case Serious Reporter Code", "Case Serious Company Code", "Outcome Code", "Lack Of Efficacy"]
    for exp in expected_assessment:
        assert exp in s12_labels, f"Step 12 missing assessment dropdown: {exp}"
        f_obj = next(f for f in s12.extracted_fields if f.label == exp)
        assert f_obj.section == "event_assessment" and f_obj.control_type == "select"

    # 8 Seriousness dropdowns
    expected_seriousness = [
        "Death", "Hospitalization", "Life Threatening", "Disabling",
        "Congenital Anomaly", "Intervention Required", "Medically Significant", "Others"
    ]
    for exp in expected_seriousness:
        assert exp in s12_labels, f"Step 12 missing seriousness dropdown: {exp}"
        f_obj = next(f for f in s12.extracted_fields if f.label == exp)
        assert f_obj.section == "event_seriousness" and f_obj.control_type == "select"

    print("[PASS] Assertion 9: Step 12 (Event) = 16/16 Fields Verified (4 Assessment + 8 Seriousness Dropdowns)")

    print("=" * 85)
    print("ALL 9 PHASE 1 GxP SPECIFICATION ASSERTIONS PASSED WITH ZERO ERRORS!")
    print(f"Total Fields Extracted across Protocol: {total_fields_extracted}")
    print("=" * 85)

if __name__ == "__main__":
    run_phase1_verification()
