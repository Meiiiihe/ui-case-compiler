import pytest

from ui_case_compiler.compiler import NaturalLanguageCompiler, PageContext
from ui_case_compiler.compiler.llm_provider import LLMProvider
from ui_case_compiler.errors import CompilationError, PlanValidationError


class NonJsonProvider:
    async def generate_plan_json(self, prompt: str) -> str:
        return "not json"


class InvalidDslProvider:
    async def generate_plan_json(self, prompt: str) -> str:
        return '{"id": "bad", "name": "Bad", "source": "natural_language", "steps": []}'


class CountingProvider:
    def __init__(self) -> None:
        self.calls = 0

    async def generate_plan_json(self, prompt: str) -> str:
        self.calls += 1
        return (
            '{"id": "ok", "name": "Ok", "source": "natural_language",'
            ' "steps": [{"id": "step-001", "type": "navigate", "url": "https://example.test"}]}'
        )


@pytest.mark.asyncio
async def test_non_json_provider_response_raises_compilation_error() -> None:
    compiler = NaturalLanguageCompiler(provider=NonJsonProvider())
    context = PageContext(url="https://example.test/login")

    with pytest.raises(CompilationError):
        await compiler.compile("Click Login", context)


@pytest.mark.asyncio
async def test_invalid_dsl_provider_response_raises_validation_error() -> None:
    compiler = NaturalLanguageCompiler(provider=InvalidDslProvider())
    context = PageContext(url="https://example.test/login")

    with pytest.raises(PlanValidationError):
        await compiler.compile("Click Login", context)


@pytest.mark.asyncio
async def test_provider_is_only_needed_during_compilation() -> None:
    provider = CountingProvider()
    compiler = NaturalLanguageCompiler(provider=provider)
    context = PageContext(url="https://example.test/login")

    plan = await compiler.compile("Open the page", context)
    _ = plan.model_dump()

    assert provider.calls == 1


def test_provider_protocol_matches_counting_provider() -> None:
    provider: LLMProvider = CountingProvider()

    assert provider is not None
