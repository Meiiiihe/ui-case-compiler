from __future__ import annotations

from typing import Any, cast

from playwright.async_api import Page, expect

from ui_case_compiler.errors import StepExecutionError
from ui_case_compiler.runner.locator_resolver import LocatorPurpose, LocatorResolver
from ui_case_compiler.schema.steps import (
    AssertTextStep,
    AssertUrlStep,
    AssertValueStep,
    AssertVisibleStep,
    Step,
)


class AssertionExecutor:
    """Execute assertion steps against a Playwright page."""

    def __init__(self, locator_resolver: LocatorResolver | None = None) -> None:
        self._locator_resolver = locator_resolver or LocatorResolver()

    async def execute(self, page: Page, step: Step) -> None:
        if isinstance(step, AssertVisibleStep):
            locator = await self._locator_resolver.resolve(
                page,
                step.target,
                LocatorPurpose.ASSERTION,
            )
            await expect(cast(Any, locator)).to_be_visible()
            return
        if isinstance(step, AssertTextStep):
            locator = await self._locator_resolver.resolve(
                page,
                step.target,
                LocatorPurpose.ASSERTION,
            )
            await expect(cast(Any, locator)).to_contain_text(step.expected)
            return
        if isinstance(step, AssertValueStep):
            locator = await self._locator_resolver.resolve(
                page,
                step.target,
                LocatorPurpose.ASSERTION,
            )
            await expect(cast(Any, locator)).to_have_value(step.expected)
            return
        if isinstance(step, AssertUrlStep):
            await expect(page).to_have_url(step.expected)
            return

        msg = f"Step '{step.type}' is not an assertion step"
        raise StepExecutionError(msg)
