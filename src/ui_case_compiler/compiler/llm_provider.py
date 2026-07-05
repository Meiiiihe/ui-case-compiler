from __future__ import annotations

from typing import Protocol


class LLMProvider(Protocol):
    """Provider abstraction for compile-time plan generation."""

    async def generate_plan_json(self, prompt: str) -> str:
        """Return a JSON string that can be validated as an ExecutablePlan."""
