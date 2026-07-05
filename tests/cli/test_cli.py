import json
from unittest.mock import patch

from typer.testing import CliRunner

from ui_case_compiler.cli.main import app
from ui_case_compiler.schema.executable_plan import ExecutablePlan
from ui_case_compiler.schema.steps import NavigateStep
from ui_case_compiler.schema.validation import dump_plan

runner = CliRunner()


def test_cli_help() -> None:
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "编译并执行 UI 自动化测试用例" in result.output
    assert "校验可执行计划 JSON 文件" in result.output
    assert "将自然语言用例编译为可执行计划" in result.output


def test_validate_command_accepts_valid_plan(tmp_path) -> None:
    plan_path = tmp_path / "plan.json"
    dump_plan(
        ExecutablePlan(
            id="login",
            name="Login",
            source="manual",
            steps=[NavigateStep(id="step-001", url="https://example.test")],
        ),
        plan_path,
    )

    result = runner.invoke(app, ["validate", str(plan_path)])

    assert result.exit_code == 0
    assert "Valid plan: login" in result.output


def test_validate_command_rejects_invalid_plan(tmp_path) -> None:
    plan_path = tmp_path / "plan.json"
    plan_path.write_text('{"id": "bad"}', encoding="utf-8")

    result = runner.invoke(app, ["validate", str(plan_path)])

    assert result.exit_code == 1
    assert "Error:" in result.output


def test_compile_recording_command_writes_plan(tmp_path) -> None:
    events_path = tmp_path / "events.json"
    output_path = tmp_path / "plan.json"
    events_path.write_text(
        json.dumps(
            [
                {
                    "type": "click",
                    "timestamp": 1,
                    "element": {"tag": "button", "role": "button", "text": "Login"},
                }
            ]
        ),
        encoding="utf-8",
    )

    result = runner.invoke(
        app,
        ["compile-recording", str(events_path), "--name", "Login Flow", "-o", str(output_path)],
    )

    assert result.exit_code == 0
    assert output_path.exists()
    assert "recording-login-flow" in output_path.read_text(encoding="utf-8")


def test_compile_nl_command_requires_api_key(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    text_path = tmp_path / "case.txt"
    context_path = tmp_path / "context.json"
    text_path.write_text("Click the Login button", encoding="utf-8")
    context_path.write_text('{"url": "https://example.test/login"}', encoding="utf-8")

    result = runner.invoke(
        app,
        ["compile-nl", str(text_path), "--context", str(context_path)],
    )

    assert result.exit_code == 1
    assert "API key" in result.output


def test_compile_nl_command_writes_plan(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test")
    text_path = tmp_path / "case.txt"
    context_path = tmp_path / "context.json"
    output_path = tmp_path / "plan.json"
    text_path.write_text("Click the Login button", encoding="utf-8")
    context_path.write_text('{"url": "https://example.test/login"}', encoding="utf-8")

    fake_json = (
        '{"id": "nl", "name": "NL", "source": "natural_language",'
        ' "steps": [{"id": "step-001", "type": "navigate", "url": "https://example.test"}]}'
    )

    async def fake_generate(self, prompt: str) -> str:
        return fake_json

    with patch(
        "ui_case_compiler.compiler.deepseek_provider.DeepSeekProvider.generate_plan_json",
        fake_generate,
    ):
        result = runner.invoke(
            app,
            ["compile-nl", str(text_path), "--context", str(context_path), "-o", str(output_path)],
        )

    assert result.exit_code == 0
    assert output_path.exists()
    assert "natural_language" in output_path.read_text(encoding="utf-8")


def test_record_command_writes_plan(tmp_path) -> None:
    output_path = tmp_path / "plan.json"

    events = [
        {"type": "navigation", "timestamp": 0, "url": "https://example.test/login"},
        {
            "type": "input",
            "timestamp": 1,
            "value": "alice",
            "element": {"tag": "input", "label": "Username", "css": "#username"},
        },
        {
            "type": "click",
            "timestamp": 2,
            "element": {"tag": "button", "role": "button", "text": "Login"},
        },
    ]

    async def fake_record(self, url: str):
        from ui_case_compiler.recorder.event_collector import EventCollector

        return EventCollector().collect(events)

    with patch(
        "ui_case_compiler.recorder.live_recorder.LiveRecorder.record",
        fake_record,
    ):
        result = runner.invoke(
            app,
            ["record", "https://example.test/login", "--name", "Rec", "-o", str(output_path)],
        )

    assert result.exit_code == 0
    assert output_path.exists()
    assert "recording" in output_path.read_text(encoding="utf-8")
