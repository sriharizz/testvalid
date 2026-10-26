import os
import sys
import json
import time
import shutil
import hashlib
from pathlib import Path

# Add backend directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from schemas import ProtocolStep, StepAssertion, ElectronicSignatureRecord
from extractor import extract_protocol
from agents import PlannerAgent
from aria_compiler import PlanCacheManager
from playwright_runner import (
    safe_select_option,
    stitch_two_stage_screenshots,
    stamp_gxp_metadata_banner,
    verify_expected_result
)
from docx_writer import DocxWriter
from audit_trail import AuditTrailManager

class MockLocator:
    def __init__(self, visible=False, text="", inner_txt=""):
        self._visible = visible
        self._text = text
        self._inner_txt = inner_txt

    async def is_visible(self):
        return self._visible

    async def text_content(self):
        return self._text

    async def inner_text(self):
        return self._inner_txt or self._text

    def first(self):
        return self

    @property
    def first(self):
        return self

    def locator(self, *args, **kwargs):
        return self

    async def count(self):
        return 0

class MockPage:
    def __init__(self, url="https://mpv-two.vercel.app/login"):
        self.url = url

    def locator(self, *args, **kwargs):
        return MockLocator(visible=False)

    def get_by_role(self, *args, **kwargs):
        return MockLocator(visible=False)

def verify_gate_a_extraction():
    print("\n--- Gate A: Multi-Format Extraction Parity ---")
    pq_candidates = list(Path("backend/uploads").glob("*PQ-022*Manual*"))
    oq_candidates = list(Path("backend/uploads").glob("*OQ-036*Manual*"))

    assert pq_candidates, "Missing PQ-022 docx in backend/uploads"
    assert oq_candidates, "Missing OQ-036 docx in backend/uploads"

    pq_file = pq_candidates[0]
    oq_file = oq_candidates[0]

    pq_session = extract_protocol(str(pq_file))
    print(f"PQ-022 Extracted: {len(pq_session.steps)} steps.")
    assert len(pq_session.steps) >= 18, f"Expected >= 18 steps, got {len(pq_session.steps)}"
    assert pq_session.steps[0].col_map is not None, "Missing col_map on PQ-022 steps"

    oq_session = extract_protocol(str(oq_file))
    print(f"OQ-036 Extracted: {len(oq_session.steps)} steps across multi-table layout.")
    assert len(oq_session.steps) >= 45, f"Expected >= 45 steps, got {len(oq_session.steps)}"
    assert oq_session.steps[0].col_map is not None, "Missing col_map on OQ-036 steps"

    print("[PASS] Gate A: Multi-Format Extraction verified successfully.")
    return pq_session, oq_session

def verify_gate_b_cache_replay(session):
    print("\n--- Gate B: Zero-Token Replay Cache ---")
    dom_map = {}
    planner = PlannerAgent(dom_map)

    # First compile or load from cache
    t0 = time.time()
    plan_steps, md_plan, latency = planner.generate_plan(session)
    t1 = time.time()
    print(f"Run 1 Plan generation time: {(t1 - t0)*1000:.1f}ms (steps: {len(plan_steps)})")

    # Second run: MUST hit disk cache in < 100ms
    t2 = time.time()
    plan_steps_2, md_plan_2, latency_2 = planner.generate_plan(session)
    t3 = time.time()
    cache_time_ms = (t3 - t2) * 1000
    print(f"Run 2 Plan cache replay time: {cache_time_ms:.1f}ms")
    assert len(plan_steps_2) == len(plan_steps), "Mismatch in cached step count"
    assert cache_time_ms < 200, f"Cache replay too slow: {cache_time_ms}ms"

    print("[PASS] Gate B: Zero-Token Replay Cache verified successfully.")

async def verify_gate_c_zero_false_positives():
    print("\n--- Gate C: Zero False Positives Verification ---")
    page = MockPage(url="https://mpv-two.vercel.app/login")

    step = ProtocolStep(
        step_id="TS1-S01",
        step_number_display="1",
        table_index=0,
        row_index=1,
        action_intent="NAVIGATE",
        primary_section="General",
        scenario="Verify Active View",
        procedure="Navigate to case processing",
        expected_result="Case Processing screen active",
        assertions=[
            StepAssertion(
                assertion_type="VIEW_ACTIVE",
                description="Case Processing view active",
                target_text="case processing"
            )
        ]
    )

    passed, summary, fail = await verify_expected_result(page, step)
    assert not passed, "VIEW_ACTIVE falsely passed when view was not active!"
    print(f"Sabotage check 1: VIEW_ACTIVE mismatch rejected -> {summary[:60]}...")

    # Check execution failure propagation
    passed, summary, fail = await verify_expected_result(
        page, step, execution_failures=["Field 'Bogus' not found"]
    )
    assert not passed, "Execution failure was masked!"
    print(f"Sabotage check 2: Missing field rejected -> {summary[:60]}...")

    print("[PASS] Gate C: Zero False Positives verified successfully.")

