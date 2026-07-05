import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import * as runsApi from "../api/runs";
import { RunDetailPage } from "./RunDetailPage";

afterEach(() => vi.restoreAllMocks());

function renderAt() {
  return render(
    <MemoryRouter initialEntries={["/runs/r1"]}>
      <Routes>
        <Route path="/runs/:runId" element={<RunDetailPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("RunDetailPage", () => {
  it("renders run status, steps and report path text", async () => {
    vi.spyOn(runsApi, "getRun").mockResolvedValue({
      run_id: "r1",
      plan_id: "p1",
      status: "passed",
      started_at: "2026-07-05T00:00:00Z",
      ended_at: "2026-07-05T00:00:01Z",
      steps: [
        {
          step_id: "step-001",
          step_type: "navigate",
          status: "passed",
          duration_ms: 64,
          error: null,
          screenshot: null,
        },
      ],
      trace_path: ".ui-case-compiler/artifacts/r1/trace.zip",
      video_paths: [],
      report_path: ".ui-case-compiler/reports/r1.html",
    });

    renderAt();

    await waitFor(() => expect(screen.getByText(/运行 r1/)).toBeInTheDocument());
    expect(screen.getByText("step-001")).toBeInTheDocument();
    expect(screen.getByText(/\.ui-case-compiler\/reports\/r1\.html/)).toBeInTheDocument();
  });
});
