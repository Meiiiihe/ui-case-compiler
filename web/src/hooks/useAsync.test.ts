import { act, renderHook, waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ApiError } from "../api/client";
import { useAsync } from "./useAsync";

describe("useAsync", () => {
  it("transitions loading -> data", async () => {
    const { result } = renderHook(() => useAsync<number>());

    await act(async () => {
      await result.current.run(async () => 42);
    });

    await waitFor(() => expect(result.current.data).toBe(42));
    expect(result.current.loading).toBe(false);
    expect(result.current.error).toBeNull();
  });

  it("captures ApiError detail", async () => {
    const { result } = renderHook(() => useAsync<number>());

    await act(async () => {
      await result.current.run(async () => {
        throw new ApiError(400, "缺少 API key");
      });
    });

    await waitFor(() => expect(result.current.error).toBe("缺少 API key"));
    expect(result.current.data).toBeNull();
  });

  it("keeps only the last result when calls race", async () => {
    const { result } = renderHook(() => useAsync<string>());

    await act(async () => {
      const slow = result.current.run(
        () => new Promise<string>((r) => setTimeout(() => r("slow"), 50)),
      );
      const fast = result.current.run(
        () => new Promise<string>((r) => setTimeout(() => r("fast"), 10)),
      );
      await Promise.all([slow, fast]);
    });

    await waitFor(() => expect(result.current.data).toBe("fast"));
  });
});
