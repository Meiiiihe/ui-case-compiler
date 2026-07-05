import type { Step } from "../api/types";

function summarize(step: Step): string {
  if (step.url) return step.url;
  if (step.expected !== undefined) return `expected: ${step.expected}`;
  if (step.target) {
    const p = step.target.primary;
    return p.role ? `role=${p.role} ${p.name ?? ""}` : `${p.strategy}=${p.value ?? ""}`;
  }
  return "";
}

function stepLabel(type: string): string {
  const labels: Record<string, string> = {
    navigate: "打开页面",
    click: "点击",
    fill: "输入",
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
            <th>输入值</th>
          </tr>
        </thead>
        <tbody>
          {steps.map((step, index) => (
            <tr key={step.id}>
              <td>
                <span className="step-index">{index + 1}</span>
                <code>{step.id}</code>
              </td>
              <td>
                <span className="step-type">{stepLabel(step.type)}</span>
                <small>{step.type}</small>
              </td>
              <td>{summarize(step)}</td>
              <td>{step.value ?? ""}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
