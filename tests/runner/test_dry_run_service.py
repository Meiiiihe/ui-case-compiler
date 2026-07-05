from datetime import UTC, datetime

import pytest

from ui_case_compiler.reporter.run_result import RunResult
from ui_case_compiler.runner.dry_run_service import DryRunService
from ui_case_compiler.runner.plan_runner import RunOptions
from ui_case_compiler.schema.executable_plan import ExecutablePlan
from ui_case_compiler.schema.steps import NavigateStep
from ui_case_compiler.storage.case_repository import CaseRepository
from ui_case_compiler.storage.file_store import FileStore


class FakeRunner:
    def __init__(self, status: str) -> None:
        self.status = status
        self.last_options: RunOptions | None = None

    async def run(self, plan: ExecutablePlan, options: RunOptions | None = None) -> RunResult:
        self.last_options = options
        now = datetime.now(UTC)
        return RunResult(
            run_id="run-test",
            plan_id=plan.id,
            status=self.status,  # type: ignore[arg-type]
            started_at=now,
            ended_at=now,
            steps=[],
        )


def _plan() -> ExecutablePlan:
    return ExecutablePlan(
        id="login",
        name="Login",
        source="manual",
        steps=[NavigateStep(id="step-001", url="https://example.test")],
    )


@pytest.mark.asyncio
async def test_dry_run_marks_case_ready_on_success(tmp_path) -> None:
    runner = FakeRunner("passed")
    repo = CaseRepository(FileStore(tmp_path))
    service = DryRunService(runner=runner, case_repository=repo)

    result = await service.dry_run(_plan())

    assert result.status == "passed"
    assert runner.last_options is not None
    assert runner.last_options.dry_run is True
    assert (tmp_path / "cases" / "login.json").read_text(encoding="utf-8")


@pytest.mark.asyncio
async def test_dry_run_marks_case_draft_on_failure(tmp_path) -> None:
    repo = CaseRepository(FileStore(tmp_path))
    service = DryRunService(runner=FakeRunner("failed"), case_repository=repo)

    await service.dry_run(_plan())

    status_json = (tmp_path / "cases" / "login.json").read_text(encoding="utf-8")
    assert '"status": "draft"' in status_json
