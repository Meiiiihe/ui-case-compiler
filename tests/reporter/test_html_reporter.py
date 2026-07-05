from datetime import UTC, datetime
from pathlib import Path

from ui_case_compiler.reporter import HtmlReporter, RunResult, StepResult


def test_html_reporter_renders_failed_step(tmp_path: Path) -> None:
    result = RunResult(
        run_id="run-1",
        plan_id="plan-1",
        status="failed",
        started_at=datetime.now(UTC),
        ended_at=datetime.now(UTC),
        steps=[
            StepResult(
                step_id="s1",
                step_type="assert_text",
                status="failed",
                duration_ms=12,
                error="expected text",
            )
        ],
    )

    report_path = HtmlReporter(tmp_path).render(result)

    assert report_path.exists()
    assert result.report_path == report_path
    assert "expected text" in report_path.read_text(encoding="utf-8")

