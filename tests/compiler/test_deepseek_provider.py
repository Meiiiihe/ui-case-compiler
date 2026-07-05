import pytest

from ui_case_compiler.compiler.deepseek_provider import DeepSeekProvider
from ui_case_compiler.config import LLMConfig
from ui_case_compiler.errors import CompilationError


class _FakeMessage:
    def __init__(self, content: str) -> None:
        self.content = content


class _FakeChoice:
    def __init__(self, content: str) -> None:
        self.message = _FakeMessage(content)


class _FakeResponse:
    def __init__(self, content: str) -> None:
        self.choices = [_FakeChoice(content)]


class _FakeCompletions:
    def __init__(self, content: str | None = None, error: Exception | None = None) -> None:
        self._content = content
        self._error = error
        self.last_kwargs: dict | None = None

    async def create(self, **kwargs):
        self.last_kwargs = kwargs
        if self._error is not None:
            raise self._error
        assert self._content is not None
        return _FakeResponse(self._content)


class _FakeChat:
    def __init__(self, completions: _FakeCompletions) -> None:
        self.completions = completions


class _FakeClient:
    def __init__(self, completions: _FakeCompletions) -> None:
        self.chat = _FakeChat(completions)


def _provider_with(client: _FakeClient) -> DeepSeekProvider:
    provider = DeepSeekProvider(LLMConfig(api_key="sk-test"))
    provider._client = client  # type: ignore[attr-defined]
    return provider


@pytest.mark.asyncio
async def test_returns_plain_json_unchanged() -> None:
    raw = '{"id": "p", "name": "P", "source": "natural_language", "steps": []}'
    completions = _FakeCompletions(content=raw)
    provider = _provider_with(_FakeClient(completions))

    result = await provider.generate_plan_json("compile this as json")

    assert result == raw


@pytest.mark.asyncio
async def test_strips_markdown_fence() -> None:
    fenced = '```json\n{"id": "p", "name": "P", "source": "natural_language", "steps": []}\n```'
    completions = _FakeCompletions(content=fenced)
    provider = _provider_with(_FakeClient(completions))

    result = await provider.generate_plan_json("json please")

    assert result.startswith("{")
    assert result.endswith("}")
    assert "```" not in result


@pytest.mark.asyncio
async def test_extracts_json_with_surrounding_text() -> None:
    noisy = (
        "Here is the plan:\n"
        '{"id": "p", "name": "P", "source": "natural_language", "steps": []}\n'
        "Done."
    )
    completions = _FakeCompletions(content=noisy)
    provider = _provider_with(_FakeClient(completions))

    result = await provider.generate_plan_json("json")

    assert result.startswith("{")
    assert result.endswith("}")
    assert "Here is" not in result


@pytest.mark.asyncio
async def test_appends_json_hint_when_missing() -> None:
    completions = _FakeCompletions(content='{"a": 1}')
    provider = _provider_with(_FakeClient(completions))

    await provider.generate_plan_json("compile the case")

    sent = completions.last_kwargs["messages"][0]["content"]
    assert "json" in sent.lower()


@pytest.mark.asyncio
async def test_does_not_duplicate_json_hint_when_present() -> None:
    completions = _FakeCompletions(content='{"a": 1}')
    provider = _provider_with(_FakeClient(completions))

    await provider.generate_plan_json("return json object")

    sent = completions.last_kwargs["messages"][0]["content"]
    assert sent == "return json object"


@pytest.mark.asyncio
async def test_sdk_error_wrapped_as_compilation_error() -> None:
    completions = _FakeCompletions(error=RuntimeError("boom"))
    provider = _provider_with(_FakeClient(completions))

    with pytest.raises(CompilationError):
        await provider.generate_plan_json("json")


@pytest.mark.asyncio
async def test_no_json_object_found_raises_compilation_error() -> None:
    completions = _FakeCompletions(content="sorry, I cannot help")
    provider = _provider_with(_FakeClient(completions))

    with pytest.raises(CompilationError):
        await provider.generate_plan_json("json")


@pytest.mark.asyncio
async def test_passes_json_object_response_format() -> None:
    completions = _FakeCompletions(content='{"a": 1}')
    provider = _provider_with(_FakeClient(completions))

    await provider.generate_plan_json("json")

    assert completions.last_kwargs["response_format"] == {"type": "json_object"}
    assert completions.last_kwargs["temperature"] == 0
    assert completions.last_kwargs["model"] == "deepseek-chat"
