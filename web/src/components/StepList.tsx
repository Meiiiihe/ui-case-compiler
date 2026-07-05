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

export function StepList({ steps }: { steps: Step[] }) {
  return (
    <table>
      <thead>
        <tr>
          <th>Step</th>
          <th>Type</th>
          <th>Target/Value</th>
          <th>Value</th>
        </tr>
      </thead>
      <tbody>
        {steps.map((step) => (
          <tr key={step.id}>
            <td>{step.id}</td>
            <td>{step.type}</td>
            <td>{summarize(step)}</td>
            <td>{step.value ?? ""}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
