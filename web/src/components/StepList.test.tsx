import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { Step } from "../api/types";
import { StepList } from "./StepList";

describe("StepList", () => {
  it("renders a row per step with type", () => {
    const steps: Step[] = [
      { id: "step-001", type: "navigate", name: null, timeout_ms: null, url: "https://x" },
      {
        id: "step-002",
        type: "fill",
        name: null,
        timeout_ms: null,
        value: "alice",
        target: {
          primary: { strategy: "label", value: "Username", role: null, name: null },
          fallbacks: [],
          confidence: 0.9,
        },
      },
    ];

    render(<StepList steps={steps} />);

    expect(screen.getByText("step-001")).toBeInTheDocument();
    expect(screen.getByText("navigate")).toBeInTheDocument();
    expect(screen.getByText("step-002")).toBeInTheDocument();
    expect(screen.getByText("fill")).toBeInTheDocument();
  });
});
