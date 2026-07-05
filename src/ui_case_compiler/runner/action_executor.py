from __future__ import annotations

from playwright.async_api import Page

from ui_case_compiler.errors import StepExecutionError
from ui_case_compiler.runner.locator_resolver import LocatorPurpose, LocatorResolver
from ui_case_compiler.schema.steps import (
    CheckStep,
    ClickStep,
    FillStep,
    HoverStep,
    NavigateStep,
    SelectStep,
    Step,
    WaitStep,
)


class ActionExecutor:
    """Execute action steps against a Playwright page."""

    def __init__(self, locator_resolver: LocatorResolver | None = None) -> None:
        self._locator_resolver = locator_resolver or LocatorResolver()

    async def execute(self, page: Page, step: Step) -> None:
        if isinstance(step, NavigateStep):
            await page.goto(step.url)
            return
        if isinstance(step, ClickStep):
            locator = await self._locator_resolver.resolve(
                page,
                step.target,
                LocatorPurpose.ACTION,
            )
            await locator.click()
            return
        if isinstance(step, FillStep):
            locator = await self._locator_resolver.resolve(
                page,
                step.target,
                LocatorPurpose.INPUT,
            )
            await locator.fill(step.value)
            return
        if isinstance(step, SelectStep):
            locator = await self._locator_resolver.resolve(
                page,
                step.target,
                LocatorPurpose.INPUT,
            )
            await locator.select_option(step.value)
            return
        if isinstance(step, CheckStep):
            locator = await self._locator_resolver.resolve(
                page,
                step.target,
                LocatorPurpose.ACTION,
            )
            if step.checked:
                await locator.check()
            return
        if isinstance(step, HoverStep):
            locator = await self._locator_resolver.resolve(
                page,
                step.target,
                LocatorPurpose.ACTION,
            )
            await locator.hover()
            return
        if isinstance(step, WaitStep):
            await page.wait_for_timeout(step.duration_ms)
            return

        msg = f"Step '{step.type}' is not an action step"
        raise StepExecutionError(msg)
