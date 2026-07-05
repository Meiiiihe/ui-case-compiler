import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { listCases } from "../api/cases";
import { CreateCaseForm } from "../components/CreateCaseForm";
import { ErrorBanner } from "../components/ErrorBanner";
import { Spinner } from "../components/Spinner";
import { useAsync } from "../hooks/useAsync";
import type { CaseSummary } from "../api/types";

export function CaseListPage() {
  const navigate = useNavigate();
  const { data, error, loading, run } = useAsync<CaseSummary[]>();

  useEffect(() => {
    void run(listCases);
  }, [run]);

  return (
    <div className="page-stack">
      <div className="page-title">
        <div>
          <p className="eyebrow">Case Console</p>
          <h1>UI 自动化用例</h1>
        </div>
        <span className="summary-pill">{data?.length ?? 0} 个用例</span>
      </div>
      <CreateCaseForm onCreated={(id) => navigate(`/cases/${id}`)} />
      <section className="panel">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Repository</p>
          <h2>用例列表</h2>
        </div>
        <span className="hint">点击行查看步骤、校验或执行</span>
      </div>
      <ErrorBanner message={error} />
      <Spinner show={loading} />
      {(data ?? []).length === 0 && !loading ? (
        <div className="empty-state">
          <strong>暂无用例</strong>
          <span>使用上方自然语言或录制 JSON 创建第一个可执行计划。</span>
        </div>
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>ID</th>
                <th>名称</th>
                <th>来源</th>
                <th>步骤数</th>
              </tr>
            </thead>
            <tbody>
              {(data ?? []).map((c) => (
                <tr key={c.id} onClick={() => navigate(`/cases/${c.id}`)} className="clickable-row">
                  <td><code>{c.id}</code></td>
                  <td>{c.name}</td>
                  <td><span className="source-badge">{c.source}</span></td>
                  <td>{c.step_count}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      </section>
    </div>
  );
}
