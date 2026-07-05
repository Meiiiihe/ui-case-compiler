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
    <div>
      <CreateCaseForm onCreated={(id) => navigate(`/cases/${id}`)} />
      <h2>用例列表</h2>
      <ErrorBanner message={error} />
      <Spinner show={loading} />
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
            <tr
              key={c.id}
              onClick={() => navigate(`/cases/${c.id}`)}
              style={{ cursor: "pointer" }}
            >
              <td>{c.id}</td>
              <td>{c.name}</td>
              <td>{c.source}</td>
              <td>{c.step_count}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
