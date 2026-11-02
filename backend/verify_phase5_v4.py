import sys
import time
import shutil
import hashlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from audit_trail import AuditTrailManager

def run_phase5_verification():
    print("=== PHASE 5 VERIFICATION: FDA 21 CFR PART 11 IMAGE-BOUND CRYPTOGRAPHIC AUDIT TRAIL ===")
    
    test_session_id = f"test_audit_v4_{int(time.time())}"
    test_dir = Path("backend/artifacts/archive") / test_session_id
    test_dir.mkdir(parents=True, exist_ok=True)

    # Minimal valid 1x1 PNG bytes
    valid_png_bytes = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4"
        b"\x00\x00\x00\rIDATx\x9cc\xf8\xff\xff?\x00\x05\xfe\x02\xfe\xa748N\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    png_path = test_dir / "step_1_screenshot.png"
    png_path.write_bytes(valid_png_bytes)

    # 1. Valid chained execution with real .png, inputs_applied provenance, and gate_scores
    print("[Check 1] Logging step with screenshot, input provenance, and 4-gate evaluation...")
    inputs_applied = [
        {
            "field_id": "TS3-S07-F01",
            "field_label": "Seriousness",
            "value_applied": "Serious",
            "provenance": "protocol_explicit",
            "dom_readback_verified": True
        },
        {
            "field_id": "TS3-S07-F02",
            "field_label": "Hospitalization Admission Date",
            "value_applied": "2026-11-03",
            "provenance": "computed_dynamic",
            "dom_readback_verified": True
        },
        {
            "field_id": "TS3-S07-F03",
            "field_label": "Reporter Type",
            "value_applied": "HCP",
            "provenance": "cpu_semantic_match",
            "original_term": "Physician",
            "dom_readback_verified": True
        }
    ]
    gate_scores = {
        "gate1_passed": True,
        "gate2_passed": True,
        "gate3_semantic_similarity": 0.92,
        "gate4_passed": True,
        "final_status": "PASS"
    }

    entry = AuditTrailManager.log_event(
        session_id=test_session_id,
        actor_username="srihari.banda",
        actor_role="TEST_EXECUTOR",
        event_type="STEP_PASSED",
        step_id="TS3-S07",
        details="Step TS3-S07 PASSED: Hospitalization section dynamically revealed",
        screenshot_path=str(png_path),
        locked_spec_sha256="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        inputs_applied=inputs_applied,
        gate_scores=gate_scores
    )

    is_valid, err = AuditTrailManager.verify_audit_trail(test_session_id)
    print(f" -> Audit Trail Initial Verification: valid={is_valid}, err={err}")
    assert is_valid is True, f"Expected initial audit trail to be valid, got err: {err}"
    assert entry.screenshot_sha256 == hashlib.sha256(valid_png_bytes).hexdigest()
    print("[Check 1 PASSED] Audit trail cryptographically sealed with image hash & input provenance.")

    # 2. Modifying 1 byte of the .png file on disk without editing audit_trail.jsonl
    print("\n[Check 2] Testing binary screenshot image tampering detection...")
    tampered_bytes = valid_png_bytes[:-1] + b"\x00"
    png_path.write_bytes(tampered_bytes)

    is_valid_tampered_img, err_img = AuditTrailManager.verify_audit_trail(test_session_id)
    print(f" -> Tampered Image Verification: valid={is_valid_tampered_img}, err={err_img}")
    assert is_valid_tampered_img is False, "Audit trail must reject tampered screenshot binary bytes!"
    assert "Screenshot image tampering detected" in (err_img or ""), f"Expected 'Screenshot image tampering detected', got: {err_img}"
    print("[Check 2 PASSED] Binary screenshot tampering successfully caught by cryptographic sieve.")

    # Restore valid image
    png_path.write_bytes(valid_png_bytes)
    is_valid_restored, _ = AuditTrailManager.verify_audit_trail(test_session_id)
    assert is_valid_restored is True

    # 3. Modifying 1 character of inputs_applied in audit_trail.jsonl
    print("\n[Check 3] Testing audit_trail.jsonl input provenance tampering detection...")
    audit_file = AuditTrailManager.get_audit_file_path(test_session_id)
    content = audit_file.read_text(encoding="utf-8")
    
    # Tamper with the inputs_applied field in jsonl
    tampered_content = content.replace("protocol_explicit", "tampered_provenance")
    audit_file.write_text(tampered_content, encoding="utf-8")

    is_valid_tampered_json, err_json = AuditTrailManager.verify_audit_trail(test_session_id)
    print(f" -> Tampered JSON Verification: valid={is_valid_tampered_json}, err={err_json}")
    assert is_valid_tampered_json is False, "Audit trail must reject tampered JSON payload!"
    assert "Tampering detected: entry_hash mismatch" in (err_json or ""), f"Expected 'Tampering detected: entry_hash mismatch', got: {err_json}"
    print("[Check 3 PASSED] JSON payload tampering successfully caught by entry_hash mismatch.")

    # Cleanup test artifacts
    if test_dir.exists():
        shutil.rmtree(test_dir, ignore_errors=True)

    print("\n[PASS] ALL PHASE 5 CRYPTOGRAPHIC AUDIT TRAIL VERIFICATION CHECKS PASSED!")

if __name__ == "__main__":
    run_phase5_verification()
