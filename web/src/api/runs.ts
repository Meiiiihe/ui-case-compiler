import { apiFetch } from "./client";
import type { RunResult, RunSummary } from "./types";

export function listRuns(): Promise<RunSummary[]> {
  return apiFetch<RunSummary[]>("/runs");
}

export function getRun(id: string): Promise<RunResult> {
  return apiFetch<RunResult>(`/runs/${id}`);
}

export function runArtifactUrl(id: string, kind: "trace" | "report"): string {
  return `/api/runs/${encodeURIComponent(id)}/artifacts/${kind}`;
}

export function stepScreenshotUrl(runId: string, stepId: string): string {
  return `/api/runs/${encodeURIComponent(runId)}/steps/${encodeURIComponent(stepId)}/screenshot`;
}