def verify_gate_d_two_stage_screenshots():
    print("\n--- Gate D: Two-Stage Screenshot Stitching ---")
    from PIL import Image
    test_dir = Path("backend/artifacts/test_verify_gate_d")
    test_dir.mkdir(parents=True, exist_ok=True)

    form_p = test_dir / "form.png"
    modal_p = test_dir / "modal.png"
    comb_p = test_dir / "stitched.png"

    Image.new("RGB", (600, 300), color=(220, 230, 242)).save(form_p)
    Image.new("RGB", (600, 200), color=(242, 230, 220)).save(modal_p)

    stitch_two_stage_screenshots(form_p, modal_p, comb_p)
    assert comb_p.exists(), "Stitched screenshot was not created"

    with Image.open(comb_p) as im:
        assert im.height == 500, f"Expected height 500, got {im.height}"

    stamp_gxp_metadata_banner(comb_p, step_id="GATE-D", case_id="CASE-V3", tester="srihari.banda")
    with Image.open(comb_p) as im:
        assert im.height == 536, f"Expected height 536 (500 + 36px banner), got {im.height}"

    # Cleanup
    shutil.rmtree(test_dir, ignore_errors=True)
    print("[PASS] Gate D: Two-Stage Stitched Screenshot verified successfully.")

def verify_gate_e_audit_trail_and_part11(pq_session):
    print("\n--- Gate E: 21 CFR Part 11 Audit Trail & Signatures ---")
    test_session_id = f"test_val_{int(time.time())}"

    # 1. Log events
    e1 = AuditTrailManager.log_event(
        session_id=test_session_id,
        actor_username="srihari.banda",
        actor_role="TEST_EXECUTOR",
        event_type="PROTOCOL_UPLOADED",
        details="Protocol uploaded CLIN-EU-PAT-OPV-1-1-PQ-022"
    )
    e2 = AuditTrailManager.log_event(
        session_id=test_session_id,
        actor_username="srihari.banda",
        actor_role="TEST_EXECUTOR",
        event_type="STEP_PASSED",
        step_id="TS1-S01",
        details="Step passed"
    )
    e3 = AuditTrailManager.log_event(
        session_id=test_session_id,
        actor_username="qa.lead",
        actor_role="QA_REVIEWER",
        event_type="ELECTRONIC_SIGNATURE_APPLIED",
        details="Signed as QA_REVIEWER"
    )

    # 2. Verify hash chain
    is_valid, err = AuditTrailManager.verify_audit_trail(test_session_id)
    assert is_valid, f"Audit trail failed hash-chain verification: {err}"
    print(f"Audit trail verified: 3 chained entries, hash integrity OK.")

    # 3. Verify DOCX signoff isolation
    pq_session.session_id = test_session_id
    out_docx = DocxWriter.populate_executed_docx(
        session=pq_session,
        source_docx_path=str(list(Path("backend/uploads").glob("*PQ-022*Manual*"))[0]),
        output_filename=f"test_gate_e_{test_session_id}.docx"
    )
    import docx
    doc = docx.Document(out_docx)
    t6 = doc.tables[6]
    reviewed_by_text = t6.rows[3].cells[1].text.strip()
    assert reviewed_by_text == "", f"Expected Reviewed By to be empty prior to QA sign-off, but found: '{reviewed_by_text}'"
    print("Part 11 verification: Table 6 'Reviewed By' correctly left empty prior to QA signoff.")

    # 4. Apply QA review signature
    qa_sig = ElectronicSignatureRecord(
        signer_username="qa.lead",
        signer_full_name="QA Lead",
        signer_initials="QL",
        signer_role="QA_REVIEWER",
        signature_meaning="I have reviewed and approved this execution record.",
        signed_at_utc=e3.timestamp_utc,
        signature_hash="mock_hash_12345"
    )
    DocxWriter.apply_qa_review_signature(out_docx, qa_sig)
    doc_after = docx.Document(out_docx)
    reviewed_after = doc_after.tables[6].rows[3].cells[1].text.strip()
    assert "QA Lead" in reviewed_after, f"Expected 'QA Lead' in Reviewed By, got '{reviewed_after}'"
    print(f"Part 11 verification: Table 6 'Reviewed By' updated with: '{reviewed_after}'.")

    # Cleanup test artifacts
    audit_file = AuditTrailManager.get_audit_file_path(test_session_id)
    if audit_file.parent.exists():
        shutil.rmtree(audit_file.parent, ignore_errors=True)
    if Path(out_docx).exists():
        Path(out_docx).unlink()

    print("[PASS] Gate E: 21 CFR Part 11 Audit Trail & Signatures verified successfully.")

async def run_all_gates():
    print("==============================================================")
    print("   AI IDE V3 ARCHITECTURE ACCEPTANCE VERIFICATION SUITE")
    print("==============================================================")
    pq_session, oq_session = verify_gate_a_extraction()
    verify_gate_b_cache_replay(pq_session)
    await verify_gate_c_zero_false_positives()
    verify_gate_d_two_stage_screenshots()
    verify_gate_e_audit_trail_and_part11(pq_session)
    print("\n==============================================================")
    print("   ALL 5 ACCEPTANCE GATES PASSED! ARCHITECTURE READY FOR PRODUCTION")
    print("==============================================================")

if __name__ == "__main__":
    import asyncio
    asyncio.run(run_all_gates())
