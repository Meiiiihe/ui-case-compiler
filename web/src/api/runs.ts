import { apiFetch } from "./client";
import type { RunResult, RunSummary } from "./types";

export function listRuns(): Promise<RunSummary[]> {
  return apiFetch<RunSummary[]>("/runs");
}

export function getRun(id: string): Promise<RunResult> {
  return apiFetch<RunResult>(`/runs/${id}`);
}
