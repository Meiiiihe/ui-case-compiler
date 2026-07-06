from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from time import perf_counter
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from ui_case_compiler.config import RuntimeConfig, load_config
from ui_case_compiler.reporter.batch_result import BatchCaseResult, BatchRunResult
from ui_case_compiler.reporter.html_reporter import HtmlReporter
from ui_case_compiler.runner.plan_runner import PlanRunner, RunOptions
from ui_case_compiler.schema.executable_plan import ExecutablePlan
from ui_case_compiler.storage.file_store import FileStore
from ui_case_compiler.storage.run_repository import RunRepository


class BatchRunOptions(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rows: list[dict[str, str]] = Field(min_length=1)
    concurrency: int = Field(default=1, ge=1, le=8)
    headed: bool = False


class BatchRunner:
    """Execute one plan multiple times with different runtime parameter rows."""

    def __init__(self, config: RuntimeConfig | None = None) -> None:
        self._config = config or load_config()
        self._runs = RunRepository(FileStore(self._config.output_dir))

    async def run(self, plan: ExecutablePlan, options: BatchRunOptions) -> BatchRunResult:
        batch_id = f"batch-{uuid4().hex[:8]}"
        started_at = datetime.now(UTC)
        semaphore = asyncio.Semaphore(options.concurrency)

        async def run_one(index: int, params: dict[str, str]) -> BatchCaseResult:
            async with semaphore:
                return await self._run_one(plan, index, params, options.headed)

        results = await asyncio.gather(
            *(run_one(index, row) for index, row in enumerate(options.rows, start=1))
        )
        passed = sum(1 for result in results if result.status == "passed")
        failed = len(results) - passed
        return BatchRunResult(
            batch_id=batch_id,
            plan_id=plan.id,
            status="failed" if failed else "passed",
            started_at=started_at,
            ended_at=datetime.now(UTC),
            total=len(results),
            passed=passed,
            failed=failed,
            concurrency=options.concurrency,
            results=results,
        )

    async def _run_one(
        self,
        plan: ExecutablePlan,
        index: int,
        params: dict[str, str],
        headed: bool,
    ) -> BatchCaseResult:
        started = perf_counter()
        try:
            runtime_params: dict[str, object] = {
                key: value for key, value in params.items()
            }
            result = await PlanRunner(self._config).run(
                plan,
                RunOptions(
                    headless=not headed,
                    output_dir=self._config.output_dir,
                    runtime_params=runtime_params,
                ),
            )
            HtmlReporter(self._config.output_dir).render(result)
            self._runs.save_result(result)
            return BatchCaseResult(
                index=index,
                status=result.status,
                params=params,
                run_id=result.run_id,
                duration_ms=self._elapsed_ms(started),
            )
        except Exception as exc:
            return BatchCaseResult(
                index=index,
                status="failed",
                params=params,
                duration_ms=self._elapsed_ms(started),
                error=str(exc),
            )

    @staticmethod
    def _elapsed_ms(started: float) -> int:
        return int((perf_counter() - started) * 1000)
