import { useCallback, useRef, useState } from "react";
import { ApiError } from "../api/client";

interface AsyncState<T> {
  data: T | null;
  error: string | null;
  loading: boolean;
  run: (fn: () => Promise<T>) => Promise<void>;
}

export function useAsync<T>(): AsyncState<T> {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const callId = useRef(0);

  const run = useCallback(async (fn: () => Promise<T>) => {
    const id = ++callId.current;
    setLoading(true);
    setError(null);
    try {
      const result = await fn();
      if (id === callId.current) {
        setData(result);
        setLoading(false);
      }
    } catch (err) {
      if (id === callId.current) {
        const message =
          err instanceof ApiError
            ? err.detail
            : err instanceof Error
              ? err.message
              : "未知错误";
        setError(message);
        setLoading(false);
      }
    }
  }, []);

  return { data, error, loading, run };
}
