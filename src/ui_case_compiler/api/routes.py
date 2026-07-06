from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse

from ui_case_compiler.api.models import (
    BatchRunRequest,
    CompileNlRequest,
    CompileRecordingRequest,
    DatasetPreviewRequest,
    DatasetPreviewResponse,
    RecordingSessionResponse,
    RunRequest,
    StartRecordingRequest,
    ValidateResponse,
)
from ui_case_compiler.api.service import ApiService
from ui_case_compiler.reporter.batch_result import BatchRunResult
from ui_case_compiler.reporter.run_result import RunResult
from ui_case_compiler.schema.executable_plan import ExecutablePlan
from ui_case_compiler.storage.batch_repository import BatchRunSummary
from ui_case_compiler.storage.case_repository import CaseSummary
from ui_case_compiler.storage.run_repository import RunSummary

router = APIRouter(prefix="/api")


def _service(request: Request) -> ApiService:
    service: ApiService = request.app.state.service
    return service


@router.get("/cases", response_model=list[CaseSummary])
def list_cases(request: Request) -> list[CaseSummary]:
    return _service(request).list_cases()


@router.post("/cases/compile-nl", response_model=ExecutablePlan)
async def compile_nl(request: Request, body: CompileNlRequest) -> ExecutablePlan:
    return await _service(request).compile_nl(body)


@router.post("/cases/compile-recording", response_model=ExecutablePlan)
def compile_recording(request: Request, body: CompileRecordingRequest) -> ExecutablePlan:
    return _service(request).compile_recording(body)


@router.post("/recordings/start", response_model=RecordingSessionResponse)
async def start_recording(
    request: Request,
    body: StartRecordingRequest,
) -> RecordingSessionResponse:
    return await _service(request).start_recording(body)


@router.post("/recordings/{session_id}/stop", response_model=ExecutablePlan)
async def stop_recording(request: Request, session_id: str) -> ExecutablePlan:
    return await _service(request).stop_recording(session_id)


@router.post("/datasets/preview", response_model=DatasetPreviewResponse)
def preview_dataset(request: Request, body: DatasetPreviewRequest) -> DatasetPreviewResponse:
    return _service(request).preview_dataset(body)


@router.get("/cases/{case_id}", response_model=ExecutablePlan)
def get_case(request: Request, case_id: str) -> ExecutablePlan:
    return _service(request).get_case(case_id)


@router.put("/cases/{case_id}", response_model=ExecutablePlan)
def update_case(request: Request, case_id: str, body: ExecutablePlan) -> ExecutablePlan:
    return _service(request).update_case(case_id, body)


@router.post("/cases/{case_id}/validate", response_model=ValidateResponse)
def validate_case(request: Request, case_id: str) -> ValidateResponse:
    return _service(request).validate_case(case_id)


@router.post("/cases/{case_id}/dry-run", response_model=RunResult)
async def dry_run(request: Request, case_id: str, body: RunRequest | None = None) -> RunResult:
    return await _service(request).dry_run(case_id, body or RunRequest())


@router.post("/cases/{case_id}/run", response_model=RunResult)
async def run_case(request: Request, case_id: str, body: RunRequest | None = None) -> RunResult:
    return await _service(request).run(case_id, body or RunRequest())


@router.post("/cases/{case_id}/batch-run", response_model=BatchRunResult)
async def batch_run(
    request: Request,
    case_id: str,
    body: BatchRunRequest,
) -> BatchRunResult:
    return await _service(request).batch_run(case_id, body)


@router.get("/runs", response_model=list[RunSummary])
def list_runs(request: Request) -> list[RunSummary]:
    return _service(request).list_runs()


@router.get("/runs/{run_id}", response_model=RunResult)
def get_run(request: Request, run_id: str) -> RunResult:
    return _service(request).get_run(run_id)


@router.get("/batch-runs", response_model=list[BatchRunSummary])
def list_batch_runs(request: Request) -> list[BatchRunSummary]:
    return _service(request).list_batch_runs()


@router.get("/batch-runs/{batch_id}", response_model=BatchRunResult)
def get_batch_run(request: Request, batch_id: str) -> BatchRunResult:
    return _service(request).get_batch_run(batch_id)


@router.get("/runs/{run_id}/artifacts/{artifact_kind}")
def get_run_artifact(request: Request, run_id: str, artifact_kind: str) -> FileResponse:
    path = _service(request).get_run_artifact_path(run_id, artifact_kind)
    return FileResponse(path)


@router.get("/runs/{run_id}/steps/{step_id}/screenshot")
def get_step_screenshot(request: Request, run_id: str, step_id: str) -> FileResponse:
    path = _service(request).get_step_screenshot_path(run_id, step_id)
    return FileResponse(path, media_type="image/png")
