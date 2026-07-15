from pathlib import Path

import pytest

from ui_case_compiler.compiler.semantic_context_collector import SemanticContextCollector


@pytest.mark.asyncio
async def test_collects_semantic_page_context(tmp_path: Path) -> None:
    page_path = tmp_path / "login.html"
    page_path.write_text(
        """<!doctype html>
<html>
  <head><title>登录页</title></head>
  <body>
    <form id="login-form">
      <label for="username">用户名</label>
      <input id="username" name="username" placeholder="请输入用户名">
      <button type="submit">登录</button>
    </form>
    <p role="status">等待登录</p>
  </body>
</html>
""",
        encoding="utf-8",
    )

    context = await SemanticContextCollector().collect(page_path.resolve().as_uri())

    assert context.title == "登录页"
    assert "等待登录" in context.visible_texts
    assert context.forms[0].form_id == "login-form"
    username = next(
        item for item in context.interactive_elements if item.name == "username"
    )
    assert username.label == "用户名"
    assert any(candidate.strategy == "label" for candidate in username.locator_candidates)
    assert context.assertion_candidates[0].text == "等待登录"
