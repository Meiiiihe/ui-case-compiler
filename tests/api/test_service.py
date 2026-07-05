from pathlib import Path
from unittest.mock import patch

import pytest

from ui_case_compiler.api.models import (
    CompileNlRequest,
    CompileRecordingRequest,
    RunRequest,
    StartRecordingRequest,
)
from ui_case_compiler.api.service import ApiService, NotFoundError
from ui_case_compiler.compiler.page_context_collector import PageContext
from ui_case_compiler.config import LLMConfig, RuntimeConfig
from ui_case_compiler.recorder.recorder_session import RecordedElement, RecordedEvent
from ui_case_compiler.schema.validation import load_plan


def _config(tmp_path: Path) -> RuntimeConfig:
    return RuntimeConfig(output_dir=tmp_path, llm=LLMConfig(api_key="sk-test"))


def _recording_events() -> list[dict[str, object]]:
    return [
        {"type": "navigation", "timestamp": 0, "url": "https://example.test/login"},
        {
            "type": "click",
            "timestamp": 1,
            "element": {"tag": "button", "role": "button", "text": "Login"},
        },
    ]


def test_compile_recording_saves_and_lists(tmp_path: Path) -> None:
    service = ApiService(_config(tmp_path))

    plan = service.compile_recording(
        CompileRecordingRequest(events=_recording_events(), name="Rec")
    )

    assert plan.source == "recording"
    assert plan.id in {s.id for s in service.list_cases()}


def test_get_case_missing_raises_not_found(tmp_path: Path) -> None:
    service = ApiService(_config(tmp_path))

    with pytest.raises(NotFoundError):
        service.get_case("does-not-exist")


def test_validate_case_reports_valid(tmp_path: Path) -> None:
    service = ApiService(_config(tmp_path))
    plan = service.compile_recording(
        CompileRecordingRequest(events=_recording_events(), name="Rec")
    )

    resp = service.validate_case(plan.id)

    assert resp.valid is True
    assert resp.plan_id == plan.id
    assert resp.step_count == len(plan.steps)


def test_get_run_missing_raises_not_found(tmp_path: Path) -> None:
    service = ApiService(_config(tmp_path))

    with pytest.raises(NotFoundError):
        service.get_run("no-run")


@pytest.mark.asyncio
async def test_compile_nl_uses_provider(tmp_path: Path) -> None:
    service = ApiService(_config(tmp_path))
    fake_json = (
        '{"id": "nl", "name": "NL", "source": "natural_language",'
        ' "steps": [{"id": "step-001", "type": "navigate", "url": "https://example.test"}]}'
    )

    async def fake_generate(self: object, prompt: str) -> str:
        return fake_json

    with patch(
        "ui_case_compiler.compiler.deepseek_provider.DeepSeekProvider.generate_plan_json",
        fake_generate,
    ):
        plan = await service.compile_nl(
            CompileNlRequest(text="go", context=PageContext(url="https://example.test/login"))
        )

    assert plan.source == "natural_language"
    assert plan.id in {s.id for s in service.list_cases()}


@pytest.mark.asyncio
async def test_start_and_stop_recording_saves_plan(tmp_path: Path) -> None:
    service = ApiService(_config(tmp_path))

    async def fake_record(self: object, url: str):
        return [
            RecordedEvent(type="navigation", timestamp=0, url=url),
            RecordedEvent(
                type="click",
                timestamp=1,
                element=RecordedElement(tag="button", role="button", text="Login"),
            ),
        ]

    with patch("ui_case_compiler.recorder.live_recorder.LiveRecorder.record", fake_record):
        started = await service.start_recording(
            StartRecordingRequest(url="https://example.test/login", name="Live Rec")
        )
        plan = await service.stop_recording(started.session_id)

    assert started.status == "recording"
    assert plan.source == "recording"
    assert plan.id in {s.id for s in service.list_cases()}


@pytest.mark.asyncio
async def test_run_against_local_page(tmp_path: Path) -> None:
    service = ApiService(_config(tmp_path))
    root = Path(__file__).resolve().parents[2]
    login_url = (root / "examples" / "pages" / "login.html").resolve().as_uri()
    login_plan = load_plan(root / "examples" / "plans" / "login.json")
    service.update_case(login_plan.id, login_plan)

    result = await service.run(login_plan.id, RunRequest(params={"loginPageUrl": login_url}))

    assert result.status == "passed"
    assert result.run_id in {s.run_id for s in service.list_runs()}
