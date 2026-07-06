from __future__ import annotations

import base64

from pydantic import BaseModel, ConfigDict, Field, field_validator

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


class DatasetPreviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    filename: str
    content_base64: str

    @field_validator("filename")
    @classmethod
    def filename_not_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("文件名不能为空")
        return value

    def content_bytes(self) -> bytes:
        return base64.b64decode(self.content_base64)


class DatasetPreviewResponse(BaseModel):
    columns: list[str]
    rows: list[dict[str, str]]
    preview_rows: list[dict[str, str]]
    row_count: int


class BatchRunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rows: list[dict[str, str]] = Field(min_length=1)
    concurrency: int = Field(default=1, ge=1, le=8)
    headed: bool = False


class ValidateResponse(BaseModel):
    valid: bool
    plan_id: str
    step_count: int


class ErrorResponse(BaseModel):
    detail: str
