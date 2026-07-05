import os
from pathlib import Path

from pydantic import BaseModel, Field


class LLMConfig(BaseModel):
    """Configuration for the compile-time LLM provider (DeepSeek, OpenAI-compatible)."""

    api_key: str | None = None
    base_url: str = "https://api.deepseek.com"
    model: str = "deepseek-chat"
    timeout_s: int = Field(default=60, gt=0)


class RuntimeConfig(BaseModel):
    """Runtime settings shared by CLI, runner, storage, and reporter modules."""

    browser: str = "chromium"
    headless: bool = True
    timeout_ms: int = Field(default=10_000, gt=0)
    output_dir: Path = Path(".ui-case-compiler")
    screenshot_on_failure: bool = True
    trace_enabled: bool = True
    video_enabled: bool = False
    llm: LLMConfig = Field(default_factory=LLMConfig)


def load_config() -> RuntimeConfig:
    """Load runtime configuration, reading LLM settings from the environment."""

    llm = LLMConfig(
        api_key=os.environ.get("DEEPSEEK_API_KEY"),
        base_url=os.environ.get("LLM_BASE_URL", "https://api.deepseek.com"),
        model=os.environ.get("LLM_MODEL", "deepseek-chat"),
    )
    return RuntimeConfig(llm=llm)
