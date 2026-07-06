import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { getCase } from "../api/cases";
import { getRun, runArtifactUrl, stepScreenshotUrl } from "../api/runs";
import type { ExecutablePlan, Locator, RunResult, Step, StepResult } from "../api/types";
import { ErrorBanner } from "../components/ErrorBanner";
import { Spinner } from "../components/Spinner";
import { useAsync } from "../hooks/useAsync";

const statusLabels: Record<StepResult["status"] | RunResult["status"], string> = {
  passed: "通过",
  failed: "失败",
  skipped: "跳过",
};

const stepTypeLabels: Record<string, string> = {
  navigate: "打开页面",
  click: "点击",
  fill: "输入",
  press: "按键",
  select: "选择",
  check: "勾选",
  hover: "悬停",
  wait: "等待",
  assert_visible: "断言可见",
  assert_text: "断言文本",
  assert_value: "断言值",
  assert_url: "断言 URL",
};

function formatDate(value: string): string {
  return new Intl.DateTimeFormat("zh-CN", {
    dateStyle: "short",
    timeStyle: "medium",
  }).format(new Date(value));
}

function stepTypeLabel(type: string): string {
  return stepTypeLabels[type] ?? type;
}

function locatorText(locator: Locator): string {
  if (locator.role) {
    return `role=${locator.role}${locator.name ? ` name=${locator.name}` : ""}`;
  }
  return `${locator.strategy}=${locator.value ?? ""}`;
}

function summarizeStep(step: Step | undefined): string {
  if (!step) return "未找到对应的用例步骤";
  if (step.type === "fill" && step.value !== undefined) return `输入内容：${step.value}`;
  if (step.type === "press" && step.key !== undefined) return `按键：${step.key}`;
  if (step.url) return step.url;
  if (step.expected !== undefined) return `期望：${step.expected}`;
  if (step.target) return locatorText(step.target.primary);
  return step.name ?? "";
}

function selectedStepFrom(runResult: RunResult | null, currentId: string | null): string | null {
  if (!runResult?.steps.length) return null;
  if (currentId && runResult.steps.some((step) => step.step_id === currentId)) return currentId;
  return runResult.steps.find((step) => step.status === "failed")?.step_id ?? runResult.steps[0].step_id;
}

function LocatorPanel({ step }: { step: Step | undefined }) {
  if (!step?.target) {
    return <p className="hint">这个步骤没有定位器信息。</p>;
  }

  const locators = [step.target.primary, ...step.target.fallbacks];

  return (
    <div className="locator-list">
      <div className="locator-confidence">
        <span>定位置信度</span>
        <strong>{Math.round(step.target.confidence * 100)}%</strong>
      </div>
      {locators.map((locator, index) => (
        <div className="locator-item" key={`${locator.strategy}-${index}`}>
          <span>{index === 0 ? "主定位器" : `备用 ${index}`}</span>
          <code>{locatorText(locator)}</code>
        </div>
      ))}
    </div>
  );
}

function StepDebugPanel({
  run,
  result,
  plan,
  step,
}: {
  run: RunResult;
  result: StepResult | undefined;
  plan: ExecutablePlan | null;
  step: Step | undefined;
}) {
  if (!result) {
    return (
      <aside className="debug-detail">
        <div className="empty-state">
          <strong>暂无步骤</strong>
          <span>运行结果里还没有可调试的步骤。</span>
        </div>
      </aside>
    );
  }

  const hasScreenshot = Boolean(result.screenshot);

  return (
    <aside className="debug-detail" aria-label="步骤调试详情">
      <div className="debug-detail-header">
        <div>
          <p className="eyebrow">Step Debug</p>
          <h2>{result.step_id}</h2>
        </div>
        <span className={`status-badge ${result.status}`}>{statusLabels[result.status]}</span>
      </div>

      <div className="debug-actions">
        {plan && (
          <Link className="link-button" to={`/cases/${plan.id}#${result.step_id}`}>
            跳到用例步骤
          </Link>
        )}
        {run.report_path && (
          <a className="link-button" href={runArtifactUrl(run.run_id, "report")} target="_blank" rel="noreferrer">
            打开报告
          </a>
        )}
        {run.trace_path && (
          <a className="link-button" href={runArtifactUrl(run.run_id, "trace")}>
            下载 Trace
          </a>
        )}
      </div>

      <dl className="debug-facts">
        <div>
          <dt>动作类型</dt>
          <dd>{stepTypeLabel(result.step_type)}</dd>
        </div>
        <div>
          <dt>耗时</dt>
          <dd>{result.duration_ms} ms</dd>
        </div>
        <div>
          <dt>目标摘要</dt>
          <dd>{summarizeStep(step)}</dd>
        </div>
      </dl>

      {result.error && (
        <div className="failure-box">
          <span>失败原因</span>
          <pre>{result.error}</pre>
        </div>
      )}

      <section className="debug-section">
        <h3>定位器候选</h3>
        <LocatorPanel step={step} />
      </section>

      {hasScreenshot && (
        <section className="debug-section">
          <h3>失败截图</h3>
          <a href={stepScreenshotUrl(run.run_id, result.step_id)} target="_blank" rel="noreferrer">
            <img
              className="failure-screenshot"
              src={stepScreenshotUrl(run.run_id, result.step_id)}
              alt={`${result.step_id} 失败时页面截图`}
            />
          </a>
        </section>
      )}

      <section className="debug-section">
        <h3>原始步骤 DSL</h3>
        <pre className="json-block">{JSON.stringify(step ?? { step_id: result.step_id }, null, 2)}</pre>
      </section>
    </aside>
  );
}

