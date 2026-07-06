from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

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
from ui_case_compiler.compiler.deepseek_provider import DeepSeekProvider
from ui_case_compiler.compiler.natural_language_compiler import NaturalLanguageCompiler
from ui_case_compiler.config import RuntimeConfig, load_config
from ui_case_compiler.data.table_parser import TableDatasetParser
from ui_case_compiler.errors import (
    CompilationError,
    PlanValidationError,
    RecordingError,
    StorageError,
    UiCaseCompilerError,
)
from ui_case_compiler.recorder.event_collector import EventCollector
from ui_case_compiler.recorder.live_recorder import LiveRecorder
from ui_case_compiler.recorder.recorder_session import RecordedEvent, RecordingCompiler
from ui_case_compiler.reporter.batch_result import BatchRunResult
from ui_case_compiler.reporter.html_reporter import HtmlReporter
from ui_case_compiler.reporter.run_result import RunResult
from ui_case_compiler.runner.batch_runner import BatchRunner, BatchRunOptions
from ui_case_compiler.runner.dry_run_service import DryRunService
from ui_case_compiler.runner.plan_runner import PlanRunner, RunOptions
from ui_case_compiler.schema.executable_plan import ExecutablePlan
from ui_case_compiler.schema.validation import validate_plan
from ui_case_compiler.storage.batch_repository import BatchRunRepository, BatchRunSummary
from ui_case_compiler.storage.case_repository import CaseRepository, CaseSummary
from ui_case_compiler.storage.file_store import FileStore
from ui_case_compiler.storage.run_repository import RunRepository, RunSummary


class NotFoundError(UiCaseCompilerError):
    """Raised when a requested case or run does not exist."""


@dataclass
class RecordingSession:
    session_id: str
    url: str
    name: str
    stop_event: asyncio.Event
    task: asyncio.Task[list[RecordedEvent]]


