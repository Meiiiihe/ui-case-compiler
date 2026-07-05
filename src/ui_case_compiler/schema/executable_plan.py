from __future__ import annotations

from typing import Any, Literal, TypeAlias

from pydantic import BaseModel, ConfigDict, Field

from ui_case_compiler.schema.steps import Step

PlanSource: TypeAlias = Literal["natural_language", "recording", "manual"]


class ExecutablePlan(BaseModel):
    """A validated UI automation plan that can be executed by the runner."""

    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    source: PlanSource
    base_url: str | None = None
    parameters: dict[str, Any] = Field(default_factory=dict)
    environment: str | None = None
    steps: list[Step] = Field(min_length=1)

