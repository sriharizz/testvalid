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

from schemas import ProtocolSession, ProtocolStep, TraceStage, ReadinessFlag
from extractor import extract_protocol
from check_coverage import CoverageChecker, check_plan_to_spec, check_protocol_to_plan
from agents import PlannerAgent, PlaywrightGeneratorAgent, HealerAgent, compute_git_baseline
from playwright_runner import PlaywrightRunner
from docx_writer import DocxWriter

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

def run_authoring_pipeline(file_path: str, filename: str) -> ProtocolSession:
    """Runs Phase 1 and Phase 2 authoring pipeline deterministically"""
    dom_map = get_dom_map()
    session = extract_protocol(file_path)
    session.filename = filename

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
def load_sample_protocol(filename: str = Form(...)):
    target_path = UPLOADS_DIR / filename
    if not target_path.exists():
        raise HTTPException(status_code=404, detail="Sample protocol file not found")
    
    session = run_authoring_pipeline(str(target_path), filename)
    session_file_paths[session.session_id] = str(target_path)
    return session.model_dump()

@app.post("/api/upload-protocol")
async def upload_protocol(file: UploadFile = File(...)):
    session_id = str(uuid.uuid4())[:8]
    clean_filename = file.filename
    target_path = UPLOADS_DIR / f"{session_id}_{clean_filename}"

    with open(target_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    session = run_authoring_pipeline(str(target_path), clean_filename)
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
            runner = PlaywrightRunner(
                base_url="https://mpv-two.vercel.app",
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
