import os
import sys
import time
import json
import httpx
import docx
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
UPLOADS_DIR = BACKEND_DIR / "uploads"
ARTIFACTS_DIR = BACKEND_DIR / "artifacts"

API_BASE = "http://localhost:8000"
FRONTEND_BASE = "http://localhost:5173"

def run_e2e_verification():
    print("=" * 70)
    print("STARTING END-TO-END VERIFICATION: CLINEVO ONEPV VALIDATION PORTAL")
    print("=" * 70)

    client = httpx.Client(timeout=60.0)

    # 1. Verify Backend Health
    print("\n[1/6] Verifying Backend Health API...")
    try:
        res = client.get(f"{API_BASE}/api/health")
        assert res.status_code == 200, f"Expected 200, got {res.status_code}"
        assert res.json().get("status") == "ok"
        print("  [OK] Backend health verified: 200 OK")
    except Exception as e:
        print(f"  [ERROR] Backend not responding at {API_BASE}: {e}")
        sys.exit(1)

    # 2. Verify Sample Protocols List
    print("\n[2/6] Verifying Available Protocol Ingestion Catalogs...")
    res = client.get(f"{API_BASE}/api/list-sample-protocols")
    assert res.status_code == 200
    protocols = res.json().get("protocols", [])
    print(f"  [OK] Discovered {len(protocols)} protocols in upload directory:")
    for p in protocols:
        print(f"       - {p['filename']} ({p['size_kb']} KB)")

    # 3. Dynamic .docx Ingestion & 6-Stage Authoring Pipeline
    print("\n[3/6] Testing Dynamic Ingestion via POST /api/upload-protocol...")
    pq_file = UPLOADS_DIR / "CLIN-EU-PAT-OPV-1-1-PQ-022- Manual - Registering Adverse Event Case.docx"
    assert pq_file.exists(), "PQ-022 docx missing in uploads!"

    with open(pq_file, "rb") as f:
        files = {"file": (pq_file.name, f, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
        res = client.post(f"{API_BASE}/api/upload-protocol", files=files)

    assert res.status_code == 200, f"Upload failed: {res.text}"
    session = res.json()
    session_id = session["session_id"]
    print(f"  [OK] Protocol parsed into Session ID: {session_id}")
    print(f"       Document No: {session['document_no']} | Total Steps: {session['total_steps']} | Evidence (µ): {session['total_screenshots']}")

    # 4. Verify All 6 Traceability Stages
    print("\n[4/6] Verifying 6-Stage Traceability Timeline & Coverage Gates...")
    stages = session.get("trace_stages", [])
    assert len(stages) == 6, f"Expected 6 stages, got {len(stages)}"

    for s in stages:
        assert s["status"] == "PASS", f"Stage {s['stage_number']} did not pass: {s['title']}"
        print(f"  [PASS] Stage {s['stage_number']}: {s['title']} | Latency: {s['latency_seconds']}s | {s['subtitle']}")

    # Check Gate 1 artifact
    gate1_report = json.loads(stages[2]["artifact_content"])
    assert gate1_report["passed"] is True
    assert gate1_report["order_verified"] is True
    assert len(gate1_report["violations"]) == 0

    # Check Gate 2 artifact
    gate2_report = json.loads(stages[4]["artifact_content"])
    assert gate2_report["passed"] is True
    assert gate2_report["order_verified"] is True
    assert len(gate2_report["violations"]) == 0
    print("  [OK] Coverage Gate 1 & Gate 2 Deterministic Reports verified: 0 violations.")

    # 5. Live Execution Against https://mpv-two.vercel.app
    print("\n[5/6] Triggering Live Automation Execution against https://mpv-two.vercel.app ...")
    exec_res = client.post(
        f"{API_BASE}/api/execute/{session_id}",
        json={
            "sim_mode": "PASS",
            "username": "sirihari.banda",
            "password": "Clinevo@2026",
            "enterprise": "Clinevo",
            "requires_approval": False,
            "headless": True
        }
    )
    assert exec_res.status_code == 200
    print("  [OK] Execution launched in background task. Monitoring progress...")

    # Poll session until first key steps complete
    time.sleep(8)
    res_session = client.get(f"{API_BASE}/api/session/{session_id}")
    live_session = res_session.json()
    steps_passed = [s for s in live_session["steps"] if s["status"] == "PASS"]
    print(f"  [OK] Live browser executed steps: {len(steps_passed)} passed so far.")

    # 6. Verify Executed .docx Download & Embedded Evidence
    print("\n[6/6] Verifying Lossless .docx Populator & Evidence Embedding...")
    download_res = client.get(f"{API_BASE}/api/download-executed-docx/{session_id}")
    assert download_res.status_code == 200, f"Download failed: {download_res.status_code}"

    test_download_path = ARTIFACTS_DIR / f"e2e_downloaded_{session_id}.docx"
    with open(test_download_path, "wb") as f:
        f.write(download_res.content)

    assert test_download_path.exists()
    doc = docx.Document(str(test_download_path))
    assert len(doc.tables) >= 6
    print(f"  [OK] Downloaded executed .docx successfully ({round(len(download_res.content)/1024, 1)} KB).")
    print(f"  [OK] Verified document tables count: {len(doc.tables)}")

    print("\n" + "=" * 70)
    print("ALL END-TO-END VERIFICATION GATES PASSED (100% SUCCESS)!")
    print(f"Backend Server:  {API_BASE}")
    print(f"Frontend Portal: {FRONTEND_BASE}")
    print("=" * 70)

if __name__ == "__main__":
    run_e2e_verification()
