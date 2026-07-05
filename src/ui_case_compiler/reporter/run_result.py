from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Literal, TypeAlias

from pydantic import BaseModel, ConfigDict, Field

StepStatus: TypeAlias = Literal["passed", "failed", "skipped"]
RunStatus: TypeAlias = Literal["passed", "failed"]


class StepResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    step_id: str
    step_type: str
    status: StepStatus
    duration_ms: int = Field(ge=0)
    error: str | None = None
    screenshot: Path | None = None


class RunResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    plan_id: str
    status: RunStatus
    started_at: datetime
    ended_at: datetime
    steps: list[StepResult]
    trace_path: Path | None = None
    video_paths: list[Path] = Field(default_factory=list)
    report_path: Path | None = None

