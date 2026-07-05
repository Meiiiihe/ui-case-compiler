from __future__ import annotations

from ui_case_compiler.api.models import (
    CompileNlRequest,
    CompileRecordingRequest,
    RunRequest,
    ValidateResponse,
)
from ui_case_compiler.compiler.deepseek_provider import DeepSeekProvider
from ui_case_compiler.compiler.natural_language_compiler import NaturalLanguageCompiler
from ui_case_compiler.config import RuntimeConfig, load_config
from ui_case_compiler.errors import (
    CompilationError,
    PlanValidationError,
    StorageError,
    UiCaseCompilerError,
)
from ui_case_compiler.recorder.event_collector import EventCollector
from ui_case_compiler.recorder.recorder_session import RecordingCompiler
from ui_case_compiler.reporter.run_result import RunResult
from ui_case_compiler.runner.dry_run_service import DryRunService
from ui_case_compiler.runner.plan_runner import PlanRunner, RunOptions
from ui_case_compiler.schema.executable_plan import ExecutablePlan
from ui_case_compiler.schema.validation import validate_plan
from ui_case_compiler.storage.case_repository import CaseRepository, CaseSummary
from ui_case_compiler.storage.file_store import FileStore
from ui_case_compiler.storage.run_repository import RunRepository, RunSummary


class NotFoundError(UiCaseCompilerError):
    """Raised when a requested case or run does not exist."""


class ApiService:
    """Orchestrate the existing core for the HTTP API. No HTTP concepts here."""

    def __init__(self, config: RuntimeConfig | None = None) -> None:
        self._config = config or load_config()
        store = FileStore(self._config.output_dir)
        self._cases = CaseRepository(store)
        self._runs = RunRepository(store)

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

    async def dry_run(self, case_id: str, req: RunRequest) -> RunResult:
        plan = self._load_case(case_id)
        service = DryRunService(
            runner=PlanRunner(self._config),
            case_repository=self._cases,
        )
        result = await service.dry_run(plan, self._run_options(req, dry_run=True))
        self._runs.save_result(result)
        return result

    async def run(self, case_id: str, req: RunRequest) -> RunResult:
        plan = self._load_case(case_id)
        result = await PlanRunner(self._config).run(plan, self._run_options(req))
        self._runs.save_result(result)
        return result

    def list_runs(self) -> list[RunSummary]:
        return self._runs.list_summaries()

    def get_run(self, run_id: str) -> RunResult:
        try:
            return self._runs.load_result(run_id)
        except StorageError as exc:
            raise NotFoundError(f"Run not found: {run_id}") from exc

    def _load_case(self, case_id: str) -> ExecutablePlan:
        try:
            return self._cases.load_plan(case_id)
        except StorageError as exc:
            raise NotFoundError(f"Case not found: {case_id}") from exc

    def _run_options(self, req: RunRequest, dry_run: bool = False) -> RunOptions:
        return RunOptions(
            headless=not req.headed,
            dry_run=dry_run,
            output_dir=self._config.output_dir,
            runtime_params=dict(req.params),
        )
