from __future__ import annotations

from enum import StrEnum
from typing import Any, Protocol, cast

from ui_case_compiler.errors import StepExecutionError
from ui_case_compiler.schema.steps import Locator, StepTarget


class LocatorPurpose(StrEnum):
    ACTION = "action"
    ASSERTION = "assertion"
    INPUT = "input"


class LocatorLike(Protocol):
    async def count(self) -> int: ...
    def nth(self, index: int) -> LocatorLike: ...
    async def is_visible(self) -> bool: ...
    async def is_enabled(self) -> bool: ...
    async def is_editable(self) -> bool: ...
    async def click(self) -> None: ...
    async def fill(self, value: str) -> None: ...
    async def select_option(self, value: str) -> object: ...
    async def check(self) -> None: ...
    async def hover(self) -> None: ...


class PageLike(Protocol):
    def get_by_role(self, role: str, *, name: str | None = None) -> LocatorLike: ...
    def get_by_label(self, text: str) -> LocatorLike: ...
    def get_by_placeholder(self, text: str) -> LocatorLike: ...
    def get_by_test_id(self, test_id: str) -> LocatorLike: ...
    def get_by_text(self, text: str) -> LocatorLike: ...
    def locator(self, selector: str) -> LocatorLike: ...


class LocatorResolver:
    """Resolve StepTarget candidates into a Playwright-compatible locator."""

    async def resolve(
        self,
        page: Any,
        target: StepTarget,
        purpose: LocatorPurpose = LocatorPurpose.ACTION,
    ) -> LocatorLike:
        candidates = [target.primary, *target.fallbacks]
        errors: list[str] = []

        for candidate in candidates:
            locator = self.to_playwright_locator(page, candidate)
            try:
                count = await locator.count()
            except Exception as exc:
                errors.append(f"{candidate.strategy}: {exc}")
                continue

            if count > 0:
                ready_locator = await self._first_ready_locator(locator, count, purpose)
                if ready_locator is not None:
                    return ready_locator
                errors.append(
                    f"{candidate.strategy}: matched {count} elements but none were usable for "
                    f"{purpose.value}"
                )
                continue
            errors.append(f"{candidate.strategy}: matched 0 elements")

        msg = f"Unable to resolve locator for {purpose.value}; candidates failed: {errors}"
        raise StepExecutionError(msg)

    def to_playwright_locator(self, page: Any, locator: Locator) -> LocatorLike:
        match locator.strategy:
            case "role":
                return cast(LocatorLike, page.get_by_role(locator.role or "", name=locator.name))
            case "label":
                return cast(LocatorLike, page.get_by_label(locator.value or ""))
            case "placeholder":
                return cast(LocatorLike, page.get_by_placeholder(locator.value or ""))
            case "test_id":
                return cast(LocatorLike, page.get_by_test_id(locator.value or ""))
            case "text":
                return cast(LocatorLike, page.get_by_text(locator.value or ""))
            case "css":
                return cast(LocatorLike, page.locator(locator.value or ""))
            case "xpath":
                return cast(LocatorLike, page.locator(f"xpath={locator.value or ''}"))

    async def _first_ready_locator(
        self,
        locator: LocatorLike,
        count: int,
        purpose: LocatorPurpose,
    ) -> LocatorLike | None:
        for index in range(count):
            candidate = locator.nth(index) if count > 1 else locator
            if await self._is_ready(candidate, purpose):
                return candidate
        return None

    async def _is_ready(self, locator: LocatorLike, purpose: LocatorPurpose) -> bool:
        try:
            if not await locator.is_visible():
                return False
            if (
                purpose in {LocatorPurpose.ACTION, LocatorPurpose.INPUT}
                and not await locator.is_enabled()
            ):
                return False
            if purpose == LocatorPurpose.INPUT and not await locator.is_editable():
                return False
        except Exception:
            return False
        return True
