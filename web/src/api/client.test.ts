import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiError, apiFetch } from "./client";

afterEach(() => {
  vi.restoreAllMocks();
});

function mockFetch(status: number, body: unknown): void {
  vi.stubGlobal(
    "fetch",
    vi.fn(
      async () =>
        new Response(JSON.stringify(body), {
          status,
          headers: { "Content-Type": "application/json" },
        }),
    ),
  );
}

describe("apiFetch", () => {
  it("prefixes /api and returns parsed json on 200", async () => {
    mockFetch(200, { id: "p1" });
    const result = await apiFetch<{ id: string }>("/cases/p1");
    expect(result).toEqual({ id: "p1" });
    expect(fetch).toHaveBeenCalledWith(
      "/api/cases/p1",
      expect.objectContaining({
        headers: expect.objectContaining({ "Content-Type": "application/json" }),
      }),
    );
  });

  it("throws ApiError with backend detail on non-2xx", async () => {
    mockFetch(404, { detail: "Case not found: x" });
    await expect(apiFetch("/cases/x")).rejects.toMatchObject({
      status: 404,
      detail: "Case not found: x",
    });
  });

  it("throws ApiError even when body is not json", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response("boom", { status: 500 })),
    );
    await expect(apiFetch("/cases")).rejects.toBeInstanceOf(ApiError);
  });
});
