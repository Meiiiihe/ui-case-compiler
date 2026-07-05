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

  const passed = data?.steps.filter((s) => s.status === "passed").length ?? 0;
  const failed = data?.steps.filter((s) => s.status === "failed").length ?? 0;
  const skipped = data?.steps.filter((s) => s.status === "skipped").length ?? 0;

  return (
    <div className="page-stack">
      <ErrorBanner message={error} />
      <Spinner show={loading} />
      {data && (
        <>
          <div className="page-title">
            <div>
              <p className="eyebrow">Run Detail</p>
              <h1>运行 {data.run_id}</h1>
            </div>
            <span className={`status-badge ${data.status}`}>{data.status}</span>
          </div>
          <section className="panel meta-panel">
            <div>
              <span className="meta-label">计划</span>
              <code>{data.plan_id}</code>
            </div>
            <div>
              <span className="meta-label">开始</span>
              <span>{data.started_at}</span>
            </div>
            <div>
              <span className="meta-label">结束</span>
              <span>{data.ended_at}</span>
            </div>
          </section>
          <section className="metric-grid">
            <div className="metric passed"><span>通过</span><strong>{passed}</strong></div>
            <div className="metric failed"><span>失败</span><strong>{failed}</strong></div>
            <div className="metric skipped"><span>跳过</span><strong>{skipped}</strong></div>
          </section>
          <section className="panel">
            <div className="section-heading">
              <div>
                <p className="eyebrow">Step Results</p>
                <h2>步骤结果</h2>
              </div>
            </div>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>步骤</th>
                    <th>类型</th>
                    <th>状态</th>
                    <th>耗时</th>
                    <th>错误</th>
                  </tr>
                </thead>
                <tbody>
                  {data.steps.map((s) => (
                    <tr key={s.step_id}>
                      <td><code>{s.step_id}</code></td>
                      <td>{s.step_type}</td>
                      <td><span className={`status-badge ${s.status}`}>{s.status}</span></td>
                      <td>{s.duration_ms} ms</td>
                      <td>{s.error ?? ""}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
          <section className="panel artifact-panel">
            <div className="section-heading">
              <div>
                <p className="eyebrow">Artifacts</p>
                <h2>执行产物</h2>
              </div>
              <span className="hint">当前展示服务端本地路径</span>
            </div>
            <p><span>报告</span><code>{data.report_path ?? "—"}</code></p>
            <p><span>Trace</span><code>{data.trace_path ?? "—"}</code></p>
          </section>
        </>
      )}
    </div>
  );
}
