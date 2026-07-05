import { apiFetch } from "./client";
import type {
  CaseSummary,
  CompileNlRequest,
  CompileRecordingRequest,
  ExecutablePlan,
  RecordingSession,
  RunRequest,
  RunResult,
  StartRecordingRequest,
  ValidateResponse,
} from "./types";

export function listCases(): Promise<CaseSummary[]> {
  return apiFetch<CaseSummary[]>("/cases");
}

export function compileNl(req: CompileNlRequest): Promise<ExecutablePlan> {
  return apiFetch<ExecutablePlan>("/cases/compile-nl", {
    method: "POST",
    body: JSON.stringify(req),
  });
}

export function compileRecording(req: CompileRecordingRequest): Promise<ExecutablePlan> {
  return apiFetch<ExecutablePlan>("/cases/compile-recording", {
    method: "POST",
    body: JSON.stringify(req),
  });
}

export function startRecording(req: StartRecordingRequest): Promise<RecordingSession> {
  return apiFetch<RecordingSession>("/recordings/start", {
    method: "POST",
    body: JSON.stringify(req),
  });
}

export function stopRecording(sessionId: string): Promise<ExecutablePlan> {
  return apiFetch<ExecutablePlan>(`/recordings/${sessionId}/stop`, {
    method: "POST",
  });
}

export function getCase(id: string): Promise<ExecutablePlan> {
  return apiFetch<ExecutablePlan>(`/cases/${id}`);
}

export function updateCase(id: string, plan: ExecutablePlan): Promise<ExecutablePlan> {
  return apiFetch<ExecutablePlan>(`/cases/${id}`, {
    method: "PUT",
    body: JSON.stringify(plan),
  });
}

export function validateCase(id: string): Promise<ValidateResponse> {
  return apiFetch<ValidateResponse>(`/cases/${id}/validate`, { method: "POST" });
}

export function dryRun(id: string, req: RunRequest): Promise<RunResult> {
  return apiFetch<RunResult>(`/cases/${id}/dry-run`, {
    method: "POST",
    body: JSON.stringify(req),
  });
}

export function runCase(id: string, req: RunRequest): Promise<RunResult> {
  return apiFetch<RunResult>(`/cases/${id}/run`, {
    method: "POST",
    body: JSON.stringify(req),
  });
}
