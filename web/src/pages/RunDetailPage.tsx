import { useEffect } from "react";
import { useParams } from "react-router-dom";
import { getRun } from "../api/runs";
import { ErrorBanner } from "../components/ErrorBanner";
import { Spinner } from "../components/Spinner";
import { useAsync } from "../hooks/useAsync";
import type { RunResult } from "../api/types";

export function RunDetailPage() {
  const { runId } = useParams<{ runId: string }>();
  const { data, error, loading, run } = useAsync<RunResult>();

  useEffect(() => {
    if (runId) void run(() => getRun(runId));
  }, [runId, run]);

  return (
    <div>
      <ErrorBanner message={error} />
      <Spinner show={loading} />
      {data && (
        <>
          <h2>运行 {data.run_id}</h2>
          <p>
            计划: <code>{data.plan_id}</code> · 状态:{" "}
            <span className={data.status}>{data.status}</span>
          </p>
          <p>
            开始: {data.started_at} · 结束: {data.ended_at}
          </p>
          <table>
            <thead>
              <tr>
                <th>Step</th>
                <th>Type</th>
                <th>Status</th>
                <th>耗时</th>
                <th>Error</th>
              </tr>
            </thead>
            <tbody>
              {data.steps.map((s) => (
                <tr key={s.step_id}>
                  <td>{s.step_id}</td>
                  <td>{s.step_type}</td>
                  <td className={s.status}>{s.status}</td>
                  <td>{s.duration_ms} ms</td>
                  <td>{s.error ?? ""}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <h3>产物(服务端路径)</h3>
          <p>报告: {data.report_path ?? "—"}</p>
          <p>Trace: {data.trace_path ?? "—"}</p>
        </>
      )}
    </div>
  );
}
