from __future__ import annotations

from pathlib import Path

from playwright.async_api import Page


class ArtifactManager:
    """Manage per-run artifact directories and files."""

    def __init__(self, output_dir: Path) -> None:
        self._output_dir = output_dir

    def create_run_dir(self, run_id: str) -> Path:
        path = self._output_dir / "artifacts" / run_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    async def save_screenshot(self, page: Page, run_dir: Path, step_id: str, index: int) -> Path:
        path = run_dir / f"{index + 1:03d}-{step_id}.png"
        await page.screenshot(path=str(path))
        return path

    def trace_path(self, run_dir: Path) -> Path:
        return run_dir / "trace.zip"