export function RunDetailPage() {
  const { runId } = useParams<{ runId: string }>();
  const runState = useAsync<RunResult>();
  const planState = useAsync<ExecutablePlan>();
  const [selectedStepId, setSelectedStepId] = useState<string | null>(null);

  useEffect(() => {
    if (runId) void runState.run(() => getRun(runId));
  }, [runId, runState.run]);

  useEffect(() => {
    const planId = runState.data?.plan_id;
    if (planId) void planState.run(() => getCase(planId));
  }, [runState.data?.plan_id, planState.run]);

  useEffect(() => {
    setSelectedStepId((current) => selectedStepFrom(runState.data, current));
  }, [runState.data]);

  const passed = runState.data?.steps.filter((step) => step.status === "passed").length ?? 0;
  const failed = runState.data?.steps.filter((step) => step.status === "failed").length ?? 0;
  const skipped = runState.data?.steps.filter((step) => step.status === "skipped").length ?? 0;
  const activeStepId = selectedStepId ?? selectedStepFrom(runState.data, null);

  const selectedResult = useMemo(
    () => runState.data?.steps.find((step) => step.step_id === activeStepId),
    [runState.data, activeStepId],
  );
  const selectedPlanStep = useMemo(
    () => planState.data?.steps.find((step) => step.id === activeStepId),
    [planState.data, activeStepId],
  );

  return (
    <div className="page-stack">
      <ErrorBanner message={runState.error ?? planState.error} />
      <Spinner show={runState.loading || planState.loading} />
      {runState.data && (
        <>
          <div className="page-title">
            <div>
              <p className="eyebrow">Run Detail</p>
              <h1>运行 {runState.data.run_id}</h1>
            </div>
            <span className={`status-badge ${runState.data.status}`}>
              {statusLabels[runState.data.status]}
            </span>
          </div>

          <section className="panel meta-panel">
            <div>
              <span className="meta-label">用例计划</span>
              <code>{runState.data.plan_id}</code>
            </div>
            <div>
              <span className="meta-label">开始时间</span>
              <span>{formatDate(runState.data.started_at)}</span>
            </div>
            <div>
              <span className="meta-label">结束时间</span>
              <span>{formatDate(runState.data.ended_at)}</span>
            </div>
          </section>

          <section className="metric-grid">
            <div className="metric passed"><span>通过</span><strong>{passed}</strong></div>
            <div className="metric failed"><span>失败</span><strong>{failed}</strong></div>
            <div className="metric skipped"><span>跳过</span><strong>{skipped}</strong></div>
          </section>

          <section className="debug-workbench">
            <div className="panel debug-list">
              <div className="section-heading">
                <div>
                  <p className="eyebrow">Step Results</p>
                  <h2>步骤结果</h2>
                </div>
                <span className="hint">点击一行查看截图、定位器和原始步骤</span>
              </div>
              <div className="table-wrap">
                <table className="result-table">
                  <thead>
                    <tr>
                      <th>步骤</th>
                      <th>类型</th>
                      <th>状态</th>
                      <th>耗时</th>
                      <th>摘要</th>
                    </tr>
                  </thead>
                  <tbody>
                    {runState.data.steps.map((step) => {
                      const planStep = planState.data?.steps.find((item) => item.id === step.step_id);
                      const selected = activeStepId === step.step_id;
                      return (
                        <tr
                          className={selected ? "selected-row clickable-row" : "clickable-row"}
                          key={step.step_id}
                          onClick={() => setSelectedStepId(step.step_id)}
                        >
                          <td>
                            <button className="step-select-button" type="button">
                              <code>{step.step_id}</code>
                            </button>
                          </td>
                          <td>{stepTypeLabel(step.step_type)}</td>
                          <td><span className={`status-badge ${step.status}`}>{statusLabels[step.status]}</span></td>
                          <td>{step.duration_ms} ms</td>
                          <td>{step.error ?? summarizeStep(planStep)}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>

            <StepDebugPanel
              run={runState.data}
              result={selectedResult}
              plan={planState.data}
              step={selectedPlanStep}
            />
          </section>
        </>
      )}
    </div>
  );
}
