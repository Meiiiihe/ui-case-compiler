import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import * as casesApi from "../api/cases";
import { CaseListPage } from "./CaseListPage";

afterEach(() => vi.restoreAllMocks());

function renderPage() {
  return render(
    <MemoryRouter>
      <CaseListPage />
    </MemoryRouter>,
  );
}

describe("CaseListPage", () => {
  it("lists cases from the api", async () => {
    vi.spyOn(casesApi, "listCases").mockResolvedValue([
      { id: "p1", name: "Login", source: "manual", step_count: 5 },
    ]);
    renderPage();
    await waitFor(() => expect(screen.getByText("Login")).toBeInTheDocument());
    expect(screen.getByText("p1")).toBeInTheDocument();
  });

  it("compiles a recording on submit", async () => {
    vi.spyOn(casesApi, "listCases").mockResolvedValue([]);
    const compile = vi.spyOn(casesApi, "compileRecording").mockResolvedValue({
      id: "rec-1",
      name: "Rec",
      source: "recording",
      base_url: null,
      parameters: {},
      environment: null,
      steps: [],
    });
    renderPage();

    await userEvent.click(screen.getByRole("button", { name: "录制 JSON" }));
    fireEvent.change(screen.getByLabelText("事件 JSON"), {
      target: { value: '[{"type":"navigation","timestamp":0,"url":"https://x"}]' },
    });
    await userEvent.click(screen.getByRole("button", { name: "从录制创建" }));

    await waitFor(() => expect(compile).toHaveBeenCalled());
  });

  it("shows error when NL url is empty", async () => {
    vi.spyOn(casesApi, "listCases").mockResolvedValue([]);
    renderPage();

    await userEvent.type(screen.getByLabelText("自然语言用例"), "click login");
    await userEvent.click(screen.getByRole("button", { name: "从自然语言创建" }));

    await waitFor(() => expect(screen.getByText(/URL 必填/)).toBeInTheDocument());
  });
});