class ApiService:
    """Orchestrate the existing core for the HTTP API. No HTTP concepts here."""

    def __init__(self, config: RuntimeConfig | None = None) -> None:
        self._config = config or load_config()
        store = FileStore(self._config.output_dir)
        self._cases = CaseRepository(store)
        self._runs = RunRepository(store)
        self._batches = BatchRunRepository(store)
        self._recordings: dict[str, RecordingSession] = {}

    def list_cases(self) -> list[CaseSummary]:
        return self._cases.list_summaries()

    async def compile_nl(self, req: CompileNlRequest) -> ExecutablePlan:
        if not self._config.llm.api_key:
            msg = "未配置模型 API key，请设置环境变量 DEEPSEEK_API_KEY"
            raise CompilationError(msg)
        provider = DeepSeekProvider(self._config.llm)
        compiler = NaturalLanguageCompiler(provider=provider)
        plan = await compiler.compile(req.text, req.context)
        self._cases.save_plan(plan)
        return plan

    def compile_recording(self, req: CompileRecordingRequest) -> ExecutablePlan:
        events = EventCollector().collect(req.events)
        plan = RecordingCompiler().compile(events, req.name)
        self._cases.save_plan(plan)
        return plan

    async def start_recording(self, req: StartRecordingRequest) -> RecordingSessionResponse:
        if not req.url.strip():
            msg = "录制起始 URL 不能为空"
            raise RecordingError(msg)

        session_id = f"rec-{uuid4().hex[:8]}"
        stop_event = asyncio.Event()

        async def wait_for_stop(page: object) -> None:
            _ = page
            await stop_event.wait()

        recorder = LiveRecorder(self._config, wait_for_stop=wait_for_stop)
        task = asyncio.create_task(recorder.record(req.url))
        self._recordings[session_id] = RecordingSession(
            session_id=session_id,
            url=req.url,
            name=req.name,
            stop_event=stop_event,
            task=task,
        )
        return RecordingSessionResponse(session_id=session_id, url=req.url, name=req.name)

    async def stop_recording(self, session_id: str) -> ExecutablePlan:
        session = self._recordings.pop(session_id, None)
        if session is None:
            raise NotFoundError(f"Recording session not found: {session_id}")

        session.stop_event.set()
        events = await session.task
        plan = RecordingCompiler().compile(events, session.name)
        self._cases.save_plan(plan)
        return plan

    def get_case(self, case_id: str) -> ExecutablePlan:
        return self._load_case(case_id)

    def update_case(self, case_id: str, plan: ExecutablePlan) -> ExecutablePlan:
        if plan.id != case_id:
            msg = f"Plan id '{plan.id}' does not match path id '{case_id}'"
            raise PlanValidationError(msg)
        validated = validate_plan(plan.model_dump(mode="json"))
        self._cases.save_plan(validated)
        return validated

    def validate_case(self, case_id: str) -> ValidateResponse:
        plan = self._load_case(case_id)
        validated = validate_plan(plan.model_dump(mode="json"))
        return ValidateResponse(
            valid=True, plan_id=validated.id, step_count=len(validated.steps)
        )

    def preview_dataset(self, req: DatasetPreviewRequest) -> DatasetPreviewResponse:
        dataset = TableDatasetParser().parse(req.filename, req.content_bytes())
        return DatasetPreviewResponse(
            columns=dataset.columns,
            rows=dataset.rows,
            preview_rows=dataset.rows[:20],
            row_count=len(dataset.rows),
        )

    async def dry_run(self, case_id: str, req: RunRequest) -> RunResult:
        plan = self._load_case(case_id)
        service = DryRunService(
            runner=PlanRunner(self._config),
            case_repository=self._cases,
        )
        result = await service.dry_run(plan, self._run_options(req, dry_run=True))
        HtmlReporter(self._config.output_dir).render(result)
        self._runs.save_result(result)
        return result

    async def run(self, case_id: str, req: RunRequest) -> RunResult:
        plan = self._load_case(case_id)
        result = await PlanRunner(self._config).run(plan, self._run_options(req))
        HtmlReporter(self._config.output_dir).render(result)
        self._runs.save_result(result)
        return result

    async def batch_run(self, case_id: str, req: BatchRunRequest) -> BatchRunResult:
        plan = self._load_case(case_id)
        result = await BatchRunner(self._config).run(
            plan,
            BatchRunOptions(
                rows=[{key: str(value) for key, value in row.items()} for row in req.rows],
                concurrency=req.concurrency,
                headed=req.headed,
            ),
        )
        self._batches.save_result(result)
        return result

    def list_runs(self) -> list[RunSummary]:
        return self._runs.list_summaries()

    def list_batch_runs(self) -> list[BatchRunSummary]:
        return self._batches.list_summaries()

    def get_batch_run(self, batch_id: str) -> BatchRunResult:
        try:
            return self._batches.load_result(batch_id)
        except StorageError as exc:
            raise NotFoundError(f"Batch run not found: {batch_id}") from exc

    def get_run(self, run_id: str) -> RunResult:
        try:
            return self._runs.load_result(run_id)
        except StorageError as exc:
            raise NotFoundError(f"Run not found: {run_id}") from exc

    def get_run_artifact_path(self, run_id: str, artifact_kind: str) -> Path:
        result = self.get_run(run_id)
        if artifact_kind == "trace":
            return self._resolve_artifact_path(result.trace_path, "Trace artifact")
        if artifact_kind == "report":
            return self._resolve_artifact_path(result.report_path, "Report artifact")
        raise NotFoundError(f"Unsupported run artifact: {artifact_kind}")

    def get_step_screenshot_path(self, run_id: str, step_id: str) -> Path:
        result = self.get_run(run_id)
        for step in result.steps:
            if step.step_id == step_id:
                return self._resolve_artifact_path(step.screenshot, "Step screenshot")
        raise NotFoundError(f"Step not found in run '{run_id}': {step_id}")

    def _load_case(self, case_id: str) -> ExecutablePlan:
        try:
            return self._cases.load_plan(case_id)
        except StorageError as exc:
            raise NotFoundError(f"Case not found: {case_id}") from exc

    def _resolve_artifact_path(self, path: Path | None, label: str) -> Path:
        if path is None:
            raise NotFoundError(f"{label} is not available")

        candidate = path if path.is_absolute() else Path.cwd() / path
        resolved = candidate.resolve()
        output_root = self._config.output_dir
        output_root = output_root if output_root.is_absolute() else Path.cwd() / output_root
        resolved_root = output_root.resolve()

        try:
            resolved.relative_to(resolved_root)
        except ValueError as exc:
            raise NotFoundError(f"{label} is outside the configured output directory") from exc

        if not resolved.is_file():
            raise NotFoundError(f"{label} file not found: {resolved}")
        return resolved

    def _run_options(self, req: RunRequest, dry_run: bool = False) -> RunOptions:
        return RunOptions(
            headless=not req.headed,
            dry_run=dry_run,
            output_dir=self._config.output_dir,
            runtime_params=dict(req.params),
        )
