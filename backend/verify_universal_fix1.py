import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from extractor import extract_fields_from_procedure, extract_step_checkpoints, extract_protocol

def test_universal_directive_filtering_and_multiline_fields():
    print("[Check 1] Testing universal section directive filter & colon-less 2-line field extraction...")
    sample_proc = """
    In the Clinical Portal page, enter the data in below fields,
    Under Subject Demographics section enter the below details:
    Subject Initials
         (Enter the data)
    Enrollment Status: Active
         (Select from the dropdown)
    Birth Date
         (Select date)
    Under Lab Assessment Section Update the below details:
    Primary Lab Country
         (Update the value from dropdown)
    Click on Save button.
    """
    fields = extract_fields_from_procedure("TEST-S01", "general", sample_proc)
    labels = [f.label for f in fields]
    sections = {f.label: f.section for f in fields}
    types = {f.label: f.control_type for f in fields}
    print(f"  -> Extracted fields: {[(f.label, f.section, f.control_type) for f in fields]}")

    assert len(fields) == 4, f"Expected exactly 4 fields, got {len(fields)}: {labels}"
    assert "Subject Initials" in labels and types["Subject Initials"] == "text"
    assert "Enrollment Status" in labels and types["Enrollment Status"] == "select"
    assert "Birth Date" in labels and types["Birth Date"] == "date"
    assert "Primary Lab Country" in labels and types["Primary Lab Country"] == "select"
    assert sections["Subject Initials"] == "subject_demographics"
    assert sections["Primary Lab Country"] == "lab_assessment"
    print("  -> PASS: Directives filtered cleanly, sections tracked, and colon-less 2-line fields extracted!")

def test_universal_checkpoint_decomposition():
    print("[Check 2] Testing universal checkpoint sub-step decomposition...")
    proc_a = (
        "Open record list and click Delete icon.\n"
        "Directly click on Confirm Delete button.\n(Refer expected result 1)\n"
        "Enter audit reason for deletion.\n"
        "Click on Confirm Delete button.\n(Refer expected result 2)"
    )
    exp_a = "Error message shall display.\n\nSystem shall delete the record successfully with confirmation message."
    cps_a, is_comp_a = extract_step_checkpoints(proc_a, exp_a)
    assert is_comp_a is True and len(cps_a) == 2
    assert cps_a[0].polarity == "NEGATIVE" and cps_a[1].polarity == "POSITIVE"
    print(f"  -> PASS: Pattern A (NEGATIVE -> POSITIVE) decomposed into {len(cps_a)} checkpoints.")

    proc_b = (
        "Under Product section select Drug X (Refer expected result 1).\n"
        "Under Event section code term (Refer expected result 2).\n"
        "Leave Reporter blank and click Submit (Refer expected result 3)."
    )
    exp_b = (
        "Generic name shall auto populate.\n\n"
        "Term shall code successfully.\n\n"
        "System shall display error message."
    )
    cps_b, is_comp_b = extract_step_checkpoints(proc_b, exp_b)
    assert is_comp_b is True and len(cps_b) == 3
    assert [c.polarity for c in cps_b] == ["POSITIVE", "POSITIVE", "NEGATIVE"]
    print(f"  -> PASS: Pattern B (POSITIVE -> POSITIVE -> NEGATIVE) decomposed into {len(cps_b)} checkpoints.")

def test_uploaded_protocols_zero_header_leakage():
    print("[Check 3] Verifying zero directive/header leakage across all .docx protocols in uploads/...")
    uploads = list(Path("backend/uploads").glob("*Manual*.docx")) or list(Path("uploads").glob("*Manual*.docx"))
    for docx_file in uploads:
        session = extract_protocol(str(docx_file))
        for s in session.steps:
            for ef in s.extracted_fields:
                low = ef.label.lower()
                assert "below details" not in low and "below fields" not in low, (
                    f"Directive leaked as field in {docx_file.name} [{s.step_id}]: '{ef.label}'"
                )
        print(f"  -> Verified {docx_file.name}: {len(session.steps)} steps, 0 directive leaks.")

if __name__ == "__main__":
    print("=== RUNNING UNIVERSAL FIX 1 VERIFICATION SUITE ===")
    test_universal_directive_filtering_and_multiline_fields()
    test_universal_checkpoint_decomposition()
    test_uploaded_protocols_zero_header_leakage()
    print("=== [100% PASS] UNIVERSAL FIX 1 COMPLETE! ===")
