from __future__ import annotations

from typing import Protocol

from ui_case_compiler.reporter.run_result import RunResult
from ui_case_compiler.runner.plan_runner import PlanRunner, RunOptions
from ui_case_compiler.schema.executable_plan import ExecutablePlan
from ui_case_compiler.storage.case_repository import CaseRepository, CaseStatus


class PlanRunnerLike(Protocol):
    async def run(self, plan: ExecutablePlan, options: RunOptions | None = None) -> RunResult:
        """Run an executable plan."""


class DryRunService:
    """Run a plan once and update case readiness based on the result."""

    def __init__(
        self,
        runner: PlanRunnerLike | None = None,
        case_repository: CaseRepository | None = None,
    ) -> None:
        self._runner = runner or PlanRunner()
        self._case_repository = case_repository

    async def dry_run(self, plan: ExecutablePlan, options: RunOptions | None = None) -> RunResult:
        run_options = (
            options.model_copy(update={"dry_run": True}) if options else RunOptions(dry_run=True)
        )
        result = await self._runner.run(plan, run_options)

        if self._case_repository is not None:
            status: CaseStatus = "ready" if result.status == "passed" else "draft"
            self._case_repository.mark_status(plan.id, status)

        return result
