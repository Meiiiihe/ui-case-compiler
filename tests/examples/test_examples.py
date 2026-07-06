from pathlib import Path

import pytest

from ui_case_compiler.config import RuntimeConfig
from ui_case_compiler.recorder.event_collector import EventCollector
from ui_case_compiler.recorder.recorder_session import RecordingCompiler
from ui_case_compiler.runner.plan_runner import PlanRunner, RunOptions
from ui_case_compiler.schema.validation import load_plan


def test_example_plan_validates() -> None:
    plan = load_plan(_project_root() / "examples" / "plans" / "login.json")

    assert plan.id == "login-example"
    assert len(plan.steps) == 5


def test_example_recording_compiles_to_plan() -> None:
    events = EventCollector().load_json(
        _project_root() / "examples" / "recordings" / "login-events.json"
    )
    plan = RecordingCompiler().compile(events, "Login Recording")

    assert plan.source == "recording"
    assert [step.type for step in plan.steps] == ["navigate", "fill", "fill", "click"]


@pytest.mark.asyncio
async def test_example_plan_runs_against_local_page(tmp_path) -> None:
    plan = load_plan(_project_root() / "examples" / "plans" / "login.json")
    login_page_url = (_project_root() / "examples" / "pages" / "login.html").resolve().as_uri()

    result = await PlanRunner(RuntimeConfig(output_dir=tmp_path)).run(
        plan,
        RunOptions(
            output_dir=tmp_path,
            runtime_params={"loginPageUrl": login_page_url},
        ),
    )

    assert result.status == "passed"


@pytest.mark.asyncio
async def test_example_plan_supports_failed_login_message(tmp_path) -> None:
    plan = load_plan(_project_root() / "examples" / "plans" / "login.json")
    login_page_url = (_project_root() / "examples" / "pages" / "login.html").resolve().as_uri()

    result = await PlanRunner(RuntimeConfig(output_dir=tmp_path)).run(
        plan,
        RunOptions(
            output_dir=tmp_path,
            runtime_params={
                "loginPageUrl": login_page_url,
                "username": "wrong@example.com",
                "password": "bad",
                "expectedText": "Invalid credentials",
            },
        ),
    )

    assert result.status == "passed"


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]
