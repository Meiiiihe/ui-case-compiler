from __future__ import annotations

import re

from openai import AsyncOpenAI

from ui_case_compiler.config import LLMConfig
from ui_case_compiler.errors import CompilationError

_JSON_HINT = "Return the result as a JSON object."
_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)


class DeepSeekProvider:
    """Real LLM provider backed by DeepSeek's OpenAI-compatible chat API."""

    def __init__(self, config: LLMConfig) -> None:
        if not config.api_key:
            msg = "未配置模型 API key，无法编译"
            raise CompilationError(msg)
        self._model = config.model
        self._client = AsyncOpenAI(
            api_key=config.api_key,
            base_url=config.base_url,
            timeout=config.timeout_s,
        )

    async def generate_plan_json(self, prompt: str) -> str:
        content = self._ensure_json_hint(prompt)
        try:
            response = await self._client.chat.completions.create(
                model=self._model,
                messages=[{"role": "user", "content": content}],
                response_format={"type": "json_object"},
                temperature=0,
            )
        except Exception as exc:  # noqa: BLE001 - wrap any SDK/network failure
            msg = f"模型调用失败: {exc}"
            raise CompilationError(msg) from exc

        raw = response.choices[0].message.content or ""
        return self._extract_json(raw)

    @staticmethod
    def _ensure_json_hint(prompt: str) -> str:
        if "json" in prompt.lower():
            return prompt
        return f"{prompt}\n{_JSON_HINT}"

    @staticmethod
    def _extract_json(raw: str) -> str:
        text = raw.strip()

        fence_match = _FENCE_RE.search(text)
        if fence_match:
            text = fence_match.group(1).strip()

        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end < start:
            msg = "模型未返回可解析的 JSON 对象"
            raise CompilationError(msg)

        return text[start : end + 1]
