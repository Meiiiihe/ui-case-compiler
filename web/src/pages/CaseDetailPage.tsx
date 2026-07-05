import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { dryRun, getCase, runCase, validateCase } from "../api/cases";
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
  const planRun = plan.run;

  useEffect(() => {
    if (caseId) void planRun(() => getCase(caseId));
  }, [caseId, planRun]);

  if (!caseId) return null;

  const runReq = { params: parseParams(paramsText), headed: false };

  async function doValidate() {
    setValidateMsg(null);
    await action.run(async () => {
      const resp = await validateCase(caseId!);
      setValidateMsg(resp.valid ? `valid (${resp.step_count} steps)` : "invalid");
      return resp;
    });
  }

  async function doRun(kind: "run" | "dry") {
    await action.run(async () => {
      const result =
        kind === "run" ? await runCase(caseId!, runReq) : await dryRun(caseId!, runReq);
      navigate(`/runs/${result.run_id}`);
      return result;
    });
  }

  const p = plan.data;

  return (
    <div>
      <ErrorBanner message={plan.error ?? action.error} />
      <Spinner show={plan.loading} />
      {p && (
        <>
          <h2>{p.name}</h2>
          <p>
            ID: <code>{p.id}</code> · 来源: {p.source} · base_url: {p.base_url ?? "—"}
          </p>
          <StepList steps={p.steps} />
          <h3>运行参数(每行 key=value)</h3>
          <textarea
            aria-label="运行参数"
            value={paramsText}
            onChange={(e) => setParamsText(e.target.value)}
            rows={3}
          />
          <div>
            <button onClick={doValidate} disabled={action.loading}>
              Validate
            </button>
            <button onClick={() => doRun("dry")} disabled={action.loading}>
              Dry-run
            </button>
            <button onClick={() => doRun("run")} disabled={action.loading}>
              Run
            </button>
          </div>
          {validateMsg && <p>{validateMsg}</p>}
        </>
      )}
    </div>
  );
}
