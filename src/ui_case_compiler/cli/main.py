from __future__ import annotations

import asyncio
from pathlib import Path

import typer
import uvicorn
from pydantic import ValidationError

from ui_case_compiler import __version__
from ui_case_compiler.api.app import create_app
from ui_case_compiler.compiler import DeepSeekProvider, NaturalLanguageCompiler, PageContext
from ui_case_compiler.config import RuntimeConfig, load_config
from ui_case_compiler.errors import UiCaseCompilerError
from ui_case_compiler.recorder.event_collector import EventCollector
from ui_case_compiler.recorder.live_recorder import LiveRecorder
from ui_case_compiler.recorder.recorder_session import RecordingCompiler
from ui_case_compiler.reporter.html_reporter import HtmlReporter
from ui_case_compiler.reporter.run_result import RunResult
from ui_case_compiler.runner.dry_run_service import DryRunService
from ui_case_compiler.runner.plan_runner import PlanRunner, RunOptions
from ui_case_compiler.schema.executable_plan import ExecutablePlan
from ui_case_compiler.schema.validation import dump_plan, load_plan
from ui_case_compiler.storage.case_repository import CaseRepository
from ui_case_compiler.storage.file_store import FileStore
from ui_case_compiler.storage.run_repository import RunRepository

app = typer.Typer(
    help="编译并执行 UI 自动化测试用例。",
    add_completion=False,
    add_help_option=False,
)


def _show_help(ctx: typer.Context, value: bool) -> None:
    if value:
        typer.echo(ctx.get_help())
        raise typer.Exit()

VERSION_OPTION = typer.Option(False, "--version", help="显示版本号并退出。")
HELP_OPTION = typer.Option(
    False,
    "--help",
    "-h",
    help="显示帮助信息并退出。",
    callback=_show_help,
    is_eager=True,
)
NAME_OPTION = typer.Option("Recorded Flow", "--name", help="生成计划的名称。")
OUTPUT_OPTION = typer.Option(None, "--output", "-o", help="输出计划 JSON 文件路径。")
CONTEXT_OPTION = typer.Option(..., "--context", help="页面上下文 JSON 文件路径。")
OUTPUT_DIR_OPTION = typer.Option(None, "--output-dir", help="执行产物输出目录。")
HEADED_OPTION = typer.Option(False, "--headed", help="使用有界面浏览器运行。")
PARAM_OPTION = typer.Option(None, "--param", help="运行时参数，格式为 key=value。")
HOST_OPTION = typer.Option(None, "--host", help="API 绑定主机，默认 127.0.0.1。")
PORT_OPTION = typer.Option(None, "--port", help="API 端口，默认 8000。")


@app.callback()
def main(
    version: bool = VERSION_OPTION,
    help_requested: bool = HELP_OPTION,
) -> None:
    """UI 用例编译器命令行入口。"""

    _ = help_requested
    if version:
        typer.echo(__version__)
        raise typer.Exit()


@app.command()
def config() -> None:
    """输出默认运行配置。"""

    typer.echo(load_config().model_dump_json(indent=2))


@app.command("serve")
def serve_command(
    host: str | None = HOST_OPTION,
    port: int | None = PORT_OPTION,
) -> None:
    """启动本地 HTTP API 服务（默认绑 127.0.0.1，仅供本地使用）。"""

    config_value = load_config()
    uvicorn.run(
        create_app(config_value),
        host=host or config_value.api.host,
        port=port or config_value.api.port,
    )


@app.command("validate")
def validate_command(plan_path: Path) -> None:
    """校验可执行计划 JSON 文件。"""

    try:
        plan = load_plan(plan_path)
        typer.echo(f"Valid plan: {plan.id} ({len(plan.steps)} steps)")
    except (UiCaseCompilerError, ValidationError, OSError, ValueError) as exc:
        _fail(exc)


@app.command("compile-recording")
def compile_recording_command(
    events_path: Path,
    name: str = NAME_OPTION,
    output: Path | None = OUTPUT_OPTION,
) -> None:
    """将离线录制事件编译为可执行计划。"""

    try:
        events = EventCollector().load_json(events_path)
        plan = RecordingCompiler().compile(events, name)
        _write_or_print_plan(plan, output)
    except (UiCaseCompilerError, ValidationError, OSError, ValueError) as exc:
        _fail(exc)


@app.command("record")
def record_command(
    url: str,
    name: str = NAME_OPTION,
    output: Path | None = OUTPUT_OPTION,
) -> None:
    """启动浏览器实时录制用户操作并编译为可执行计划。"""

    try:
        events = asyncio.run(LiveRecorder().record(url))
        plan = RecordingCompiler().compile(events, name)
        _write_or_print_plan(plan, output)
    except (UiCaseCompilerError, ValidationError, OSError) as exc:
        _fail(exc)


