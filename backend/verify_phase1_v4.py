import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from schemas import AppliedInputRecord, GateEvaluationResult, DirectProtocolAuthorRequest, ProtocolStep
from cpu_semantic_matcher import (
    compute_assertion_similarity,
    match_label_to_dom_candidates,
    match_dropdown_option
)

def run_phase1_verification():
    print("=== PHASE 1 VERIFICATION: SCHEMAS & OFFLINE CPU SEMANTIC ENGINE ===")

    # 1. Paraphrased negative assertion match
    exp = "System should block registration and show an error alert that Admission Date cannot be in the future."
    act_valid = "Validation Failed: Date of Hospital Admission must not be later than current date."
    sim_valid = compute_assertion_similarity(exp, act_valid)
    print(f"[Check 1] Paraphrased Admission Date similarity: {sim_valid}")
    assert sim_valid >= 0.78, f"Expected >= 0.78, got {sim_valid}"

    # 2. Wrong field negative assertion rejection
    act_wrong = "Validation Error: Reporter Country is required."
    sim_wrong = compute_assertion_similarity(exp, act_wrong)
    print(f"[Check 2] Wrong field error similarity: {sim_wrong}")
    assert sim_wrong < 0.45, f"Expected < 0.45 for wrong field error, got {sim_wrong}"

    # 3. Label to DOM candidate matching
    dom_candidates = [
        {"id": "#rep_country", "label": "Reporter Country"},
        {"id": "#adm_date", "label": "Hospitalization Admission Date"},
        {"id": "#pat_init", "label": "Patient Initials"}
    ]
    matched_ctrl, score = match_label_to_dom_candidates("admission date", dom_candidates)
    print(f"[Check 3] Matched label 'admission date' -> {matched_ctrl} (score={score})")
    assert matched_ctrl and matched_ctrl["id"] == "#adm_date" and score >= 0.82

    # 4. Dropdown synonym matching (Physician -> HCP)
    opts = [{"text": "HCP", "val": "HCP"}, {"text": "Consumer", "val": "CON"}]
    matched_opt, opt_score, prov = match_dropdown_option("Physician", opts)
    print(f"[Check 4] Matched dropdown 'Physician' -> {matched_opt} (score={opt_score}, provenance={prov})")
    assert matched_opt and matched_opt["val"] == "HCP" and prov == "cpu_semantic_match"

    print("[PASS] PHASE 1 VERIFICATION COMPLETE!")

if __name__ == "__main__":
    run_phase1_verification()
