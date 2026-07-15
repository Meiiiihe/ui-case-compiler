from __future__ import annotations

from ui_case_compiler.compiler.page_context_collector import PageContext
from ui_case_compiler.errors import CompilationError

_SCHEMA_SPEC = """\
你必须只输出一个 JSON 对象，结构必须严格符合 ExecutablePlan：

{
  "id": string,                 // kebab-case 标识，例如 "login-flow"
  "name": string,               // 用例名称
  "source": "natural_language", // 必须固定为这个值
  "base_url": string | null,    // 可选的起始 URL
  "steps": [ Step, ... ]        // 一个或多个按顺序执行的步骤
}

不要添加上述字段之外的顶层字段，例如不要添加 "url"、"title"。
不要把 "source" 放进 steps；它只能出现在顶层。

每个 Step 必须是下面形态之一。每个步骤都必须有唯一的 "id"，例如
"step-001"、"step-002"，并且必须有 "type"。动作步骤：

  {"id": "step-001", "type": "navigate", "url": string}
  {"id": "step-002", "type": "click",  "target": Target}
  {"id": "step-003", "type": "fill",   "target": Target, "value": string}
  {"id": "step-004", "type": "select", "target": Target, "value": string}
  {"id": "step-005", "type": "check",  "target": Target, "checked": boolean}
  {"id": "step-006", "type": "hover",  "target": Target}
  {"id": "step-007", "type": "wait",   "duration_ms": integer}

断言步骤：

  {"id": "step-008", "type": "assert_visible", "target": Target}
  {"id": "step-009", "type": "assert_text",  "target": Target, "expected": string}
  {"id": "step-010", "type": "assert_value", "target": Target, "expected": string}
  {"id": "step-011", "type": "assert_url",   "expected": string}

Target 用来定位一个页面元素，必须包含一个 primary locator 和可选 fallbacks：

  {
    "primary": Locator,
    "fallbacks": [ Locator, ... ],   // 可以为空数组
    "confidence": number             // 0.0 到 1.0
  }

Locator 每次只能使用一种 strategy。不同 strategy 的必填字段如下：

  {"strategy": "role", "role": string, "name": string}   // role 必须有 role，可带 name
  {"strategy": "label", "value": string}
  {"strategy": "placeholder", "value": string}
  {"strategy": "test_id", "value": string}
  {"strategy": "text", "value": string}
  {"strategy": "css", "value": string}
  {"strategy": "xpath", "value": string}

不要发明 "locator_candidates"、"expected_value"、"label" 之类字段。
也不要把 "css" 当作 locator 顶层字段。Locator 必须始终包含 "strategy" 字段；
非 role 策略的选择器或文本统一放在 "value" 字段。

定位可交互元素时，优先使用用户可感知的 locator，例如 role、label、
placeholder 或 text。只有在缺少语义信息时才使用 css/xpath。
如果必须对输入框或点击目标使用 CSS，优先使用可见元素选择器，例如 "#kw:visible"，
并尽量提供语义化 fallbacks。不要故意定位隐藏元素。"""

_EXAMPLE = """\
示例。对于中文用例：
"打开登录页面，输入用户名和密码，点击登录按钮，并验证出现欢迎回来"
起始 URL 为 https://example.test/login，一个正确的计划是：

{
  "id": "login-flow",
  "name": "登录流程",
  "source": "natural_language",
  "base_url": "https://example.test/login",
  "steps": [
    {"id": "step-001", "type": "navigate", "url": "https://example.test/login"},
    {"id": "step-002", "type": "fill",
     "target": {"primary": {"strategy": "label", "value": "Username"},
                "fallbacks": [{"strategy": "css", "value": "#username"}], "confidence": 0.9},
     "value": "testuser"},
    {"id": "step-003", "type": "fill",
     "target": {"primary": {"strategy": "label", "value": "Password"},
                "fallbacks": [{"strategy": "css", "value": "#password"}], "confidence": 0.9},
     "value": "secret"},
    {"id": "step-004", "type": "click",
     "target": {"primary": {"strategy": "role", "role": "button", "name": "Login"},
                "fallbacks": [{"strategy": "text", "value": "Login"}], "confidence": 0.95}},
    {"id": "step-005", "type": "assert_text",
     "target": {"primary": {"strategy": "text", "value": "欢迎回来"},
                "fallbacks": [{"strategy": "css", "value": "#message"}], "confidence": 0.8},
     "expected": "欢迎回来"}
  ]
}"""


class PromptBuilder:
    """Build a strict JSON-only prompt for plan compilation."""

    def build(self, text: str, context: PageContext) -> str:
        if not text.strip():
            msg = "自然语言用例不能为空"
            raise CompilationError(msg)

        if not context.url.strip():
            msg = "页面上下文必须包含 URL"
            raise CompilationError(msg)

        return "\n".join(
            [
                "你是 UI 自动化测试用例编译器，负责把自然语言用例编译为 ExecutablePlan JSON 对象。",
                "只返回 JSON 对象本身。不要返回 Markdown、注释、解释或额外文本。",
                "",
                _SCHEMA_SPEC,
                "",
                _EXAMPLE,
                "",
                "下面是本次需要编译的页面上下文：",
                f"URL: {context.url}",
                f"页面标题: {context.title or ''}",
                f"可访问性树摘要: {context.accessibility_tree or ''}",
                f"DOM 摘要: {context.dom_summary or ''}",
                f"截图路径: {context.screenshot_path or ''}",
                "",
                f"用户用例: {text.strip()}",
                "",
                "现在输出 ExecutablePlan JSON 对象。",
            ]
        )
