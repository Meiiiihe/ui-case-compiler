import type { Step } from "../api/types";

function targetSummary(step: Step): string {
  if (!step.target) return "";

  const primary = step.target.primary;
  return primary.role
    ? `role=${primary.role} ${primary.name ?? ""}`
    : `${primary.strategy}=${primary.value ?? ""}`;
}

function summarize(step: Step): string {
  if (step.type === "fill" && step.value !== undefined) {
    return `输入内容：${step.value}`;
  }
  if (step.type === "press" && step.key !== undefined) {
    return `按键：${step.key}`;
  }
  if (step.url) return step.url;
  if (step.expected !== undefined) return `期望：${step.expected}`;
  return targetSummary(step);
}

function stepValue(step: Step): string {
  if (step.type === "press") return step.key ?? "";
  return step.value ?? "";
}

function stepLabel(type: string): string {
  const labels: Record<string, string> = {
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
  return labels[type] ?? type;
}

export function StepList({ steps }: { steps: Step[] }) {
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>步骤</th>
            <th>类型</th>
            <th>目标 / 期望</th>
            <th>输入值 / 按键</th>
          </tr>
        </thead>
        <tbody>
          {steps.map((step, index) => (
            <tr id={step.id} key={step.id}>
              <td>
                <span className="step-index">{index + 1}</span>
                <code>{step.id}</code>
              </td>
              <td>
                <span className="step-type">{stepLabel(step.type)}</span>
                <small>{step.type}</small>
              </td>
              <td>{summarize(step)}</td>
              <td>{stepValue(step)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
