from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Literal, Any

SectionType = Literal[
    "auth",
    "navigation",
    "general",
    "questionnaire",
    "reporter",
    "patient",
    "product",
    "event",
    "event_assessment",
    "event_seriousness",
    "activity_log",
    "case_processing",
    "open_case",
    "audit_history"
]

ControlType = Literal[
    "text",
    "select",
    "date",
    "toggle",
    "modal_search_select",
    "auto_populate_verify",
    "button_click",
    "link_new_tab",
    "file_download",
    "hover_tooltip_verify"
]

class ReadinessFlag(BaseModel):
    step_id: str
    flag_type: Literal["AMBIGUOUS_ERROR_MESSAGE", "RUNTIME_DATA_REQUIRED", "AMBIGUOUS_STEP", "UNMAPPED_ACTION"]
    raw_text: str
    resolved_value: str

class ExtractedFieldSpec(BaseModel):
    field_id: str                        # e.g., "TS1-S09-F01"
    section: SectionType                 # Active section from protocol procedure
    label: str                           # Exact field label from protocol, e.g., "First Name", "Sex code"
    raw_instruction: str                 # Exact instruction from protocol, e.g., "(Select from the dropdown)"
    control_type: ControlType            # Inferred from protocol instruction
    explicit_value: Optional[str] = None # Populated if protocol specifies literal value (e.g., "Adverse Event")
    search_trigger_icon: bool = False    # True when instruction says "Click on the search icon..."
    auto_populated: bool = False         # True when instruction says "(System will auto populate)"

class SubActionSpec(BaseModel):
    order: int
    description: str
    action_type: Literal[
        "navigate",
        "fill_fields",
        "click_button",
        "open_modal",
        "modal_select",
        "verify_modal_message",
        "verify_auto_populate",
        "verify_hover_tooltip",
        "verify_new_tab",
        "verify_file_download",
        "capture_screenshot"
    ]
    target_label: Optional[str] = None
    before_modal_dismiss: bool = False

class ProtocolStep(BaseModel):
    step_id: str                         # e.g., "TS1-S01" .. "TS1-S18"
    test_set_no: int = 1
    step_number_display: str             # e.g., "1", "2" .. "18"
    table_index: int
    row_index: int
    scenario: str
    procedure: str
    expected_result: str
    action_intent: str
    primary_section: SectionType
    extracted_fields: List[ExtractedFieldSpec] = Field(default_factory=list)
    sub_actions: List[SubActionSpec] = Field(default_factory=list)
    executable_commands: List[Dict[str, Any]] = Field(default_factory=list)
    screenshot_required: bool = False
    screenshot_count: int = 0
    capture_before_modal_dismiss: bool = False
    required_assertions_count: int = 1
    # Runtime Execution Results
    status: Literal["QUEUED", "EXECUTING", "PASS", "FAIL", "BLOCKED"] = "QUEUED"
    observed_result: Optional[str] = None
    failure_reason: Optional[str] = None
    form_screenshot_path: Optional[str] = None
    modal_screenshot_path: Optional[str] = None
    combined_screenshot_path: Optional[str] = None
    execution_duration_ms: Optional[int] = None
    tester_initials_date: Optional[str] = None

    # Backwards compatibility fields for seamless transition across phases
    test_set_number: int = 1
    test_set_title: str = ""
    test_data: Dict[str, Any] = Field(default_factory=dict)
    latency_ms: Optional[int] = None
    pass_fail_text: Optional[str] = None
    initials_date: Optional[str] = None
    screenshot_url: Optional[str] = None
    form_screenshot_url: Optional[str] = None
    modal_screenshot_url: Optional[str] = None
    error_detail: Optional[str] = None
    capture_before_modal_ok: bool = False

class PlannedFieldAction(BaseModel):
    field_id: str                        # 1-to-1 match with ExtractedFieldSpec.field_id
    section: SectionType
    label: str
    control_type: ControlType
    target_value: str                    # Synthesized by Qwen Planner (or preserved from explicit_value)
    expect_auto_populated: bool = False

