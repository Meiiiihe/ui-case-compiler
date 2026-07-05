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
    await userEvent.click(screen.getByRole("button", { name: "Validate" }));
    await waitFor(() => expect(screen.getByText("valid (1 steps)")).toBeInTheDocument());
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
    await userEvent.click(screen.getByRole("button", { name: "Run" }));
    await waitFor(() => expect(screen.getByText("RUN PAGE")).toBeInTheDocument());
  });
});
