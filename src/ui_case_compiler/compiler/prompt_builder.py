from __future__ import annotations

from ui_case_compiler.compiler.page_context_collector import PageContext
from ui_case_compiler.errors import CompilationError

_SCHEMA_SPEC = """\
Output a single JSON object with this exact structure (an ExecutablePlan):

{
  "id": string,                 // kebab-case identifier, e.g. "login-flow"
  "name": string,               // human-readable name
  "source": "natural_language", // always this exact value
  "base_url": string | null,    // optional starting URL
  "steps": [ Step, ... ]        // one or more steps, in order
}

Do NOT add any top-level keys other than the ones above (no "url", no "title").
Do NOT put "source" inside steps; it belongs only at the top level.

Each Step is one of these shapes. Every step MUST have a unique "id" like
"step-001", "step-002" and a "type". Action steps:

  {"id": "step-001", "type": "navigate", "url": string}
  {"id": "step-002", "type": "click",  "target": Target}
  {"id": "step-003", "type": "fill",   "target": Target, "value": string}
  {"id": "step-004", "type": "select", "target": Target, "value": string}
  {"id": "step-005", "type": "check",  "target": Target, "checked": boolean}
  {"id": "step-006", "type": "hover",  "target": Target}
  {"id": "step-007", "type": "wait",   "duration_ms": integer}

Assertion steps:

  {"id": "step-008", "type": "assert_visible", "target": Target}
  {"id": "step-009", "type": "assert_text",  "target": Target, "expected": string}
  {"id": "step-010", "type": "assert_value", "target": Target, "expected": string}
  {"id": "step-011", "type": "assert_url",   "expected": string}

A Target locates one element with a primary locator plus optional fallbacks:

  {
    "primary": Locator,
    "fallbacks": [ Locator, ... ],   // may be empty
    "confidence": number             // 0.0 to 1.0
  }

A Locator uses exactly one strategy. Its required fields depend on strategy:

  {"strategy": "role", "role": string, "name": string}   // role REQUIRES role (+ optional name)
  {"strategy": "label", "value": string}
  {"strategy": "placeholder", "value": string}
  {"strategy": "test_id", "value": string}
  {"strategy": "text", "value": string}
  {"strategy": "css", "value": string}
  {"strategy": "xpath", "value": string}

Do NOT invent keys like "locator_candidates", "expected_value", "label", or
"css" as top-level locator keys. A locator ALWAYS has a "strategy" field, and
non-role strategies carry their selector in "value".

For interactive elements, prefer user-facing locators such as role, label,
placeholder, or text. If you must use a CSS selector for input/click targets,
prefer a visible selector such as "#kw:visible" and include semantic fallbacks
when possible. Never intentionally target hidden elements."""

_EXAMPLE = """\
Example. For the case "打开登录页，输入用户名和密码，点击 Login 按钮，并验证出现 Welcome back"
with URL https://example.test/login, a correct plan is:

{
  "id": "login-flow",
  "name": "Login Flow",
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
     "target": {"primary": {"strategy": "text", "value": "Welcome back"},
                "fallbacks": [{"strategy": "css", "value": "#message"}], "confidence": 0.8},
     "expected": "Welcome back"}
  ]
}"""


class PromptBuilder:
    """Build a strict JSON-only prompt for plan compilation."""

    def build(self, text: str, context: PageContext) -> str:
        if not text.strip():
            msg = "Natural-language case text must not be empty"
            raise CompilationError(msg)

        if not context.url.strip():
            msg = "Page context requires url"
            raise CompilationError(msg)

        return "\n".join(
            [
                "You are compiling a UI test case into an ExecutablePlan JSON object.",
                "Return the JSON object only. No markdown, no comments, no explanation.",
                "",
                _SCHEMA_SPEC,
                "",
                _EXAMPLE,
                "",
                "Page context for the case you must now compile:",
                f"URL: {context.url}",
                f"Title: {context.title or ''}",
                f"Accessibility tree summary: {context.accessibility_tree or ''}",
                f"DOM summary: {context.dom_summary or ''}",
                f"Screenshot path: {context.screenshot_path or ''}",
                "",
                f"User case: {text.strip()}",
                "",
                "Now output the ExecutablePlan JSON object.",
            ]
        )
