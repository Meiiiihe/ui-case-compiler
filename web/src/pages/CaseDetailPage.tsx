import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { dryRun, getCase, runCase, validateCase } from "../api/cases";
import { BatchRunPanel } from "../components/BatchRunPanel";
import { ErrorBanner } from "../components/ErrorBanner";
import { Spinner } from "../components/Spinner";
import { StepList } from "../components/StepList";
import { useAsync } from "../hooks/useAsync";
import type { ExecutablePlan, RunResult, ValidateResponse } from "../api/types";

function parseParams(text: string): Record<string, string> {
  const params: Record<string, string> = {};
  for (const line of text.split("\n")) {
    const trimmed = line.trim();
    if (!trimmed || !trimmed.includes("=")) continue;
    const [key, ...rest] = trimmed.split("=");
    params[key.trim()] = rest.join("=").trim();
  }
  return params;
}

export function CaseDetailPage() {
  const { caseId } = useParams<{ caseId: string }>();
  const navigate = useNavigate();
  const plan = useAsync<ExecutablePlan>();
  const action = useAsync<RunResult | ValidateResponse>();
  const [paramsText, setParamsText] = useState("");
  const [validateMsg, setValidateMsg] = useState<string | null>(null);

  useEffect(() => {
    if (caseId) void plan.run(() => getCase(caseId));
  }, [caseId, plan.run]);

  if (!caseId) return null;

  const currentCaseId = caseId;
  const runReq = { params: parseParams(paramsText), headed: false };

  async function doValidate() {
    setValidateMsg(null);
    await action.run(async () => {
      const resp = await validateCase(currentCaseId);
      setValidateMsg(resp.valid ? `校验通过（${resp.step_count} 步）` : "校验失败");
      return resp;
    });
  }

  async function doRun(kind: "run" | "dry") {
    await action.run(async () => {
      const result =
        kind === "run" ? await runCase(currentCaseId, runReq) : await dryRun(currentCaseId, runReq);
      navigate(`/runs/${result.run_id}`);
      return result;
    });
  }

  const currentPlan = plan.data;

  return (
    <div className="page-stack">
      <ErrorBanner message={plan.error ?? action.error} />
      <Spinner show={plan.loading} />
      {currentPlan && (
        <>
          <div className="page-title">
            <div>
              <p className="eyebrow">Case Detail</p>
              <h1>{currentPlan.name}</h1>
            </div>
            <span className="source-badge">{currentPlan.source}</span>
          </div>
          <section className="panel meta-panel">
            <div>
              <span className="meta-label">计划 ID</span>
              <code>{currentPlan.id}</code>
            </div>
            <div>
              <span className="meta-label">Base URL</span>
              <span>{currentPlan.base_url ?? "未设置"}</span>
            </div>
            <div>
              <span className="meta-label">步骤数</span>
              <strong>{currentPlan.steps.length}</strong>
            </div>
          </section>
          <section className="panel">
            <div className="section-heading">
              <div>
                <p className="eyebrow">Executable Plan</p>
                <h2>步骤明细</h2>
              </div>
            </div>
            <StepList steps={currentPlan.steps} />
          </section>
          <section className="panel run-panel">
            <div className="section-heading">
              <div>
                <p className="eyebrow">Run Control</p>
                <h2>单次运行</h2>
              </div>
              <span className="hint">每行一个 key=value</span>
            </div>
            <label className="field field-wide">
              <span>运行参数</span>
              <textarea
                aria-label="运行参数"
                value={paramsText}
                onChange={(event) => setParamsText(event.target.value)}
                rows={4}
                spellCheck={false}
                placeholder="loginPageUrl=file:///F:/.../login.html&#10;username=demo@example.com"
              />
            </label>
            <div className="button-row">
              <button className="secondary-action" onClick={doValidate} disabled={action.loading}>
                校验计划
              </button>
              <button className="secondary-action" onClick={() => doRun("dry")} disabled={action.loading}>
                试运行
              </button>
              <button className="primary-action" onClick={() => doRun("run")} disabled={action.loading}>
                正式运行
              </button>
            </div>
            {validateMsg && <p className="success-note">{validateMsg}</p>}
          </section>
          <BatchRunPanel caseId={currentCaseId} />
        </>
      )}
    </div>
  );
}
