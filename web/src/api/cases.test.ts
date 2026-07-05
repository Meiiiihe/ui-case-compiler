import { afterEach, describe, expect, it, vi } from "vitest";
import * as client from "./client";
import { compileNl, listCases, runCase, validateCase } from "./cases";

afterEach(() => vi.restoreAllMocks());

describe("cases api", () => {
  it("listCases calls GET /cases", async () => {
    const spy = vi.spyOn(client, "apiFetch").mockResolvedValue([]);
    await listCases();
    expect(spy).toHaveBeenCalledWith("/cases");
  });

  it("compileNl posts to /cases/compile-nl", async () => {
    const spy = vi.spyOn(client, "apiFetch").mockResolvedValue({ id: "nl" });
    await compileNl({ text: "go", context: { url: "https://x" } });
    expect(spy).toHaveBeenCalledWith(
      "/cases/compile-nl",
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("validateCase posts to /cases/{id}/validate", async () => {
    const spy = vi.spyOn(client, "apiFetch").mockResolvedValue({ valid: true });
    await validateCase("p1");
    expect(spy).toHaveBeenCalledWith(
      "/cases/p1/validate",
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("runCase posts params to /cases/{id}/run", async () => {
    const spy = vi.spyOn(client, "apiFetch").mockResolvedValue({ run_id: "r1" });
    await runCase("p1", { params: { a: "b" }, headed: false });
    expect(spy).toHaveBeenCalledWith(
      "/cases/p1/run",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ params: { a: "b" }, headed: false }),
      }),
    );
  });
});
