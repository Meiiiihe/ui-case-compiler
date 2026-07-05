from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any, cast

from ui_case_compiler.compiler.llm_provider import LLMProvider
from ui_case_compiler.compiler.page_context_collector import PageContext
from ui_case_compiler.compiler.prompt_builder import PromptBuilder
from ui_case_compiler.errors import CompilationError
from ui_case_compiler.schema.executable_plan import ExecutablePlan
from ui_case_compiler.schema.validation import validate_plan


class NaturalLanguageCompiler:
    """Compile natural-language UI cases into validated executable plans."""

    def __init__(
        self,
        provider: LLMProvider,
        prompt_builder: PromptBuilder | None = None,
    ) -> None:
        self._provider = provider
        self._prompt_builder = prompt_builder or PromptBuilder()

    async def compile(self, text: str, context: PageContext) -> ExecutablePlan:
        prompt = self._prompt_builder.build(text, context)
        raw_plan = await self._provider.generate_plan_json(prompt)
        data = self._parse_plan_json(raw_plan)
        return validate_plan(data)

    @staticmethod
    def _parse_plan_json(raw_plan: str) -> Mapping[str, Any]:
        try:
            data: Any = json.loads(raw_plan)
        except json.JSONDecodeError as exc:
            msg = "LLM provider returned non-JSON content"
            raise CompilationError(msg) from exc

        if not isinstance(data, dict):
            msg = "LLM provider must return a JSON object"
            raise CompilationError(msg)

        return cast(Mapping[str, Any], data)
