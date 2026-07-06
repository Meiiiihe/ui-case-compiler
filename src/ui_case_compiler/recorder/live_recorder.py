from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

from playwright.async_api import Frame, Page, async_playwright

from ui_case_compiler.browser_profile import (
    BROWSER_CONTEXT_OPTIONS,
    STEALTH_INIT_SCRIPT,
    browser_launch_args,
)
from ui_case_compiler.config import RuntimeConfig, load_config
from ui_case_compiler.recorder.event_collector import EventCollector
from ui_case_compiler.recorder.recorder_session import RecordedEvent

_SCRIPT_PATH = Path(__file__).with_name("recorder_script.js")
_STOP_PROMPT = "按回车结束录制..."

WaitForStop = Callable[[Page], Awaitable[None]]


class LiveRecorder:
    """Capture live browser interactions via an injected script."""

    def __init__(
        self,
        config: RuntimeConfig | None = None,
        wait_for_stop: WaitForStop | None = None,
    ) -> None:
        self._config = config or load_config()
        self._wait_for_stop = wait_for_stop or self._default_wait_for_stop
        self._collector = EventCollector()

    async def record(self, url: str) -> list[RecordedEvent]:
        raw_events: list[dict[str, Any]] = []
        script = _SCRIPT_PATH.read_text(encoding="utf-8")

        async with async_playwright() as pw:
            browser = await pw.chromium.launch(
                headless=False,
                args=browser_launch_args("chromium"),
            )
            context = await browser.new_context(**BROWSER_CONTEXT_OPTIONS)

            async def on_record(source: Any, payload: dict[str, Any]) -> None:
                raw_events.append(payload)

            await context.expose_binding("__uicaseRecord", on_record)
            await context.add_init_script(STEALTH_INIT_SCRIPT)
            await context.add_init_script(script=script)
            page = await context.new_page()

            def on_navigated(frame: Frame) -> None:
                if frame is page.main_frame:
                    raw_events.append(
                        {"type": "navigation", "timestamp": 0, "url": frame.url}
                    )

            page.on("framenavigated", on_navigated)
            await page.goto(url)
            await self._wait_for_stop(page)
            await browser.close()

        return self._collector.collect(raw_events)

    async def _default_wait_for_stop(self, page: Page) -> None:
        _ = page
        await asyncio.to_thread(input, _STOP_PROMPT)