@app.command("compile-nl")
def compile_nl_command(
    text_path: Path,
    context_path: Path = CONTEXT_OPTION,
    output: Path | None = OUTPUT_OPTION,
) -> None:
    """将自然语言用例编译为可执行计划。"""

    try:
        config_value = load_config()
        if not config_value.llm.api_key:
            msg = "未配置模型 API key，请设置环境变量 DEEPSEEK_API_KEY"
            raise UiCaseCompilerError(msg)
        provider = DeepSeekProvider(config_value.llm)
        text = text_path.read_text(encoding="utf-8")
        context = PageContext.model_validate_json(context_path.read_text(encoding="utf-8"))
        plan = asyncio.run(NaturalLanguageCompiler(provider=provider).compile(text, context))
        _write_or_print_plan(plan, output)
    except (UiCaseCompilerError, ValidationError, OSError) as exc:
        _fail(exc)


@app.command("run")
def run_command(
    plan_path: Path,
    output_dir: Path | None = OUTPUT_DIR_OPTION,
    headed: bool = HEADED_OPTION,
    params: list[str] | None = PARAM_OPTION,
) -> None:
    """执行可执行计划并生成报告。"""

    try:
        plan = load_plan(plan_path)
        config_value = _config_with_output(output_dir)
        result = asyncio.run(
            PlanRunner(config_value).run(
                plan,
                RunOptions(
                    headless=not headed,
                    output_dir=config_value.output_dir,
                    runtime_params=_parse_params(params),
                ),
            )
        )
        _persist_and_report(result, config_value.output_dir)
        if result.status == "failed":
            raise typer.Exit(1)
    except typer.Exit:
        raise
    except (UiCaseCompilerError, ValidationError, OSError) as exc:
        _fail(exc)


@app.command("dry-run")
def dry_run_command(
    plan_path: Path,
    output_dir: Path | None = OUTPUT_DIR_OPTION,
    headed: bool = HEADED_OPTION,
    params: list[str] | None = PARAM_OPTION,
) -> None:
    """以试运行模式校验计划是否可用于回归。"""

    try:
        plan = load_plan(plan_path)
        config_value = _config_with_output(output_dir)
        store = FileStore(config_value.output_dir)
        service = DryRunService(
            runner=PlanRunner(config_value),
            case_repository=CaseRepository(store),
        )
        result = asyncio.run(
            service.dry_run(
                plan,
                RunOptions(
                    headless=not headed,
                    dry_run=True,
                    output_dir=config_value.output_dir,
                    runtime_params=_parse_params(params),
                ),
            )
        )
        _persist_and_report(result, config_value.output_dir)
        typer.echo(f"Dry-run status: {'ready' if result.status == 'passed' else 'draft'}")
        if result.status == "failed":
            raise typer.Exit(1)
    except typer.Exit:
        raise
    except (UiCaseCompilerError, ValidationError, OSError) as exc:
        _fail(exc)


def _write_or_print_plan(plan: ExecutablePlan, output: Path | None) -> None:
    if output is None:
        typer.echo(plan.model_dump_json(indent=2))
        return

    dump_plan(plan, output)
    typer.echo(f"Plan written: {output}")


def _config_with_output(output_dir: Path | None) -> RuntimeConfig:
    config_value = load_config()
    if output_dir is None:
        return config_value
    return config_value.model_copy(update={"output_dir": output_dir})


def _parse_params(params: list[str] | None) -> dict[str, object]:
    parsed: dict[str, object] = {}
    for item in params or []:
        if "=" not in item:
            msg = f"Invalid --param value '{item}', expected key=value"
            raise ValueError(msg)
        key, value = item.split("=", 1)
        if not key:
            msg = "Runtime parameter key must not be empty"
            raise ValueError(msg)
        parsed[key] = value
    return parsed


def _persist_and_report(result: RunResult, output_dir: Path) -> None:
    report_path = HtmlReporter(output_dir).render(result)
    RunRepository(FileStore(output_dir)).save_result(result)
    typer.echo(f"Run status: {result.status}")
    typer.echo(f"Report: {report_path}")
    if result.trace_path:
        typer.echo(f"Trace: {result.trace_path}")
    failed_steps = [step for step in result.steps if step.status == "failed"]
    if failed_steps:
        typer.echo("Failures:")
        for step in failed_steps:
            typer.echo(f"- {step.step_id} {step.step_type}: {step.error}")


def _fail(exc: Exception) -> None:
    typer.echo(f"Error: {exc}", err=True)
    raise typer.Exit(1)


if __name__ == "__main__":
    app()