class PlannedStep(BaseModel):
    step_id: str
    scenario: str
    action_intent: str
    primary_section: SectionType
    field_actions: List[PlannedFieldAction] = Field(default_factory=list)
    sub_actions: List[SubActionSpec] = Field(default_factory=list)
    executable_commands: List[Dict[str, Any]] = Field(default_factory=list)
    expected_assertions: List[str] = Field(default_factory=list)
    requires_form_screenshot: bool = False
    requires_modal_screenshot: bool = False

class CoverageGateReport(BaseModel):
    gate_name: Literal["GATE_1_PROTOCOL_TO_PLAN", "GATE_2_PLAN_TO_SPEC"]
    passed: bool
    total_steps_expected: int
    total_steps_mapped: int
    total_fields_expected: int
    total_fields_mapped: int
    missing_steps: List[str] = Field(default_factory=list)
    missing_fields: List[str] = Field(default_factory=list)
    order_mismatch_errors: List[str] = Field(default_factory=list)
    assertion_errors: List[str] = Field(default_factory=list)
    screenshot_errors: List[str] = Field(default_factory=list)
    skip_violations: List[str] = Field(default_factory=list)
    details: List[str] = Field(default_factory=list)

class TraceStage(BaseModel):
    stage_number: int                   # 1 to 6
    title: str                          # e.g., "1. Python Protocol Extractor"
    subtitle: str                       # e.g., "18 steps, 18 µ screenshot points"
    status: Literal["PENDING", "RUNNING", "PASS", "FAIL"] = "PENDING"
    latency_seconds: float = 0.0
    artifact_type: Literal["JSON", "MARKDOWN", "CODE", "COVERAGE", "GIT"]
    artifact_content: str = ""

class ProtocolSession(BaseModel):
    session_id: str
    filename: str
    document_no: str
    version: str
    effective_date: str
    title: str
    objective: str
    scope: str
    steps: List[ProtocolStep]
    planned_steps: List[PlannedStep] = Field(default_factory=list)
    gate1_report: Optional[CoverageGateReport] = None
    gate2_report: Optional[CoverageGateReport] = None
    generated_spec_code: Optional[str] = None
    git_baseline_commit: Optional[str] = None
    runtime_state: Dict[str, str] = Field(default_factory=dict)

    # Backwards compatibility attributes for frontend & stages
    total_steps: int = 0
    total_screenshots: int = 0
    coverage_mapped: int = 0
    coverage_skipped: int = 0
    git_commit_sha: str = "v1.1-a8f3d"
    readiness_flags: List[ReadinessFlag] = Field(default_factory=list)
    trace_stages: List[TraceStage] = Field(default_factory=list)


class StepRootCauseAnalysis(BaseModel):
    step_id: str
    scenario: str
    failure_observation: str
    root_cause_explanation: str
    impact_assessment: Literal["CRITICAL", "MAJOR", "MINOR"]
    capa_remediation: str

class ExecutionSummaryReport(BaseModel):
    session_id: str
    document_no: str
    protocol_title: str
    tester: str
    execution_date_utc: str
    total_steps: int
    passed_count: int
    failed_count: int
    blocked_count: int
    overall_status: Literal["PASS", "FAIL", "BLOCKED"]
    acceptance_criteria_met: bool
    deviation_ids: List[str] = Field(default_factory=list)
    root_cause_analyses: List[StepRootCauseAnalysis] = Field(default_factory=list)
    compliance_statement: str = "Executed in accordance with 21 CFR Part 11 and EU Annex 11 computerized system validation principles."
    archive_status: Optional[str] = "READY_FOR_ARCHIVE"
    manifest_sha256: Optional[str] = None

class ProtocolGenerationRequest(BaseModel):
    protocol_type: Literal["OQ", "PQ"]
    source_type: Literal["FDS", "URS"]
    system_name: str = "OnePV / Safety Platform"
    version: str = "1.0"
    document_no: Optional[str] = None
    requirements_text: Optional[str] = None
    target_url: Optional[str] = "https://mpv-two.vercel.app"

class ProtocolGenerationResponse(BaseModel):
    protocol_type: str
    document_no: str
    filename: str
    file_path: str
    total_steps_generated: int
    requirements_traced: int
    rtm_table_included: bool
    preview_steps: List[Dict[str, Any]]
