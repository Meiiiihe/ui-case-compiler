import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import * as casesApi from "../api/cases";
import { CaseDetailPage } from "./CaseDetailPage";

afterEach(() => vi.restoreAllMocks());

const plan = {
  id: "p1",
  name: "Login",
  source: "manual",
  base_url: null,
  parameters: {},
  environment: null,
  steps: [{ id: "step-001", type: "navigate", name: null, timeout_ms: null, url: "https://x" }],
};

function renderAt() {
  return render(
    <MemoryRouter initialEntries={["/cases/p1"]}>
      <Routes>
        <Route path="/cases/:caseId" element={<CaseDetailPage />} />
        <Route path="/runs/:runId" element={<div>RUN PAGE</div>} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("CaseDetailPage", () => {
  it("renders plan meta and steps", async () => {
    vi.spyOn(casesApi, "getCase").mockResolvedValue(plan);
    renderAt();
    await waitFor(() => expect(screen.getByText("Login")).toBeInTheDocument());
    expect(screen.getByText("step-001")).toBeInTheDocument();
  });

  it("validates the case", async () => {
    vi.spyOn(casesApi, "getCase").mockResolvedValue(plan);
    vi.spyOn(casesApi, "validateCase").mockResolvedValue({
      valid: true,
      plan_id: "p1",
      step_count: 1,
    });
    renderAt();
    await waitFor(() => expect(screen.getByText("Login")).toBeInTheDocument());
    await userEvent.click(screen.getByRole("button", { name: "校验计划" }));
    await waitFor(() => expect(screen.getByText("校验通过（1 步）")).toBeInTheDocument());
  });

  it("runs and navigates to run detail", async () => {
    vi.spyOn(casesApi, "getCase").mockResolvedValue(plan);
    vi.spyOn(casesApi, "runCase").mockResolvedValue({
      run_id: "r1",
      plan_id: "p1",
      status: "passed",
      started_at: "2026-07-05T00:00:00Z",
      ended_at: "2026-07-05T00:00:01Z",
      steps: [],
      trace_path: null,
      video_paths: [],
      report_path: null,
    });
    renderAt();
    await waitFor(() => expect(screen.getByText("Login")).toBeInTheDocument());
    await userEvent.click(screen.getByRole("button", { name: "正式运行" }));
    await waitFor(() => expect(screen.getByText("RUN PAGE")).toBeInTheDocument());
  });

  it("previews dataset and runs a batch", async () => {
    vi.spyOn(casesApi, "getCase").mockResolvedValue(plan);
    vi.spyOn(casesApi, "previewDataset").mockResolvedValue({
      columns: ["username", "password"],
      rows: [{ username: "alice", password: "secret" }],
      preview_rows: [{ username: "alice", password: "secret" }],
      row_count: 1,
    });
    vi.spyOn(casesApi, "batchRunCase").mockResolvedValue({
      batch_id: "batch-1",
      plan_id: "p1",
      status: "passed",
      started_at: "2026-07-05T00:00:00Z",
      ended_at: "2026-07-05T00:00:01Z",
      total: 1,
      passed: 1,
      failed: 0,
      concurrency: 1,
      results: [
        {
          index: 1,
          status: "passed",
          params: { username: "alice", password: "secret" },
          run_id: "run-1",
          duration_ms: 1200,
          error: null,
        },
      ],
    });

    renderAt();
    await waitFor(() => expect(screen.getByText("Login")).toBeInTheDocument());

    const file = new File(["username,password\nalice,secret\n"], "login.csv", {
      type: "text/csv",
    });
    await userEvent.upload(screen.getByLabelText("数据文件"), file);
    await waitFor(() => expect(screen.getByText("login.csv")).toBeInTheDocument());

    await userEvent.click(screen.getByRole("button", { name: "执行批量测试" }));
    await waitFor(() => expect(screen.getByText("username=alice，password=secret")).toBeInTheDocument());
    expect(screen.getByRole("link", { name: "查看" })).toHaveAttribute("href", "/runs/run-1");
  });
});
