export type SimulationMode = 'PASS' | 'FAIL' | 'BLOCKED';

export interface ReadinessFlag {
  step_id: string;
  flag_type: 'AMBIGUOUS_ERROR_MESSAGE' | 'RUNTIME_DATA_REQUIRED';
  raw_text: string;
  resolved_value: string;
}

export interface ProtocolStep {
  step_id: string;
  step_number_display: string;
  test_set_number: number;
  test_set_title: string;
  table_index: number;
  row_index: number;
  scenario: string;
  procedure: string;
  expected_result: string;
  screenshot_required: boolean;
  capture_before_modal_ok: boolean;
  required_assertions_count: number;
  action_intent: string;
  test_data?: Record<string, any>;
  status: 'QUEUED' | 'EXECUTING' | 'PASS' | 'FAIL' | 'BLOCKED';
  latency_ms?: number | null;
  observed_result?: string | null;
  pass_fail_text?: 'Pass' | 'Fail' | 'Blocked' | null;
  initials_date?: string | null;
  screenshot_url?: string | null;
  form_screenshot_url?: string | null;
  modal_screenshot_url?: string | null;
  error_detail?: string | null;
}

export interface TraceStage {
  stage_number: number;
  title: string;
  subtitle: string;
  status: 'PENDING' | 'RUNNING' | 'PASS' | 'FAIL';
  latency_seconds: number;
  artifact_type: 'JSON' | 'MARKDOWN' | 'CODE' | 'COVERAGE' | 'GIT';
  artifact_content: string;
}

export interface ProtocolSession {
  session_id: string;
  filename: string;
  document_no: string;
  version: string;
  effective_date: string;
  title: string;
  objective: string;
  scope: string;
  total_steps: number;
  total_screenshots: number;
  coverage_mapped: number;
  coverage_skipped: number;
  git_commit_sha: string;
  readiness_flags: ReadinessFlag[];
  trace_stages: TraceStage[];
  steps: ProtocolStep[];
}
