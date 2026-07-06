from __future__ import annotations

from datetime import datetime
from typing import Literal, TypeAlias

from pydantic import BaseModel, ConfigDict, Field

BatchStatus: TypeAlias = Literal["passed", "failed"]


class BatchCaseResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    index: int = Field(ge=1)
    status: BatchStatus
    params: dict[str, str]
    run_id: str | None = None
    duration_ms: int = Field(ge=0)
    error: str | None = None


class BatchRunResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    batch_id: str
    plan_id: str
    status: BatchStatus
    started_at: datetime
    ended_at: datetime
    total: int = Field(ge=0)
    passed: int = Field(ge=0)
    failed: int = Field(ge=0)
    concurrency: int = Field(ge=1)
    results: list[BatchCaseResult]
