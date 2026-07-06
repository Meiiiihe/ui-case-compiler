import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import * as casesApi from "../api/cases";
import * as runsApi from "../api/runs";
import { RunDetailPage } from "./RunDetailPage";

afterEach(() => vi.restoreAllMocks());

function renderAt() {
  return render(
    <MemoryRouter initialEntries={["/runs/r1"]}>
      <Routes>
        <Route path="/runs/:runId" element={<RunDetailPage />} />
        <Route path="/cases/:caseId" element={<div>CASE PAGE</div>} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("RunDetailPage", () => {
  it("renders run status and opens the failed step debug panel", async () => {
    vi.spyOn(runsApi, "getRun").mockResolvedValue({
      run_id: "r1",
      plan_id: "p1",
      status: "failed",
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
        {
          step_id: "step-010",
          step_type: "click",
          status: "failed",
          duration_ms: 963,
          error: "Unable to resolve locator",
          screenshot: ".ui-case-compiler/artifacts/r1/010-step-010.png",
        },
      ],
      trace_path: ".ui-case-compiler/artifacts/r1/trace.zip",
      video_paths: [],
      report_path: ".ui-case-compiler/reports/r1.html",
    });
    vi.spyOn(casesApi, "getCase").mockResolvedValue({
      id: "p1",
      name: "Login",
      source: "recording",
      base_url: null,
      parameters: {},
      environment: null,
      steps: [
        { id: "step-001", type: "navigate", name: null, timeout_ms: null, url: "https://x" },
        {
          id: "step-010",
          type: "click",
          name: null,
          timeout_ms: null,
          target: {
            confidence: 0.82,
            primary: { strategy: "role", value: null, role: "button", name: "提交" },
            fallbacks: [{ strategy: "text", value: "提交", role: null, name: null }],
          },
        },
      ],
    });

    renderAt();

    await waitFor(() => expect(screen.getByText(/运行 r1/)).toBeInTheDocument());
    expect(screen.getByText("失败原因")).toBeInTheDocument();
    expect(screen.getAllByText("Unable to resolve locator")).toHaveLength(2);
    await waitFor(() => expect(screen.getAllByText("role=button name=提交").length).toBeGreaterThan(0));
    expect(screen.getByRole("link", { name: "打开报告" })).toHaveAttribute(
      "href",
      "/api/runs/r1/artifacts/report",
    );
    expect(screen.getByRole("link", { name: "下载 Trace" })).toHaveAttribute(
      "href",
      "/api/runs/r1/artifacts/trace",
    );
    expect(screen.getByAltText("step-010 失败时页面截图")).toHaveAttribute(
      "src",
      "/api/runs/r1/steps/step-010/screenshot",
    );
  });

  it("switches debug detail when a step row is clicked", async () => {
    vi.spyOn(runsApi, "getRun").mockResolvedValue({
      run_id: "r1",
      plan_id: "p1",
      status: "failed",
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
        {
          step_id: "step-010",
          step_type: "click",
          status: "failed",
          duration_ms: 963,
          error: "Unable to resolve locator",
          screenshot: null,
        },
      ],
      trace_path: null,
      video_paths: [],
      report_path: null,
    });
    vi.spyOn(casesApi, "getCase").mockResolvedValue({
      id: "p1",
      name: "Login",
      source: "recording",
      base_url: null,
      parameters: {},
      environment: null,
      steps: [
        { id: "step-001", type: "navigate", name: null, timeout_ms: null, url: "https://x" },
        { id: "step-010", type: "click", name: null, timeout_ms: null },
      ],
    });

    renderAt();

    await waitFor(() => expect(screen.getByText(/运行 r1/)).toBeInTheDocument());
    await userEvent.click(screen.getByRole("button", { name: "step-001" }));
    const detail = screen.getByLabelText("步骤调试详情");
    expect(within(detail).getByText("https://x")).toBeInTheDocument();
  });

  it("shows fill values and press keys in step result summaries", async () => {
    vi.spyOn(runsApi, "getRun").mockResolvedValue({
      run_id: "r1",
      plan_id: "p1",
      status: "passed",
      started_at: "2026-07-05T00:00:00Z",
      ended_at: "2026-07-05T00:00:01Z",
      steps: [
        {
          step_id: "step-003",
          step_type: "fill",
          status: "passed",
          duration_ms: 100,
          error: null,
          screenshot: null,
        },
        {
          step_id: "step-004",
          step_type: "press",
          status: "passed",
          duration_ms: 50,
          error: null,
          screenshot: null,
        },
      ],
      trace_path: null,
      video_paths: [],
      report_path: null,
    });
    vi.spyOn(casesApi, "getCase").mockResolvedValue({
      id: "p1",
      name: "Baidu Search",
      source: "recording",
      base_url: null,
      parameters: {},
      environment: null,
      steps: [
        {
          id: "step-003",
          type: "fill",
          name: null,
          timeout_ms: null,
          value: "王俊凯",
          target: {
            confidence: 0.95,
            primary: {
              strategy: "role",
              value: null,
              role: "textbox",
              name: "湖人双加时93-91逆转热火",
            },
            fallbacks: [],
          },
        },
        {
          id: "step-004",
          type: "press",
          name: null,
          timeout_ms: null,
          key: "Enter",
          target: {
            confidence: 0.95,
            primary: { strategy: "css", value: "#chat-textarea", role: null, name: null },
            fallbacks: [],
          },
        },
      ],
    });

    renderAt();

    await waitFor(() => expect(screen.getAllByText("输入内容：王俊凯").length).toBeGreaterThan(0));
    expect(screen.getAllByText("按键：Enter").length).toBeGreaterThan(0);

    const resultTable = screen.getByRole("table");
    expect(within(resultTable).getByText("输入内容：王俊凯")).toBeInTheDocument();
    expect(within(resultTable).queryByText("role=textbox name=湖人双加时93-91逆转热火")).not.toBeInTheDocument();
  });
});
