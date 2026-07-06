from __future__ import annotations

from pathlib import Path

from jinja2 import Template

from ui_case_compiler.reporter.run_result import RunResult

REPORT_TEMPLATE = """<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <title>UI Case Run {{ result.run_id }}</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 24px; color: #1f2937; }
    table { border-collapse: collapse; width: 100%; margin-top: 16px; }
    th, td { border: 1px solid #d1d5db; padding: 8px; text-align: left; }
    th { background: #f3f4f6; }
    .passed { color: #047857; font-weight: 700; }
    .failed { color: #b91c1c; font-weight: 700; }
    .skipped { color: #92400e; font-weight: 700; }
    code { background: #f3f4f6; padding: 2px 4px; }
  </style>
</head>
<body>
  <h1>UI Case Run {{ result.run_id }}</h1>
  <p>Plan: <code>{{ result.plan_id }}</code></p>
  <p>Status: <span class="{{ result.status }}">{{ result.status }}</span></p>
  <p>Started: {{ result.started_at }}</p>
  <p>Ended: {{ result.ended_at }}</p>
  {% if result.trace_path %}
  <p>Trace: <a href="/api/runs/{{ result.run_id }}/artifacts/trace">Download trace.zip</a></p>
  {% endif %}
  <table>
    <thead>
      <tr>
        <th>Step</th>
        <th>Type</th>
        <th>Status</th>
        <th>Duration</th>
        <th>Error</th>
        <th>Screenshot</th>
      </tr>
    </thead>
    <tbody>
      {% for step in result.steps %}
      <tr>
        <td>{{ step.step_id }}</td>
        <td>{{ step.step_type }}</td>
        <td class="{{ step.status }}">{{ step.status }}</td>
        <td>{{ step.duration_ms }} ms</td>
        <td>{{ step.error or "" }}</td>
        <td>
          {% if step.screenshot %}
          <a
            href="/api/runs/{{ result.run_id }}/steps/{{ step.step_id }}/screenshot"
          >View screenshot</a>
          {% endif %}
        </td>
      </tr>
      {% endfor %}
    </tbody>
  </table>
</body>
</html>
"""


class HtmlReporter:
    """Render run results into a self-contained HTML report."""

    def __init__(self, output_dir: Path) -> None:
        self._output_dir = output_dir

    def render(self, result: RunResult) -> Path:
        report_dir = self._output_dir / "reports"
        report_dir.mkdir(parents=True, exist_ok=True)
        report_path = report_dir / f"{result.run_id}.html"
        html = Template(REPORT_TEMPLATE).render(result=result)
        report_path.write_text(html, encoding="utf-8")
        result.report_path = report_path
        return report_path
