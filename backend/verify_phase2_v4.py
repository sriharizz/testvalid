import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from schemas import DirectProtocolAuthorRequest, DirectStepInput
from protocol_generator import ProtocolGenerator

def run_phase2_verification():
    print("=== PHASE 2 VERIFICATION: DIRECT STUDIO AUTHORING & CPU CONFIDENCE SIEVE ===")
    req = DirectProtocolAuthorRequest(
        protocol_type="PQ",
        product_id="onepv",
        document_no="CLIN-PQ-STUDIO-001",
        title="Direct Studio Pharmacovigilance Qualification",
        steps=[
            DirectStepInput(
                step_id="TS1-S01",
                scenario="Register Adverse Event Case",
                procedure="In Manual Case Registration, under General Information, enter:\nCase Classifications Code: Adverse Event\nCase Intake Source Code: HCP\nCompany Receipt Date: 2023-10-15\nClick Save. (µ)",
                expected_result="System shall register case successfully with confirmation message and temporary case ID shall create."
            ),
            DirectStepInput(
                step_id="TS3-S07",
                scenario="Negative Future Hospitalization Admission Date",
                procedure="Navigate to Case Intake. Pick 'Serious' for seriousness—this opens the hospitalization sub-section. Set admission date to a future date (tomorrow), fill all other mandatory patient & reporter fields with valid dummy data, choose 'Physician' as reporter type, and try to Save. (µ)",
                expected_result="System should block registration and show an error alert that Admission Date cannot be in the future."
            )
        ]
    )
    session, docx_path = ProtocolGenerator.create_direct_session(req)
    assert len(session.steps) == 2
    s1, s2 = session.steps[0], session.steps[1]
    print(f"[Step 1] fields={len(s1.extracted_fields)}, conf={s1.cpu_parse_confidence}, discovery={s1.needs_mode1_discovery}")
    assert s1.cpu_parse_confidence >= 0.90 and not s1.needs_mode1_discovery

    print(f"[Step 2] fields={[(f.label, f.explicit_value) for f in s2.extracted_fields]}, conf={s2.cpu_parse_confidence}, discovery={s2.needs_mode1_discovery}")
    assert s2.needs_mode1_discovery is True
    extracted_map = {f.label.lower(): f.explicit_value for f in s2.extracted_fields}
    assert extracted_map.get("seriousness") == "Serious"
    assert extracted_map.get("reporter type") == "Physician"
    assert extracted_map.get("admission date") == "TODAY+1"
    print("[PASS] PHASE 2 VERIFICATION COMPLETE!")

if __name__ == "__main__":
    run_phase2_verification()
