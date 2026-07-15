import pytest

from ui_case_compiler.compiler.page_context_collector import PageContext
from ui_case_compiler.compiler.prompt_builder import PromptBuilder
from ui_case_compiler.errors import CompilationError


def _context() -> PageContext:
    return PageContext(url="https://example.test/login", title="Login Example")


def test_prompt_includes_case_text_and_url() -> None:
    prompt = PromptBuilder().build("Click Login", _context())

    assert "Click Login" in prompt
    assert "https://example.test/login" in prompt


def test_prompt_describes_required_top_level_fields() -> None:
    prompt = PromptBuilder().build("Click Login", _context())

    assert '"source": "natural_language"' in prompt
    assert '"strategy"' in prompt
    assert '"primary"' in prompt
    assert '"fallbacks"' in prompt


def test_prompt_warns_against_observed_hallucinated_keys() -> None:
    prompt = PromptBuilder().build("Click Login", _context())

    assert "locator_candidates" in prompt
    assert "expected_value" in prompt


def test_prompt_contains_json_keyword_for_json_mode() -> None:
    prompt = PromptBuilder().build("Click Login", _context())

    assert "json" in prompt.lower()


def test_prompt_includes_worked_example() -> None:
    prompt = PromptBuilder().build("Click Login", _context())

    assert '"id": "login-flow"' in prompt
    assert '"expected": "欢迎回来"' in prompt
    assert "打开登录页面" in prompt


def test_empty_case_text_raises() -> None:
    with pytest.raises(CompilationError):
        PromptBuilder().build("   ", _context())


def test_empty_url_raises() -> None:
    with pytest.raises(CompilationError):
        PromptBuilder().build("Click Login", PageContext(url=" "))
