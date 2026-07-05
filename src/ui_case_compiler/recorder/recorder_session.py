from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from ui_case_compiler.errors import RecordingError
from ui_case_compiler.recorder.event_normalizer import EventNormalizer
from ui_case_compiler.recorder.locator_generator import LocatorGenerator
from ui_case_compiler.schema.executable_plan import ExecutablePlan
from ui_case_compiler.schema.steps import (
    CheckStep,
    ClickStep,
    FillStep,
    NavigateStep,
    SelectStep,
    Step,
    StepTarget,
)


class RecordedElement(BaseModel):
    """Element metadata captured by an offline recording event."""

    model_config = ConfigDict(extra="forbid")

    tag: str
    text: str | None = None
    role: str | None = None
    label: str | None = None
    placeholder: str | None = None
    test_id: str | None = None
    css: str | None = None
    xpath: str | None = None


class RecordedEvent(BaseModel):
    """Single browser interaction event from an offline recording stream."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["click", "input", "change", "navigation", "mousemove"]
    timestamp: int = Field(ge=0)
    value: str | None = None
    url: str | None = None
    element: RecordedElement | None = None


class RecordingCompiler:
    """Compile offline recorded events into an executable plan."""

    def __init__(
        self,
        normalizer: EventNormalizer | None = None,
        locator_generator: LocatorGenerator | None = None,
    ) -> None:
        self._normalizer = normalizer or EventNormalizer()
        self._locator_generator = locator_generator or LocatorGenerator()

    def compile(self, events: list[RecordedEvent], name: str) -> ExecutablePlan:
        normalized_events = self._normalizer.normalize(events)
        steps: list[Step] = []

        for event in normalized_events:
            step_id = self._step_id(len(steps) + 1)
            if event.type == "navigation":
                steps.append(self._navigation_step(event, step_id))
            elif event.type == "click":
                steps.append(ClickStep(id=step_id, target=self._target_for(event)))
            elif event.type == "input":
                steps.append(
                    FillStep(
                        id=step_id,
                        target=self._target_for(event),
                        value=self._value_for(event),
                    )
                )
            elif event.type == "change":
                steps.append(self._change_step(event, step_id))

        if not steps:
            msg = "Recorded event stream contains no executable events"
            raise RecordingError(msg)

        return ExecutablePlan(
            id=self._plan_id(name),
            name=name,
            source="recording",
            base_url=self._first_navigation_url(steps),
            steps=steps,
        )

    def _change_step(self, event: RecordedEvent, step_id: str) -> Step:
        element = self._element_for(event)
        target = self._locator_generator.generate(element)
        tag = element.tag.lower()
        role = (element.role or "").lower()

        if tag == "select":
            return SelectStep(id=step_id, target=target, value=self._value_for(event))

        if tag == "checkbox" or role in {"checkbox", "switch"}:
            return CheckStep(id=step_id, target=target, checked=self._checked_for(event))

        return FillStep(id=step_id, target=target, value=self._value_for(event))

    def _navigation_step(self, event: RecordedEvent, step_id: str) -> NavigateStep:
        if not event.url:
            msg = "Navigation event requires url"
            raise RecordingError(msg)
        return NavigateStep(id=step_id, url=event.url)

    def _target_for(self, event: RecordedEvent) -> StepTarget:
        return self._locator_generator.generate(self._element_for(event))

    @staticmethod
    def _element_for(event: RecordedEvent) -> RecordedElement:
        if event.element is None:
            msg = f"{event.type} event requires element metadata"
            raise RecordingError(msg)
        return event.element

    @staticmethod
    def _value_for(event: RecordedEvent) -> str:
        if event.value is None:
            msg = f"{event.type} event requires value"
            raise RecordingError(msg)
        return event.value

    @staticmethod
    def _checked_for(event: RecordedEvent) -> bool:
        if event.value is None:
            return True
        return event.value.strip().lower() in {"1", "true", "yes", "on", "checked"}

    @staticmethod
    def _step_id(index: int) -> str:
        return f"step-{index:03d}"

    @staticmethod
    def _plan_id(name: str) -> str:
        slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
        return f"recording-{slug or 'plan'}"

    @staticmethod
    def _first_navigation_url(steps: list[Step]) -> str | None:
        for step in steps:
            if isinstance(step, NavigateStep):
                return step.url
        return None
