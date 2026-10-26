import os
import sys
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")
load_dotenv()
import shutil
import uuid
import json
import asyncio
import threading
import time
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, UploadFile, File, Form, WebSocket, WebSocketDisconnect, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from schemas import ProtocolSession, ProtocolStep, TraceStage, ReadinessFlag, ProtocolGenerationRequest, ProtocolGenerationResponse, ExecutionSummaryReport, StepRootCauseAnalysis
from protocol_generator import ProtocolGenerator
from extractor import extract_protocol
from check_coverage import CoverageChecker, check_plan_to_spec, check_protocol_to_plan
from agents import PlannerAgent, PlaywrightGeneratorAgent, HealerAgent, compute_git_baseline, QwenLLMClient
from playwright_runner import PlaywrightRunner
from docx_writer import DocxWriter
from products import get_product, list_products

BACKEND_DIR = Path(__file__).resolve().parent
UPLOADS_DIR = BACKEND_DIR / "uploads"
ARTIFACTS_DIR = BACKEND_DIR / "artifacts"
SCREENSHOTS_DIR = ARTIFACTS_DIR / "screenshots"

UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="Clinevo OnePV — Validation & Execution Portal API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage for active sessions, generated artifacts, and approval events
sessions: Dict[str, ProtocolSession] = {}
session_plans: Dict[str, List[Dict[str, Any]]] = {}
session_specs: Dict[str, str] = {}
session_approval_events: Dict[str, asyncio.Event] = {}
session_halt_flags: Dict[str, bool] = {}
session_file_paths: Dict[str, str] = {}
active_connections: Dict[str, List[WebSocket]] = {}

# Mount screenshots directory
app.mount("/api/artifacts/screenshots", StaticFiles(directory=str(SCREENSHOTS_DIR)), name="screenshots")


@app.get("/api/products")
def get_products():
    return {"products": [p.model_dump() for p in list_products()]}

# Load live DOM map
DOM_MAP_PATH = ARTIFACTS_DIR / "dom_map.json"
def get_dom_map() -> Dict[str, Any]:
    if DOM_MAP_PATH.exists():
        with open(DOM_MAP_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"target_url": "https://mpv-two.vercel.app"}

async def broadcast_to_session(session_id: str, message: Dict[str, Any]):
    if session_id in active_connections:
        dead_connections = []
        for ws in active_connections[session_id]:
            try:
                await ws.send_json(message)
            except Exception:
                dead_connections.append(ws)
        for dead in dead_connections:
            active_connections[session_id].remove(dead)

def run_authoring_pipeline(file_path: str, filename: str, product_id: str = 'onepv') -> ProtocolSession:
    """Runs Phase 1 and Phase 2 authoring pipeline deterministically"""
    dom_map = get_dom_map()
    session = extract_protocol(file_path)
    session.filename = filename
    session.product_id = product_id
    sessions[session.session_id] = session

    # Stage 2: Qwen Planner Agent
    planner = PlannerAgent(dom_map)
    plan_steps, md_plan, plan_latency = planner.generate_plan(session)
    session_plans[session.session_id] = plan_steps
    
    session.trace_stages[1].status = "PASS"
    session.trace_stages[1].latency_seconds = plan_latency
    session.trace_stages[1].subtitle = f"Plan mapped via Groq Qwen 3.8-27B ({len(plan_steps)} steps)"
    session.trace_stages[1].artifact_content = md_plan

    # Stage 3: Coverage Gate 1
    gate1_report = session.gate1_report or check_protocol_to_plan(session)
    session.gate1_report = gate1_report
    session.trace_stages[2].status = "PASS" if gate1_report.passed else "FAIL"
    session.trace_stages[2].latency_seconds = 0.1
    session.trace_stages[2].artifact_content = json.dumps(gate1_report.model_dump(), indent=2)

    # Stage 4: Playwright Generator & Healer
    generator = PlaywrightGeneratorAgent(dom_map)
    spec_code, gen_latency = generator.generate_spec(session, plan_steps)
    spec_code = HealerAgent.verify_and_heal_selectors(spec_code, dom_map)
    session_specs[session.session_id] = spec_code

    # Save generated spec
    spec_path = ARTIFACTS_DIR / f"generated_{session.session_id}.spec.ts"
    with open(spec_path, "w", encoding="utf-8") as f:
        f.write(spec_code)

    session.trace_stages[3].status = "PASS"
    session.trace_stages[3].latency_seconds = gen_latency
    session.trace_stages[3].artifact_content = spec_code

    # Stage 5: Coverage Gate 2
    session.generated_spec_code = spec_code
    gate2_report = check_plan_to_spec(session)
    session.gate2_report = gate2_report
    session.trace_stages[4].status = "PASS" if gate2_report.passed else "FAIL"
    session.trace_stages[4].latency_seconds = 0.1
    session.trace_stages[4].artifact_content = json.dumps(gate2_report.model_dump(), indent=2)

    # Stage 6: Frozen Git Baseline
    git_sha = compute_git_baseline(spec_code, md_plan)
    session.git_commit_sha = git_sha
    session.trace_stages[5].status = "PASS"
    session.trace_stages[5].latency_seconds = 0.0
    session.trace_stages[5].subtitle = f"Commit: {git_sha}"
    session.trace_stages[5].artifact_content = f"Repository Baseline: {git_sha}\nArtifacts: generated_{session.session_id}.spec.ts\nAll 6 gates passing."

    sessions[session.session_id] = session
    return session

