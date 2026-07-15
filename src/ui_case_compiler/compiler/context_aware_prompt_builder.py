from __future__ import annotations

from ui_case_compiler.compiler.page_context_collector import PageContext
from ui_case_compiler.compiler.prompt_builder import _EXAMPLE, _SCHEMA_SPEC
from ui_case_compiler.errors import CompilationError

_CONTEXT_AWARE_RULES = """\
Context-Aware 规则：

1. DOM 摘要字段中包含页面语义地图 JSON，包括 visible_texts、interactive_elements、
   forms、assertion_candidates。
2. 生成 click/fill/select/check/assert_text 等需要 target 的步骤时，优先从
   interactive_elements[*].locator_candidates 里选择 locator。
3. 不要凭空编造页面上不存在的 selector、按钮文案、输入框 label 或 test_id。
4. 如果元素有 test_id、label、placeholder、role/text 等多个候选，优先选择更稳定、
   更接近用户语义的 locator，并把其他候选放进 fallbacks。
5. select 步骤的 value 必须使用对应 option 的 value；如果 option value 与中文展示文案相同，
   可以直接使用中文展示文案。
6. 断言优先使用 assertion_candidates 或 visible_texts 中真实存在/操作后会出现的文案。
7. 如果用户用例没有明确写“打开页面”，也必须把 page_url 作为第一步 navigate。
"""


class ContextAwarePromptBuilder:
    """Build a JSON-only prompt that grounds generation on a semantic page map."""

    def build(self, text: str, context: PageContext) -> str:
        if not text.strip():
            msg = "自然语言用例不能为空"
            raise CompilationError(msg)

        if not context.url.strip():
            msg = "页面上下文必须包含 URL"
            raise CompilationError(msg)

        return "\n".join(
            [
                "你是 Context-Aware UI 自动化测试用例编译器。",
                "你的任务是基于真实页面语义地图，把中文自然语言用例编译为 ExecutablePlan JSON。",
                "只返回 JSON 对象本身。不要返回 Markdown、注释、解释或额外文本。",
                "",
                _SCHEMA_SPEC,
                "",
                _CONTEXT_AWARE_RULES,
                "",
                _EXAMPLE,
                "",
                "下面是本次需要编译的页面上下文：",
                f"URL: {context.url}",
                f"页面标题: {context.title or ''}",
                "页面语义地图 JSON:",
                context.dom_summary or "{}",
                "",
                f"用户用例: {text.strip()}",
                "",
                "现在输出 ExecutablePlan JSON 对象。",
            ]
        )
