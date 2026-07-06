export interface CaseSummary {
  id: string;
  name: string;
  source: string;
  step_count: number;
}

export interface RunSummary {
  run_id: string;
  plan_id: string;
  status: string;
  started_at: string;
}

export interface Locator {
  strategy: string;
  value: string | null;
  role: string | null;
  name: string | null;
}

export interface StepTarget {
  primary: Locator;
  fallbacks: Locator[];
  confidence: number;
}

export interface Step {
  id: string;
  type: string;
  name: string | null;
  timeout_ms: number | null;
  url?: string;
  target?: StepTarget;
  value?: string;
  key?: string;
  expected?: string;
  duration_ms?: number;
  checked?: boolean;
}

export interface ExecutablePlan {
  id: string;
  name: string;
  source: string;
  base_url: string | null;
  parameters: Record<string, unknown>;
  environment: string | null;
  steps: Step[];
}

export interface StepResult {
  step_id: string;
  step_type: string;
  status: "passed" | "failed" | "skipped";
  duration_ms: number;
  error: string | null;
  screenshot: string | null;
}

export interface RunResult {
  run_id: string;
  plan_id: string;
  status: "passed" | "failed";
  started_at: string;
  ended_at: string;
  steps: StepResult[];
  trace_path: string | null;
  video_paths: string[];
  report_path: string | null;
}

export interface DatasetPreviewRequest {
  filename: string;
  content_base64: string;
}

export interface DatasetPreviewResponse {
  columns: string[];
  rows: Record<string, string>[];
  preview_rows: Record<string, string>[];
  row_count: number;
}

export interface BatchCaseResult {
  index: number;
  status: "passed" | "failed";
  params: Record<string, string>;
  run_id: string | null;
  duration_ms: number;
  error: string | null;
}

export interface BatchRunRequest {
  rows: Record<string, string>[];
  concurrency: number;
  headed: boolean;
}

export interface BatchRunResult {
  batch_id: string;
  plan_id: string;
  status: "passed" | "failed";
  started_at: string;
  ended_at: string;
  total: number;
  passed: number;
  failed: number;
  concurrency: number;
  results: BatchCaseResult[];
}

export interface PageContext {
  url: string;
  title?: string;
  accessibility_tree?: string;
  dom_summary?: string;
  screenshot_path?: string;
}

export interface CompileNlRequest {
  text: string;
  context: PageContext;
  name?: string;
}

export interface CompileRecordingRequest {
  events: Record<string, unknown>[];
  name: string;
}

export interface StartRecordingRequest {
  url: string;
  name: string;
}

export interface RecordingSession {
  session_id: string;
  url: string;
  name: string;
  status: "recording";
}

export interface RunRequest {
  params: Record<string, string>;
  headed: boolean;
}

export interface ValidateResponse {
  valid: boolean;
  plan_id: string;
  step_count: number;
}
