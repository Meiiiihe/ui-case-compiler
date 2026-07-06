from __future__ import annotations

import asyncio
from enum import StrEnum
from time import monotonic
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
    async def click(self, *, force: bool = False) -> None: ...
    async def focus(self) -> None: ...
    async def fill(self, value: str) -> None: ...
    async def type(self, text: str, *, delay: float = 0) -> None: ...
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

    def __init__(self, wait_timeout_ms: int = 5_000, poll_interval_ms: int = 100) -> None:
        self._wait_timeout_ms = wait_timeout_ms
        self._poll_interval_ms = poll_interval_ms

    async def resolve(
        self,
        page: Any,
        target: StepTarget,
        purpose: LocatorPurpose = LocatorPurpose.ACTION,
    ) -> LocatorLike:
        candidates = self._expanded_candidates(page, [target.primary, *target.fallbacks])
        locators = [
            (candidate, self.to_playwright_locator(page, candidate)) for candidate in candidates
        ]
        errors = [""] * len(locators)
        deadline = monotonic() + (self._wait_timeout_ms / 1000)

        while True:
            for index, (candidate, locator) in enumerate(locators):
                try:
                    count = await locator.count()
                except Exception as exc:
                    errors[index] = f"{candidate.strategy}: {exc}"
                    continue

                if count > 0:
                    ready_locator = await self._first_ready_locator(locator, count, purpose)
                    if ready_locator is not None:
                        return ready_locator
                    errors[index] = (
                        f"{candidate.strategy}: matched {count} elements but none were usable for "
                        f"{purpose.value}"
                    )
                    continue
                errors[index] = f"{candidate.strategy}: matched 0 elements"

            if monotonic() >= deadline:
                break
            await asyncio.sleep(self._poll_interval_ms / 1000)

        msg = f"Unable to resolve locator for {purpose.value}; candidates failed: {errors}"
        raise StepExecutionError(msg)

    async def resolve_existing(self, page: Any, target: StepTarget) -> LocatorLike:
        candidates = self._expanded_candidates(page, [target.primary, *target.fallbacks])
        locators = [
            (candidate, self.to_playwright_locator(page, candidate)) for candidate in candidates
        ]
        errors = [""] * len(locators)
        deadline = monotonic() + (self._wait_timeout_ms / 1000)

        while True:
            for index, (candidate, locator) in enumerate(locators):
                try:
                    count = await locator.count()
                except Exception as exc:
                    errors[index] = f"{candidate.strategy}: {exc}"
                    continue

                if count > 0:
                    return locator if count == 1 else locator.nth(0)
                errors[index] = f"{candidate.strategy}: matched 0 elements"

            if monotonic() >= deadline:
                break
            await asyncio.sleep(self._poll_interval_ms / 1000)

        msg = f"Unable to resolve existing locator; candidates failed: {errors}"
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

    def _expanded_candidates(self, page: Any, candidates: list[Locator]) -> list[Locator]:
        expanded: list[Locator] = []
        for candidate in candidates:
            expanded.append(candidate)
            if self._is_baidu_page(page):
                expanded.extend(self._baidu_legacy_candidates(candidate))
        return self._deduplicate_candidates(expanded)

    @staticmethod
    def _is_baidu_page(page: Any) -> bool:
        return "baidu.com" in str(getattr(page, "url", "")).lower()

    def _baidu_legacy_candidates(self, locator: Locator) -> list[Locator]:
        if self._looks_like_baidu_search_input(locator):
            return [
                Locator(strategy="css", value="#chat-textarea"),
                Locator(strategy="css", value="#chat-input-main textarea"),
                Locator(strategy="css", value="#chat-input-main [contenteditable='true']"),
                Locator(strategy="css", value="#chat-input-main .ai-input-editor"),
                Locator(strategy="css", value="#chat-input-main .chat-input-textarea"),
                Locator(strategy="css", value="#chat-input-area"),
                Locator(strategy="css", value="#main-ipt"),
                Locator(strategy="css", value="#kw"),
            ]

        if self._looks_like_baidu_search_submit(locator):
            return [
                Locator(strategy="css", value="#chat-submit-button"),
                Locator(strategy="css", value="#chat-input-main #chat-submit-button"),
                Locator(strategy="css", value="#chat-input-main button[type='submit']"),
                Locator(
                    strategy="css",
                    value="input[type='submit'][value='\u767e\u5ea6\u4e00\u4e0b']",
                ),
                Locator(strategy="css", value="#su"),
                Locator(strategy="role", role="button", name="\u641c\u7d22"),
                Locator(strategy="role", role="button", name="\u767e\u5ea6\u4e00\u4e0b"),
            ]

        return []

    @staticmethod
    def _looks_like_baidu_search_input(locator: Locator) -> bool:
        if locator.strategy == "css" and (locator.value or "").strip() in {
            "#kw",
            "#kw:visible",
            "input#kw",
            "input#kw:visible",
        }:
            return True

        if locator.strategy in {"label", "placeholder"}:
            return (locator.value or "").strip() in {
                "\u641c\u7d22",
                "\u8bf7\u8f93\u5165\u5173\u952e\u8bcd",
                "\u767e\u5ea6\u641c\u7d22",
            }

        return False

    @staticmethod
    def _looks_like_baidu_search_submit(locator: Locator) -> bool:
        if locator.strategy == "css" and (locator.value or "").strip() in {
            "#su",
            "#su:visible",
            "input#su",
            "input#su:visible",
        }:
            return True

        if locator.strategy == "role" and locator.role == "button":
            return (locator.name or "").strip() in {
                "\u767e\u5ea6\u4e00\u4e0b",
                "\u641c\u7d22",
            }

        if locator.strategy == "text":
            return (locator.value or "").strip() in {
                "\u767e\u5ea6\u4e00\u4e0b",
                "\u641c\u7d22",
            }

        return False

    @staticmethod
    def _deduplicate_candidates(candidates: list[Locator]) -> list[Locator]:
        seen: set[tuple[str, str | None, str | None, str | None]] = set()
        deduplicated: list[Locator] = []
        for candidate in candidates:
            key = (candidate.strategy, candidate.value, candidate.role, candidate.name)
            if key in seen:
                continue
            seen.add(key)
            deduplicated.append(candidate)
        return deduplicated

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
