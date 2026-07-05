from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


class PageContext(BaseModel):
    """Static page context used by the natural-language compiler."""

    model_config = ConfigDict(extra="forbid")

    url: str = Field(min_length=1)
    title: str | None = None
    accessibility_tree: str | None = None
    dom_summary: str | None = None
    screenshot_path: Path | None = None


class PageContextCollector:
    """MVP collector for caller-provided static page context."""

    def collect_static(
        self,
        url: str,
        title: str | None = None,
        accessibility_tree: str | None = None,
        dom_summary: str | None = None,
        screenshot_path: Path | None = None,
    ) -> PageContext:
        return PageContext(
            url=url,
            title=title,
            accessibility_tree=accessibility_tree,
            dom_summary=dom_summary,
            screenshot_path=screenshot_path,
        )
