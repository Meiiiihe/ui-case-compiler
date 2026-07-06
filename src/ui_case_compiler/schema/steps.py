from __future__ import annotations

from typing import Annotated, Literal, TypeAlias

from pydantic import BaseModel, ConfigDict, Field, model_validator

LocatorStrategy: TypeAlias = Literal[
    "role",
    "label",
    "placeholder",
    "test_id",
    "text",
    "css",
    "xpath",
]


class Locator(BaseModel):
    """A single locator candidate for a target element."""

    model_config = ConfigDict(extra="forbid")

    strategy: LocatorStrategy
    value: str | None = None
    role: str | None = None
    name: str | None = None

    @model_validator(mode="after")
    def validate_required_fields(self) -> Locator:
        if self.strategy == "role":
            if not self.role:
                msg = "role locator requires 'role'"
                raise ValueError(msg)
            return self

        if not self.value:
            msg = f"{self.strategy} locator requires 'value'"
            raise ValueError(msg)
        return self


class StepTarget(BaseModel):
    """Primary locator plus optional fallback candidates."""

    model_config = ConfigDict(extra="forbid")

    primary: Locator
    fallbacks: list[Locator] = Field(default_factory=list)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class BaseStep(BaseModel):
    """Common fields shared by all executable steps."""

    model_config = ConfigDict(extra="forbid")

    id: str
    type: str
    name: str | None = None
    timeout_ms: int | None = Field(default=None, gt=0)


class NavigateStep(BaseStep):
    type: Literal["navigate"] = "navigate"
    url: str


class ClickStep(BaseStep):
    type: Literal["click"] = "click"
    target: StepTarget


class FillStep(BaseStep):
    type: Literal["fill"] = "fill"
    target: StepTarget
    value: str


class PressStep(BaseStep):
    type: Literal["press"] = "press"
    target: StepTarget
    key: str


class SelectStep(BaseStep):
    type: Literal["select"] = "select"
    target: StepTarget
    value: str


class CheckStep(BaseStep):
    type: Literal["check"] = "check"
    target: StepTarget
    checked: bool = True


class HoverStep(BaseStep):
    type: Literal["hover"] = "hover"
    target: StepTarget


class WaitStep(BaseStep):
    type: Literal["wait"] = "wait"
    duration_ms: int = Field(gt=0, le=60_000)


class AssertVisibleStep(BaseStep):
    type: Literal["assert_visible"] = "assert_visible"
    target: StepTarget


class AssertTextStep(BaseStep):
    type: Literal["assert_text"] = "assert_text"
    target: StepTarget
    expected: str


class AssertValueStep(BaseStep):
    type: Literal["assert_value"] = "assert_value"
    target: StepTarget
    expected: str


class AssertUrlStep(BaseStep):
    type: Literal["assert_url"] = "assert_url"
    expected: str


Step: TypeAlias = Annotated[
    NavigateStep
    | ClickStep
    | FillStep
    | PressStep
    | SelectStep
    | CheckStep
    | HoverStep
    | WaitStep
    | AssertVisibleStep
    | AssertTextStep
    | AssertValueStep
    | AssertUrlStep,
    Field(discriminator="type"),
]
