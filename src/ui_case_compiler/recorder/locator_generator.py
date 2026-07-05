from __future__ import annotations

from typing import TYPE_CHECKING

from ui_case_compiler.errors import RecordingError
from ui_case_compiler.schema.steps import Locator, StepTarget

if TYPE_CHECKING:
    from ui_case_compiler.recorder.recorder_session import RecordedElement


class LocatorGenerator:
    """Create locator candidates using semantic strategies before CSS/XPath."""

    def generate(self, element: RecordedElement) -> StepTarget:
        candidates: list[tuple[Locator, float]] = []
        accessible_name = self._first_text(element.text, element.label, element.placeholder)

        if element.role and accessible_name:
            candidates.append(
                (Locator(strategy="role", role=element.role, name=accessible_name), 0.95)
            )
        if element.label:
            candidates.append((Locator(strategy="label", value=element.label), 0.90))
        if element.placeholder:
            candidates.append((Locator(strategy="placeholder", value=element.placeholder), 0.85))
        if element.test_id:
            candidates.append((Locator(strategy="test_id", value=element.test_id), 0.80))
        if element.text:
            candidates.append((Locator(strategy="text", value=element.text), 0.70))
        if element.css:
            candidates.append((Locator(strategy="css", value=element.css), 0.45))
        if element.xpath:
            candidates.append((Locator(strategy="xpath", value=element.xpath), 0.35))

        locators = self._dedupe(candidates)
        if not locators:
            msg = "Recorded element has no usable locator candidate"
            raise RecordingError(msg)

        primary, confidence = locators[0]
        fallbacks = [locator for locator, _ in locators[1:]]
        return StepTarget(primary=primary, fallbacks=fallbacks, confidence=confidence)

    @staticmethod
    def _first_text(*values: str | None) -> str | None:
        for value in values:
            if value and value.strip():
                return value.strip()
        return None

    @staticmethod
    def _dedupe(candidates: list[tuple[Locator, float]]) -> list[tuple[Locator, float]]:
        seen: set[tuple[str, str | None, str | None, str | None]] = set()
        unique: list[tuple[Locator, float]] = []
        for locator, confidence in candidates:
            key = (locator.strategy, locator.value, locator.role, locator.name)
            if key in seen:
                continue
            seen.add(key)
            unique.append((locator, confidence))
        return unique
