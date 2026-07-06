from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from uuid import uuid4

from playwright.async_api import Page, async_playwright
from pydantic import BaseModel, ConfigDict, Field

from ui_case_compiler.browser_profile import (
    BROWSER_CONTEXT_OPTIONS,
    STEALTH_INIT_SCRIPT,
    browser_launch_args,
)
from ui_case_compiler.config import RuntimeConfig, load_config
from ui_case_compiler.reporter.artifact_manager import ArtifactManager
from ui_case_compiler.reporter.run_result import RunResult, StepResult
from ui_case_compiler.runner.action_executor import ActionExecutor
from ui_case_compiler.runner.assertion_executor import AssertionExecutor
from ui_case_compiler.runner.parameter_resolver import ParameterContext, ParameterResolver
from ui_case_compiler.schema.executable_plan import ExecutablePlan
from ui_case_compiler.schema.steps import (
    AssertTextStep,
    AssertUrlStep,
    AssertValueStep,
    AssertVisibleStep,
    Step,
)


class RunOptions(BaseModel):
    model_config = ConfigDict(extra="forbid")

    headless: bool | None = None
    browser: str | None = None
    timeout_ms: int | None = Field(default=None, gt=0)
    dry_run: bool = False
    stop_on_failure: bool = True
    runtime_params: dict[str, object] = Field(default_factory=dict)
    environment_params: dict[str, object] = Field(default_factory=dict)
    global_params: dict[str, object] = Field(default_factory=dict)
    output_dir: Path | None = None


class PlanRunner:
    """Execute an executable plan with Playwright Python."""

    def __init__(
        self,
        config: RuntimeConfig | None = None,
        action_executor: ActionExecutor | None = None,
        assertion_executor: AssertionExecutor | None = None,
        parameter_resolver: ParameterResolver | None = None,
        artifact_manager: ArtifactManager | None = None,
    ) -> None:
        self._config = config or load_config()
        self._action_executor = action_executor or ActionExecutor()
        self._assertion_executor = assertion_executor or AssertionExecutor()
        self._parameter_resolver = parameter_resolver or ParameterResolver()
        self._artifact_manager = artifact_manager

    async def run(self, plan: ExecutablePlan, options: RunOptions | None = None) -> RunResult:
        options = options or RunOptions()
        run_id = f"run-{uuid4().hex[:8]}"
        output_dir = options.output_dir or self._config.output_dir
        artifact_manager = self._artifact_manager or ArtifactManager(output_dir)
        artifact_dir = artifact_manager.create_run_dir(run_id)
        started_at = datetime.now(UTC)
        trace_path: Path | None = None

        parameter_context = ParameterContext(
            runtime=options.runtime_params,
            case=plan.parameters,
            environment=options.environment_params,
            global_params=options.global_params,
        )

        records: list[StepResult] = []
        failed = False

        async with async_playwright() as playwright:
            browser_name = options.browser or self._config.browser
            browser_type = getattr(playwright, browser_name)
            headless = self._config.headless if options.headless is None else options.headless
            browser = await browser_type.launch(
                headless=headless,
                args=browser_launch_args(browser_name),
            )
            context = await browser.new_context(**BROWSER_CONTEXT_OPTIONS)
            await context.add_init_script(STEALTH_INIT_SCRIPT)
            if self._config.trace_enabled:
                await context.tracing.start(screenshots=True, snapshots=True, sources=True)
            page = await context.new_page()
            page.set_default_timeout(options.timeout_ms or self._config.timeout_ms)

            for index, raw_step in enumerate(plan.steps):
                if failed and options.stop_on_failure:
                    records.append(self._skipped_record(raw_step))
                    continue

                step = self._parameter_resolver.resolve_step(raw_step, parameter_context)
                record = await self._execute_step(page, artifact_manager, artifact_dir, index, step)
                records.append(record)
                failed = record.status == "failed"

            if self._config.trace_enabled:
                trace_path = artifact_manager.trace_path(artifact_dir)
                await context.tracing.stop(path=str(trace_path))
            await context.close()
            await browser.close()

        return RunResult(
            run_id=run_id,
            plan_id=plan.id,
            status="failed" if any(record.status == "failed" for record in records) else "passed",
            started_at=started_at,
            ended_at=datetime.now(UTC),
            steps=records,
            trace_path=trace_path,
        )

    async def _execute_step(
        self,
        page: Page,
        artifact_manager: ArtifactManager,
        artifact_dir: Path,
        index: int,
        step: Step,
    ) -> StepResult:
        started_at = perf_counter()
        try:
            if self._is_assertion(step):
                await self._assertion_executor.execute(page, step)
            else:
                await self._action_executor.execute(page, step)
            return StepResult(
                step_id=step.id,
                step_type=step.type,
                status="passed",
                duration_ms=self._elapsed_ms(started_at),
            )
        except Exception as exc:
            screenshot = await self._capture_screenshot(
                page,
                artifact_manager,
                artifact_dir,
                index,
                step,
            )
            return StepResult(
                step_id=step.id,
                step_type=step.type,
                status="failed",
                duration_ms=self._elapsed_ms(started_at),
                error=str(exc),
                screenshot=screenshot,
            )

    async def _capture_screenshot(
        self,
        page: Page,
        artifact_manager: ArtifactManager,
        artifact_dir: Path,
        index: int,
        step: Step,
    ) -> Path | None:
        if not self._config.screenshot_on_failure:
            return None

        return await artifact_manager.save_screenshot(page, artifact_dir, step.id, index)

    @staticmethod
    def _elapsed_ms(started_at: float) -> int:
        return int((perf_counter() - started_at) * 1000)

    @staticmethod
    def _is_assertion(step: Step) -> bool:
        return isinstance(
            step,
            AssertVisibleStep | AssertTextStep | AssertValueStep | AssertUrlStep,
        )

    @staticmethod
    def _skipped_record(step: Step) -> StepResult:
        return StepResult(
            step_id=step.id,
            step_type=step.type,
            status="skipped",
            duration_ms=0,
        )