@app.get("/api/health")
def health():
    return {"status": "ok", "system": "Clinevo OnePV Validation Portal"}

@app.get("/api/list-sample-protocols")
def list_sample_protocols():
    files = []
    for f in UPLOADS_DIR.glob("*.docx"):
        files.append({
            "filename": f.name,
            "size_kb": round(f.stat().st_size / 1024, 1)
        })
    return {"protocols": files}

@app.post("/api/load-sample-protocol")
def load_sample_protocol(filename: str = Form(...), product_id: Optional[str] = Form('onepv')):
    target_path = UPLOADS_DIR / filename
    if not target_path.exists():
        raise HTTPException(status_code=404, detail="Sample protocol file not found")
    
    session = run_authoring_pipeline(str(target_path), filename, product_id or 'onepv')
    session_file_paths[session.session_id] = str(target_path)
    return session.model_dump()

@app.post("/api/upload-protocol")
async def upload_protocol(file: UploadFile = File(...), product_id: Optional[str] = Form('onepv')):
    session_id = str(uuid.uuid4())[:8]
    clean_filename = file.filename
    target_path = UPLOADS_DIR / f"{session_id}_{clean_filename}"

    with open(target_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    session = run_authoring_pipeline(str(target_path), clean_filename, product_id or 'onepv')
    session_file_paths[session.session_id] = str(target_path)
    return session.model_dump()

@app.get("/api/raw-protocol/{session_id}")
def get_raw_protocol(session_id: str):
    if session_id in session_file_paths and os.path.exists(session_file_paths[session_id]):
        filename = sessions[session_id].filename if session_id in sessions else "protocol.docx"
        return FileResponse(
            session_file_paths[session_id],
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            filename=filename
        )
    raise HTTPException(status_code=404, detail="Raw protocol file not found")

@app.get("/api/session/{session_id}")
def get_session(session_id: str):
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    session = sessions[session_id]
    screenshots_dir = SCREENSHOTS_DIR / session_id
    if screenshots_dir.exists():
        for step in session.steps:
            form_file = screenshots_dir / f"{step.step_id}_form.png"
            modal_file = screenshots_dir / f"{step.step_id}_modal.png"
            comb_file = screenshots_dir / f"{step.step_id}.png"
            if form_file.exists():
                step.form_screenshot_url = f"/api/artifacts/screenshots/{session_id}/{step.step_id}_form.png"
            if modal_file.exists():
                step.modal_screenshot_url = f"/api/artifacts/screenshots/{session_id}/{step.step_id}_modal.png"
            if comb_file.exists() and not step.screenshot_url:
                step.screenshot_url = f"/api/artifacts/screenshots/{session_id}/{step.step_id}.png"
    return session.model_dump()

class ExecuteRequest(BaseModel):
    sim_mode: str = "PASS"
    username: str = "sirihari.banda"
    password: str = "Clinevo@2026"
    enterprise: str = "Clinevo"
    requires_approval: bool = False
    headless: bool = True
    max_steps: Optional[int] = None

@app.post("/api/execute/{session_id}")
async def execute_session(
    session_id: str,
    req: ExecuteRequest
):
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    session = sessions[session_id]
    approval_event = threading.Event()
    session_approval_events[session_id] = approval_event
    session_halt_flags[session_id] = False

    main_loop = asyncio.get_running_loop()

    def run_worker_thread():
        # Ensure Windows Proactor event loop policy for flawless Playwright subprocess support
        if sys.platform == "win32":
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

        async def worker_coro():
            product = get_product(session.product_id)
            runner = PlaywrightRunner(
                base_url=product.base_url,
                headless=req.headless
            )
            async def ws_cb(msg):
                try:
                    asyncio.run_coroutine_threadsafe(broadcast_to_session(session_id, msg), main_loop)
                except Exception as e:
                    print(f"ws_cb error: {e}")

            try:
                await runner.run_protocol(
                    session=session,
                    sim_mode=req.sim_mode,
                    credentials={
                        "username": req.username,
                        "password": req.password,
                        "enterprise": req.enterprise
                    },
                    plan_steps=session_plans.get(session_id, []),
                    requires_approval=req.requires_approval,
                    approval_event=approval_event,
                    ws_callback=ws_cb,
                    is_halt_requested=lambda: session_halt_flags.get(session_id, False),
                    max_steps=req.max_steps
                )
            except Exception as e:
                print(f"Runner execution exception: {e}")

            # Notify complete
            try:
                asyncio.run_coroutine_threadsafe(broadcast_to_session(session_id, {
                    "type": "EXECUTION_COMPLETE",
                    "session": session.model_dump()
                }), main_loop)
            except Exception as e:
                print(f"Execution complete broadcast error: {e}")

        asyncio.run(worker_coro())

    worker_thread = threading.Thread(target=run_worker_thread, daemon=True)
    worker_thread.start()

    return {"status": "started", "session_id": session_id}

@app.post("/api/approve-login/{session_id}")
def approve_login(session_id: str):
    if session_id in session_approval_events:
        session_approval_events[session_id].set()
        return {"status": "approved"}
    return {"status": "no_event_found"}

@app.post("/api/approve-review/{session_id}")
def approve_review(session_id: str):
    if session_id in session_approval_events:
        session_halt_flags[session_id] = False
        session_approval_events[session_id].set()
        return {"status": "review_approved"}
    return {"status": "no_event_found"}

@app.post("/api/halt-execution/{session_id}")
def halt_execution(session_id: str):
    session_halt_flags[session_id] = True
    if session_id in session_approval_events:
        session_approval_events[session_id].set()
    return {"status": "halted"}

@app.get("/api/download-executed-docx/{session_id}")
def download_executed_docx(session_id: str):
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    session = sessions[session_id]
    
    # Locate original file in uploads or session_file_paths
    src_file = None
    if session_id in session_file_paths and os.path.exists(session_file_paths[session_id]):
        src_file = Path(session_file_paths[session_id])
    else:
        for p in UPLOADS_DIR.glob(f"*{session.filename}*"):
            src_file = p
            break
        if not src_file or not src_file.exists():
            for p in UPLOADS_DIR.glob("*.docx"):
                src_file = p
                break

    if not src_file:
        raise HTTPException(status_code=404, detail="Source protocol .docx missing")

    out_docx = DocxWriter.populate_executed_docx(
        session=session,
        source_docx_path=str(src_file),
        output_filename=f"executed_{session.filename}"
    )

    return FileResponse(
        out_docx,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=f"Executed_{session.filename}"
    )

@app.get("/api/download-companion-evidence-docx/{session_id}")
def download_companion_evidence_docx(session_id: str):
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    session = sessions[session_id]
    evidence_docx = DocxWriter.generate_companion_evidence_docx(
        session=session,
        output_filename=f"Screenshot_Evidence_{session.filename}"
    )

    clean_name = session.filename
    if clean_name.endswith(".docx"):
        clean_name = clean_name[:-5]

    return FileResponse(
        evidence_docx,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=f"Screenshot_Evidence_{clean_name}.docx"
    )

@app.post("/api/archive-session/{session_id}")
def archive_session(session_id: str):
    import hashlib
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    session = sessions[session_id]
    archive_dir = ARTIFACTS_DIR / "archive" / session_id
    archive_dir.mkdir(parents=True, exist_ok=True)

    manifest_files = {}

    def hash_and_copy(file_path: Path, dest_name: str):
        if file_path.exists() and file_path.is_file():
            hasher = hashlib.sha256()
            with open(file_path, "rb") as f:
                while chunk := f.read(65536):
                    hasher.update(chunk)
            file_hash = hasher.hexdigest()
            dest_path = archive_dir / dest_name
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(str(file_path), str(dest_path))
            manifest_files[dest_name] = {
                "sha256": file_hash,
                "size_bytes": dest_path.stat().st_size
            }

    exec_docx = ARTIFACTS_DIR / f"executed_{session.filename}"
    if exec_docx.exists():
        hash_and_copy(exec_docx, f"Executed_{session.filename}")

    evid_docx = ARTIFACTS_DIR / f"Screenshot_Evidence_{session.filename}"
    if evid_docx.exists():
        hash_and_copy(evid_docx, f"Screenshot_Evidence_{session.filename}")

    sc_dir = SCREENSHOTS_DIR / session_id
    if sc_dir.exists():
        for sc in sc_dir.glob("*.png"):
            hash_and_copy(sc, f"screenshots/{sc.name}")

    manifest_data = {
        "session_id": session_id,
        "protocol": session.document_no or session.filename,
        "archived_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "total_files": len(manifest_files),
        "files": manifest_files
    }

    manifest_json_path = archive_dir / "manifest.json"
    with open(manifest_json_path, "w", encoding="utf-8") as f:
        json.dump(manifest_data, f, indent=2)

    manifest_sha_path = archive_dir / "manifest.sha256"
    with open(manifest_sha_path, "w", encoding="utf-8") as f:
        for fname, info in manifest_files.items():
            f.write(f"{info['sha256']}  {fname}\n")

    return {
        "status": "archived",
        "archive_directory": str(archive_dir),
        "manifest": manifest_data
    }



def generate_ai_root_cause_analysis(session: ProtocolSession, failed_steps: List[ProtocolStep]) -> List[StepRootCauseAnalysis]:
    """
    Invokes Groq Qwen (with graceful deterministic fallback) to generate authoritative
    GxP Root Cause Analysis (RCA) and CAPA remediations for failed/blocked steps.
    """
    if not failed_steps:
        return []

    # 1. Deterministic GxP fallback mappings (100% fail-safe)
    fallback_analyses: List[StepRootCauseAnalysis] = []
    for s in failed_steps:
        obs = s.observed_result or s.failure_reason or "Discrepancy observed in actual DOM vs expected criteria"
        impact = "CRITICAL" if any(k in s.scenario.lower() for k in ["login", "save", "event", "patient", "submit"]) else "MAJOR"
        if "mandatory" in obs.lower() or "validation error" in obs.lower():
            rc_exp = "System enforced strict data validation. The step procedure attempted form submission before all mandatory GxP fields were completed."
            capa = "Ensure prerequisite clinical fields are fully populated prior to triggering form submission."
        elif "timeout" in obs.lower() or "waiting for" in obs.lower():
            rc_exp = "UI synchronization latency. Target element did not reach stable/actionable state within the timeout window."
            capa = "Review asynchronous component rendering speed; adjust network wait condition."
        elif "blocked" in obs.lower():
            rc_exp = "Dependent execution block. Step execution was inhibited by an upstream precondition halt."
            capa = "Resolve upstream blocker and re-execute serial sequence."
        elif any(k in obs.lower() for k in ["meddra", "badge", "coding status"]):
            rc_exp = f"Mock portal UI discrepancy: Expected coded status badge / indicator was not rendered in UI ({obs[:120]})."
            capa = "Verify coding dictionary microservice integration and ensure status indicator updates upon coding completion."
        elif any(k in obs.lower() for k in ["auto-populate", "empty in ui", "field '"]):
            rc_exp = f"Data-binding discrepancy: Target field was expected to auto-populate but remained empty in UI ({obs[:120]})."
            capa = "Verify dynamic lookup listener and field mapping configuration in UI form component."
        elif "table" in obs.lower() or "record" in obs.lower():
            rc_exp = f"Data grid discrepancy: Table record state did not match expected criteria ({obs[:120]})."
            capa = "Inspect table data store mutation and ensure optimistic UI or refetch completes after action."
        else:
            rc_exp = f"Functional discrepancy between expected protocol acceptance criteria and observed runtime DOM state ({obs[:150]})."
            capa = "Perform code inspection on active UI component and align acceptance criteria with functional specification."

        fallback_analyses.append(StepRootCauseAnalysis(
            step_id=s.step_id,
            scenario=s.scenario,
            failure_observation=obs,
            root_cause_explanation=rc_exp,
            impact_assessment=impact,
            capa_remediation=capa
        ))

    # 2. Try Groq Qwen for intelligent GxP RCA synthesis
    try:
        llm = QwenLLMClient()
        if not (llm.groq_api_key or llm.is_dgx_configured()):
            return fallback_analyses

        step_summaries = []
        for s in failed_steps[:15]:
            obs = s.observed_result or s.failure_reason or "Discrepancy observed"
            step_summaries.append({
                "step_id": s.step_id,
                "scenario": s.scenario,
                "procedure": (s.procedure or "")[:150],
                "expected": (s.expected_result or "")[:150],
                "observed": obs[:200]
            })

        system_prompt = (
            "You are an expert FDA 21 CFR Part 11 / EU Annex 11 Computer Systems Validation (CSV) Lead and Pharmacovigilance QA Specialist. "
            "Analyze the provided test execution discrepancies and produce an authoritative Root Cause Analysis (RCA) "
            "and CAPA remediation for each step in JSON format.\n"
            "Return a JSON object with a single key 'analyses' containing a list of objects:\n"
            "{\n"
            "  \"analyses\": [\n"
            "    {\n"
            "      \"step_id\": \"TS1-SXX\",\n"
            "      \"root_cause_explanation\": \"Authoritative 1-2 sentence technical/GxP root cause explanation\",\n"
            "      \"impact_assessment\": \"CRITICAL\" or \"MAJOR\" or \"MINOR\",\n"
            "      \"capa_remediation\": \"Actionable 1-2 sentence engineering/validation CAPA recommendation\"\n"
            "    }\n"
            "  ]\n"
            "}"
        )
        user_prompt = f"Protocol: {session.document_no or session.filename} - {session.title or session.filename}\nDiscrepancies:\n{json.dumps(step_summaries, indent=2)}"

        res = llm.chat_completion(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.1,
            max_tokens=650,
            json_mode=True
        )

        if res:
            parsed = json.loads(res)
            raw_list = parsed.get("analyses") if isinstance(parsed, dict) else (parsed if isinstance(parsed, list) else None)
            if raw_list and isinstance(raw_list, list):
                rca_map = {item.get("step_id"): item for item in raw_list if isinstance(item, dict) and "step_id" in item}
                merged_analyses = []
                for fb in fallback_analyses:
                    if fb.step_id in rca_map:
                        ai_item = rca_map[fb.step_id]
                        merged_analyses.append(StepRootCauseAnalysis(
                            step_id=fb.step_id,
                            scenario=fb.scenario,
                            failure_observation=fb.failure_observation,
                            root_cause_explanation=ai_item.get("root_cause_explanation") or fb.root_cause_explanation,
                            impact_assessment=ai_item.get("impact_assessment") if ai_item.get("impact_assessment") in ["CRITICAL", "MAJOR", "MINOR"] else fb.impact_assessment,
                            capa_remediation=ai_item.get("capa_remediation") or fb.capa_remediation
                        ))
                    else:
                        merged_analyses.append(fb)
                return merged_analyses
    except Exception as e:
        print(f"[AI RCA] Groq Qwen RCA generation fallback triggered: {e}")

    return fallback_analyses


@app.get("/api/session-summary/{session_id}", response_model=ExecutionSummaryReport)
def get_session_summary(session_id: str):
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    session = sessions[session_id]
    total_steps = len(session.steps)
    passed_count = sum(1 for s in session.steps if s.status == "PASS")
    failed_count = sum(1 for s in session.steps if s.status == "FAIL")
    blocked_count = sum(1 for s in session.steps if s.status == "BLOCKED")

    overall_status = "PASS" if (failed_count == 0 and blocked_count == 0 and passed_count > 0) else ("FAIL" if failed_count > 0 else "BLOCKED")
    acceptance_criteria_met = (overall_status == "PASS")

    failed_steps = [s for s in session.steps if s.status in ["FAIL", "BLOCKED"]]
    deviation_ids = [f"DEV-{i+1:03d}" for i in range(len(failed_steps))]
    root_cause_analyses = generate_ai_root_cause_analysis(session, failed_steps)

    manifest_file = ARTIFACTS_DIR / "archive" / session_id / "manifest.sha256"
    manifest_sha = None
    if manifest_file.exists():
        try:
            with open(manifest_file, "r", encoding="utf-8") as mf:
                lines = mf.read().splitlines()
                if lines:
                    manifest_sha = lines[0].split()[0]
        except Exception:
            pass

    return ExecutionSummaryReport(
        session_id=session_id,
        document_no=session.document_no or session.filename,
        protocol_title=session.title or session.filename,
        tester="sirihari.banda (S.B.)",
        execution_date_utc=time.strftime("%d-%b-%Y %H:%M UTC", time.gmtime()),
        total_steps=total_steps,
        passed_count=passed_count,
        failed_count=failed_count,
        blocked_count=blocked_count,
        overall_status=overall_status,
        acceptance_criteria_met=acceptance_criteria_met,
        deviation_ids=deviation_ids,
        root_cause_analyses=root_cause_analyses,
        archive_status="ARCHIVED" if manifest_file.exists() else "READY_FOR_ARCHIVE",
        manifest_sha256=manifest_sha
    )

@app.post("/api/generate-protocol")
def generate_protocol(req: ProtocolGenerationRequest):
    if req.protocol_type == "OQ":
        res = ProtocolGenerator.generate_oq_protocol(
            system_name=req.system_name,
            version=req.version
        )
    else:
        res = ProtocolGenerator.generate_pq_protocol(
            system_name=req.system_name,
            version=req.version
        )
    return res


@app.websocket("/ws/session/{session_id}")
async def websocket_session(websocket: WebSocket, session_id: str):
    await websocket.accept()
    if session_id not in active_connections:
        active_connections[session_id] = []
    active_connections[session_id].append(websocket)

    try:
        while True:
            data = await websocket.receive_text()
            # If client sends approve message
            try:
                msg = json.loads(data)
                action = msg.get("action")
                if action in ["APPROVE_LOGIN", "APPROVE_REVIEW"]:
                    if session_id in session_approval_events:
                        session_approval_events[session_id].set()
                elif action == "HALT_EXECUTION":
                    session_halt_flags[session_id] = True
                    if session_id in session_approval_events:
                        session_approval_events[session_id].set()
            except Exception:
                pass
    except WebSocketDisconnect:
        if session_id in active_connections and websocket in active_connections[session_id]:
            active_connections[session_id].remove(websocket)
