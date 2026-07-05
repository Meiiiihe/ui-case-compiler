from pathlib import Path

import pytest
from playwright.async_api import async_playwright


def _script() -> str:
    root = Path(__file__).resolve().parents[2]
    return (root / "src" / "ui_case_compiler" / "recorder" / "recorder_script.js").read_text(
        encoding="utf-8"
    )


def _login_url() -> str:
    root = Path(__file__).resolve().parents[2]
    return (root / "examples" / "pages" / "login.html").resolve().as_uri()


async def _collect_with(actions) -> list[dict]:
    events: list[dict] = []
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        context = await browser.new_context()
        await context.expose_binding(
            "__uicaseRecord",
            lambda source, payload: events.append(payload),
        )
        await context.add_init_script(script=_script())
        page = await context.new_page()
        await page.goto(_login_url())
        await actions(page)
        await page.wait_for_timeout(100)
        await browser.close()
    return events


@pytest.mark.asyncio
async def test_click_captures_button_role_and_text() -> None:
    async def actions(page):
        await page.click("button[type=submit]")

    events = await _collect_with(actions)
    clicks = [e for e in events if e["type"] == "click"]
    assert clicks, "expected at least one click event"
    element = clicks[-1]["element"]
    assert element["tag"] == "button"
    assert element["role"] == "button"
    assert element["text"] == "Login"


@pytest.mark.asyncio
async def test_input_captures_label_from_ancestor_label() -> None:
    async def actions(page):
        await page.fill("#username", "alice")

    events = await _collect_with(actions)
    inputs = [e for e in events if e["type"] == "input"]
    assert inputs, "expected at least one input event"
    last = inputs[-1]
    assert last["value"] == "alice"
    element = last["element"]
    assert element["tag"] == "input"
    assert element["label"] == "Username"
    assert element["role"] == "textbox"
    assert element["css"] == "#username"


@pytest.mark.asyncio
async def test_element_always_has_xpath() -> None:
    async def actions(page):
        await page.click("button[type=submit]")

    events = await _collect_with(actions)
    element = [e for e in events if e["type"] == "click"][-1]["element"]
    assert element["xpath"]
    assert element["xpath"].startswith("/")
