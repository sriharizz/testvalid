import sys
import time
import shutil
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import docx
from agents import QwenLLMClient
from audit_trail import AuditTrailManager
from schemas import DirectProtocolAuthorRequest, DirectStepInput
from protocol_generator import ProtocolGenerator
from docx_writer import DocxWriter

def run_llm_tracking_verification():
    print("=== VERIFYING ALCOA+ LLM CONTEXT & TOKEN FOOTPRINT TRACKER ===")

    # 1. Verify Provider Safety: DGX is off / ready to switch; Groq is primary
    print("[Check 1] Verifying Provider Safety & Configuration...")
    llm = QwenLLMClient()
    print(f" -> Active provider: {llm.provider}")
    print(f" -> is_dgx_configured: {llm.is_dgx_configured()} (DGX safely bypassed while offline)")
    assert llm.provider == "GROQ", f"Expected provider 'GROQ', got '{llm.provider}'"
    assert llm.is_dgx_configured() is False, "DGX must not be configured/called while offline"
    print("[Check 1 PASSED] QwenLLMClient configured for Groq with DGX safely dormant.")

    # 2. Reset and execute tracked LLM call
    print("\n[Check 2] Executing tracked LLM invocation via Groq Cloud...")
    QwenLLMClient.reset_total_usage()
    assert QwenLLMClient.get_total_usage()["total_calls"] == 0

    reply = llm.chat_completion(
        messages=[{"role": "user", "content": "Respond with the word PASS in uppercase"}],
        max_tokens=10
    )
    metrics = QwenLLMClient.get_total_usage()
    print(f" -> LLM Reply: {reply}")
    print(f" -> Tracked Metrics: {metrics}")

    assert reply is not None, "Groq call failed to return content"
    assert metrics["total_calls"] == 1, f"Expected total_calls=1, got {metrics['total_calls']}"
    assert metrics["prompt_tokens"] > 0, f"Expected prompt_tokens > 0, got {metrics['prompt_tokens']}"
    assert metrics["completion_tokens"] > 0, f"Expected completion_tokens > 0, got {metrics['completion_tokens']}"
    assert metrics["total_tokens"] == metrics["prompt_tokens"] + metrics["completion_tokens"]
    assert "Groq" in metrics["model_used"]
    print(f"[Check 2 PASSED] Invocations: {metrics['total_calls']}, Context Tokens: {metrics['prompt_tokens']}, Completion Tokens: {metrics['completion_tokens']}.")

    # 3. Cryptographic Audit Trail Sealing of Token Metrics
    print("\n[Check 3] Cryptographically binding LLM context & tokens into Part 11 Audit Trail...")
    test_session_id = f"test_llm_audit_{int(time.time())}"
    audit_file = AuditTrailManager.get_audit_file_path(test_session_id)

    entry = AuditTrailManager.log_event(
        session_id=test_session_id,
        actor_username="srihari.banda",
        actor_role="TEST_EXECUTOR",
        event_type="PLAN_COMPILED",
        details="Compiled protocol plan with tracked Groq context",
        llm_metrics=metrics
    )
    is_valid, err = AuditTrailManager.verify_audit_trail(test_session_id)
    print(f" -> Audit Trail Verification: valid={is_valid}, err={err}")
    assert is_valid is True, f"Audit trail failed verification: {err}"

    # Tamper with the llm_metrics in audit_trail.jsonl
    content = audit_file.read_text(encoding="utf-8")
    assert '"prompt_tokens"' in content, "llm_metrics must be present in audit_trail.jsonl"
    tampered_content = content.replace(f'"prompt_tokens":{metrics["prompt_tokens"]}', '"prompt_tokens":999999').replace(f'"prompt_tokens": {metrics["prompt_tokens"]}', '"prompt_tokens": 999999')
    assert tampered_content != content, "Tampering replace failed to modify content!"
    audit_file.write_text(tampered_content, encoding="utf-8")

    is_valid_tamp, err_tamp = AuditTrailManager.verify_audit_trail(test_session_id)
    print(f" -> Tampered Token Verification: valid={is_valid_tamp}, err={err_tamp}")
    assert is_valid_tamp is False, "Audit trail must reject tampered token counts!"
    assert "Tampering detected: entry_hash mismatch" in (err_tamp or "")
    print("[Check 3 PASSED] LLM token metrics are cryptographically sealed into SHA-256 hash chain.")

    # 4. Verify Word Deliverables (VSR & Audit Certificate)
    print("\n[Check 4] Verifying Word Evidence Dossier & Audit Certificate disclosure...")
    req = DirectProtocolAuthorRequest(
        protocol_type="PQ",
        product_id="onepv",
        document_no="CLIN-PQ-TOKEN-001",
        title="Token Tracked Protocol",
        steps=[
            DirectStepInput(
                step_id="TS1-S01",
                scenario="Register Case",
                procedure="Fill Case Type as Spontaneous. Save.",
                expected_result="Case registered successfully."
            )
        ]
    )
    session, docx_path = ProtocolGenerator.create_direct_session(req)
    session.session_id = test_session_id
    session.llm_metrics = metrics
    session.steps[0].status = "PASS"

    evid_path = DocxWriter.generate_companion_evidence_docx(session, output_filename=f"evid_llm_{test_session_id}.docx")
    cert_path = DocxWriter.generate_audit_trail_certificate_docx(session, output_filename=f"cert_llm_{test_session_id}.docx")

    # Inspect VSR
    doc_evid = docx.Document(evid_path)
    evid_text = " ".join(cell.text for t in doc_evid.tables for row in t.rows for cell in row.cells)
    print(f" -> VSR text snippet: {evid_text[:250]}...")
    assert "AI LLM Invocations:" in evid_text
    assert "AI Token Footprint (Context / Gen):" in evid_text
    assert f"{metrics['total_tokens']} tokens" in evid_text

    # Inspect Audit Certificate
    doc_cert = docx.Document(cert_path)
    cert_text = " ".join(cell.text for t in doc_cert.tables for row in t.rows for cell in row.cells)
    assert "AI & Token Traceability (ALCOA+):" in cert_text
    print("[Check 4 PASSED] Token footprint & context size verified in VSR and Audit Certificate.")

    # Cleanup test files
    for p in [evid_path, cert_path]:
        if Path(p).exists():
            Path(p).unlink()
    if audit_file.parent.exists():
        shutil.rmtree(audit_file.parent, ignore_errors=True)

    print("\n[PASS] ALL ALCOA+ LLM CONTEXT & TOKEN TRACKING CHECKS PASSED!")

if __name__ == "__main__":
    run_llm_tracking_verification()
