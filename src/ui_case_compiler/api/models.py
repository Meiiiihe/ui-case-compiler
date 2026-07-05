from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from ui_case_compiler.compiler.page_context_collector import PageContext


class CompileNlRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str
    context: PageContext
    name: str | None = None


class CompileRecordingRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    events: list[dict[str, object]] = Field(default_factory=list)
    name: str = "Recorded Flow"


class StartRecordingRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    url: str
    name: str = "Recorded Flow"


class RecordingSessionResponse(BaseModel):
    session_id: str
    url: str
    name: str
    status: str = "recording"


class RunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    params: dict[str, str] = Field(default_factory=dict)
    headed: bool = False


class ValidateResponse(BaseModel):
    valid: bool
    plan_id: str
    step_count: int


class ErrorResponse(BaseModel):
    detail: str
