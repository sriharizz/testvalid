import sys
import time
import shutil
import hashlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import docx
from schemas import (
    DirectProtocolAuthorRequest,
    DirectStepInput,
    AppliedInputRecord,
    GateEvaluationResult,
    ElectronicSignatureRecord
)
from protocol_generator import ProtocolGenerator
from docx_writer import DocxWriter
from audit_trail import AuditTrailManager

def run_phase6_verification():
    print("=== PHASE 6 MASTER VERIFICATION: FULL VSR, RCA & AUDIT CERTIFICATE ===")

    test_session_id = f"test_phase6_{int(time.time())}"
    
    # 1. Author Direct Protocol Session with TS1-S04 & TS3-S07
    print("[Check 1] Creating session with TS1-S04 (positive) and TS3-S07 (messy conditional negative)...")
    req = DirectProtocolAuthorRequest(
        protocol_type="PQ",
        product_id="onepv",
        document_no="CLIN-PQ-PHASE6-001",
        title="Pharmacovigilance Direct Qualification Protocol",
        steps=[
            DirectStepInput(
                step_id="TS1-S04",
                scenario="Register Adverse Event Case",
                procedure="In Manual Case Registration, enter Case Type as Spontaneous and Case Intake Source as HCP. Click Save.",
                expected_result="System shall register case successfully and create a case ID."
            ),
            DirectStepInput(
                step_id="TS3-S07",
                scenario="Negative Future Hospitalization Admission Date",
                procedure="Pick 'Serious' for seriousness—this opens the hospitalization sub-section. Set admission date to a future date (tomorrow), fill all other mandatory patient & reporter fields with valid dummy data, choose 'Physician' as reporter type, and try to Save. (µ)",
                expected_result="System should block registration and show an error alert that Admission Date cannot be in the future."
            )
        ]
    )
    session, source_docx_path = ProtocolGenerator.create_direct_session(req)
    session.session_id = test_session_id
    session.plan_locked_sha256 = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"

    # Setup dummy screenshot checkpoints
    from PIL import Image
    sc_dir = Path("backend/artifacts/screenshots") / test_session_id
    sc_dir.mkdir(parents=True, exist_ok=True)
    sc1 = sc_dir / "TS1-S04.png"
    sc2 = sc_dir / "TS3-S07.png"
    img = Image.new("RGB", (120, 80), color=(16, 149, 193))
    img.save(sc1)
    img.save(sc2)

    # Simulate step 1 execution (Positive)
    s1 = session.steps[0]
    s1.status = "PASS"
    s1.pass_fail_text = "Pass"
    s1.screenshot_required = True
    s1.combined_screenshot_path = str(sc1)
    s1.observed_result = "Case registered successfully with Temporary Case ID: TMP-CASE-8821"
    s1.applied_inputs = [
        AppliedInputRecord(
            field_label="Case Type",
            value_applied="Spontaneous",
            provenance="protocol_explicit",
            readback_verified=True
        )
    ]
    s1.gate_evaluation = GateEvaluationResult(
        gate1_passed=True,
        gate2_passed=True,
        gate3_semantic_similarity=0.95,
        final_status="PASS"
    )

    # Simulate step 2 execution (Messy conditional negative)
    s2 = session.steps[1]
    s2.status = "PASS"
    s2.pass_fail_text = "Pass"
    s2.screenshot_required = True
    s2.combined_screenshot_path = str(sc2)
    s2.observed_result = "Validation Failed: Date of Hospital Admission must not be later than current date."
    s2.applied_inputs = [
        AppliedInputRecord(
            field_label="Seriousness",
            value_applied="Serious",
            provenance="protocol_explicit",
            readback_verified=True
        ),
        AppliedInputRecord(
            field_label="Hospitalization Admission Date",
            value_applied="2026-11-03",
            provenance="computed_dynamic",
            readback_verified=True
        ),
        AppliedInputRecord(
            field_label="Reporter Type",
            value_applied="HCP",
            provenance="cpu_semantic_match",
            original_term="Physician",
            readback_verified=True
        ),
        AppliedInputRecord(
            field_label="Patient Initials",
            value_applied="JD",
            provenance="ai_synthesized_mandatory",
            readback_verified=True
        )
    ]
    s2.gate_evaluation = GateEvaluationResult(
        gate1_passed=True,
        gate2_passed=True,
        gate3_semantic_similarity=1.0,
        final_status="PASS"
    )

    # Log events in audit trail
    AuditTrailManager.log_event(
        session_id=test_session_id,
        actor_username="srihari.banda",
        actor_role="TEST_EXECUTOR",
        event_type="PROTOCOL_UPLOADED",
        details="Author Direct Protocol CLIN-PQ-PHASE6-001"
    )
    AuditTrailManager.log_event(
        session_id=test_session_id,
        actor_username="srihari.banda",
        actor_role="TEST_EXECUTOR",
        event_type="STEP_PASSED",
        step_id="TS1-S04",
        details="Step TS1-S04 PASSED: Case created",
        screenshot_path=str(sc1),
        locked_spec_sha256=session.plan_locked_sha256,
        inputs_applied=[i.model_dump() for i in s1.applied_inputs],
        gate_scores=s1.gate_evaluation.model_dump()
    )
    AuditTrailManager.log_event(
        session_id=test_session_id,
        actor_username="srihari.banda",
        actor_role="TEST_EXECUTOR",
        event_type="STEP_PASSED",
        step_id="TS3-S07",
        details="Step TS3-S07 PASSED: Admission Date validation blocked future date",
        screenshot_path=str(sc2),
        locked_spec_sha256=session.plan_locked_sha256,
        inputs_applied=[i.model_dump() for i in s2.applied_inputs],
        gate_scores=s2.gate_evaluation.model_dump()
    )

    print("[Check 1 PASSED] Protocol session simulated with full provenance and 4-gate evaluations.")

    # 2. Test DocxWriter.populate_executed_docx()
    print("\n[Check 2] Verifying populate_executed_docx() provenance disclosure & Part 11 signoff separation...")
    exec_docx_path = DocxWriter.populate_executed_docx(
        session=session,
        source_docx_path=source_docx_path,
        output_filename=f"executed_{test_session_id}.docx"
    )
    doc_exec = docx.Document(exec_docx_path)
    
    # Check that sign-off Reviewed By is empty
    t_sign = None
    for t in doc_exec.tables:
        if len(t.rows) >= 4 and "acceptance criteria" in t.rows[0].cells[0].text.lower():
            t_sign = t
            break
    assert t_sign is not None, "Sign-off table not found in executed document"
    reviewed_by = t_sign.rows[3].cells[1].text.strip()
    assert reviewed_by == "", f"Reviewed By must be blank prior to QA signoff, but found: '{reviewed_by}'"

    # Check that provenance disclosure is stamped into observed result
    step_table = doc_exec.tables[s2.table_index]
    full_table_text = " ".join(cell.text for row in step_table.rows for cell in row.cells)
    print(f" -> Table text snippet: {full_table_text[:200]}...")
    assert "[Provenance:" in full_table_text, "Expected '[Provenance:' disclosure in executed Word table!"
    assert "cpu semantic match" in full_table_text
    assert "computed dynamic" in full_table_text
    assert "ai synthesized mandatory" in full_table_text
    print("[Check 2 PASSED] Provenance disclosure stamped into Word table; Reviewed By correctly kept blank.")

    # 3. Test DocxWriter.generate_companion_evidence_docx()
    print("\n[Check 3] Verifying 4-Section Evidence Dossier generation...")
    evid_docx_path = DocxWriter.generate_companion_evidence_docx(
        session=session,
        output_filename=f"evidence_{test_session_id}.docx"
    )
    doc_evid = docx.Document(evid_docx_path)
    evid_text = " ".join(p.text for p in doc_evid.paragraphs)
    for t in doc_evid.tables:
        evid_text += " " + " ".join(cell.text for row in t.rows for cell in row.cells)

    assert "Section 1: Validation Summary Report" in evid_text, "Missing Section 1 in evidence dossier"
    assert "Section 2: ALCOA+ Input Data Provenance" in evid_text, "Missing Section 2 in evidence dossier"
    assert "Section 3: Deviation Registry" in evid_text, "Missing Section 3 in evidence dossier"
    assert "Section 4: Stamped Visual Evidence" in evid_text, "Missing Section 4 in evidence dossier"
    assert "QUALIFIED / PASS" in evid_text
    assert "Zero Deviations Recorded" in evid_text
    assert "Cryptographic Checkpoint for TS3-S07" in evid_text
    print("[Check 3 PASSED] 4-Section VSR + Provenance + RCA + Evidence Dossier verified.")

    # 4. Test DocxWriter.generate_audit_trail_certificate_docx()
    print("\n[Check 4] Verifying Audit Trail Certificate (.docx) generation...")
    cert_docx_path = DocxWriter.generate_audit_trail_certificate_docx(
        session=session,
        output_filename=f"cert_{test_session_id}.docx"
    )
    doc_cert = docx.Document(cert_docx_path)
    cert_text = " ".join(p.text for p in doc_cert.paragraphs)
    for t in doc_cert.tables:
        cert_text += " " + " ".join(cell.text for row in t.rows for cell in row.cells)

    assert "Section 1: Cryptographic Integrity Verification Banner" in cert_text
    assert "VERIFIED INTACT — 0 TAMPER EVENTS" in cert_text
    assert "Section 2: 21 CFR Part 11 Hash-Chained Event Table" in cert_text
    assert "Section 3: Electronic Signature Registry" in cert_text
    assert "TS3-S07" in cert_text
    print("[Check 4 PASSED] Human-readable Audit_Trail_Certificate.docx verified.")

    # Cleanup test files
    for p in [exec_docx_path, evid_docx_path, cert_docx_path]:
        if Path(p).exists():
            Path(p).unlink()
    if sc_dir.exists():
        shutil.rmtree(sc_dir, ignore_errors=True)
    audit_file = AuditTrailManager.get_audit_file_path(test_session_id)
    if audit_file.parent.exists():
        shutil.rmtree(audit_file.parent, ignore_errors=True)

    print("\n[PASS] ALL PHASE 6 END-TO-END VERIFICATION CHECKS PASSED!")

if __name__ == "__main__":
    run_phase6_verification()
