import pytest

from ui_case_compiler.compiler.context_aware_prompt_builder import (
    ContextAwarePromptBuilder,
)
from ui_case_compiler.compiler.page_context_collector import PageContext
from ui_case_compiler.errors import CompilationError


def _context() -> PageContext:
    return PageContext(
        url="https://example.test/login",
        title="登录",
        dom_summary='{"interactive_elements":[{"label":"用户名"}]}',
    )


def test_prompt_includes_semantic_context_and_case_text() -> None:
    prompt = ContextAwarePromptBuilder().build("输入用户名 admin", _context())

    assert "https://example.test/login" in prompt
    assert '"label":"用户名"' in prompt
    assert "输入用户名 admin" in prompt
    assert "不要凭空编造" in prompt


def test_empty_case_text_raises() -> None:
    with pytest.raises(CompilationError):
        ContextAwarePromptBuilder().build("   ", _context())


def test_empty_url_raises() -> None:
    with pytest.raises(CompilationError):
        ContextAwarePromptBuilder().build("点击登录", PageContext(url=" "))
