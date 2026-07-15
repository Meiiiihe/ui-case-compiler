from pathlib import Path

import pytest

from ui_case_compiler.recorder.live_recorder import LiveRecorder
from ui_case_compiler.recorder.recorder_session import RecordedEvent, RecordingCompiler


def _login_url() -> str:
    root = Path(__file__).resolve().parents[2]
    return (root / "examples" / "pages" / "login.html").resolve().as_uri()


def _driver_stop(drive):
    """Build a wait_for_stop hook that drives the page then returns."""

    async def hook(page) -> None:
        await page.wait_for_timeout(100)
        await drive(page)
        await page.wait_for_timeout(100)

    return hook


@pytest.mark.asyncio
async def test_record_collects_navigation_and_interactions() -> None:
    async def drive(page) -> None:
        await page.fill("#username", "alice")
        await page.fill("#password", "secret")
        await page.click("button[type=submit]")

    recorder = LiveRecorder(wait_for_stop=_driver_stop(drive), headless=True)
    events = await recorder.record(_login_url())

    assert all(isinstance(e, RecordedEvent) for e in events)
    types = [e.type for e in events]
    assert types[0] == "navigation"
    assert "input" in types
    assert "click" in types


@pytest.mark.asyncio
async def test_recorded_events_compile_to_plan() -> None:
    async def drive(page) -> None:
        await page.fill("#username", "alice")
        await page.click("button[type=submit]")

    recorder = LiveRecorder(wait_for_stop=_driver_stop(drive), headless=True)
    events = await recorder.record(_login_url())
    plan = RecordingCompiler().compile(events, "Recorded Login")

    assert plan.source == "recording"
    step_types = [s.type for s in plan.steps]
    assert step_types[0] == "navigate"
    assert "fill" in step_types
    assert "click" in step_types
