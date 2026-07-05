# v2 子项目① 真实模型 Provider 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 用真实 DeepSeek 模型(OpenAI 兼容接口)替换 MockLLMProvider,实现智能化自然语言编译;去 Mock 化,未配 api_key 即报错。

**Architecture:** 复用 v1 已有的 `LLMProvider` Protocol 扩展点,新增 `DeepSeekProvider` 真实实现并注入 `NaturalLanguageCompiler`,编译管线本身零改动。宽容 JSON 解析与 DeepSeek 的 "json" 字样要求全部封装在 provider 内部。删除 Mock,`compile-nl` 命令在缺失 api_key 时报错退出,不回落。

**Tech Stack:** Python 3.11、openai SDK(走 DeepSeek OpenAI 兼容端点)、Pydantic v2、Typer、pytest / pytest-asyncio、ruff、mypy strict。

## Global Constraints

- Python 版本:`>=3.11`(见 `pyproject.toml`)。
- 目标模型:仅 DeepSeek,通过 `openai>=1.0` SDK 走 OpenAI 兼容接口。不做多 provider 抽象。
- 编译管线(`NaturalLanguageCompiler`、`PromptBuilder`、`schema/`、`runner/`、`reporter/`、`storage/`)零改动。
- 不重写 prompt;不做回环重试;不保留任何 Mock 回落路径。
- 未配置 api_key → 报 `CompilationError`,CLI 非 0 退出,绝不回落 Mock。
- 单元测试不打真实网络;密钥不进测试。
- 全程 ruff + mypy strict 必须绿。
- 配置项:环境变量 `DEEPSEEK_API_KEY`(api_key)、`LLM_BASE_URL`(默认 `https://api.deepseek.com`)、`LLM_MODEL`(默认 `deepseek-chat`)。
- 提交信息结尾:`Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`。

---

## File Structure

- `pyproject.toml` — 新增 `openai>=1.0` 运行依赖。
- `src/ui_case_compiler/config.py` — 新增 `LLMConfig`,挂到 `RuntimeConfig.llm`,`load_config()` 从环境变量读取。
- `src/ui_case_compiler/compiler/deepseek_provider.py`(新) — `DeepSeekProvider`,实现 `LLMProvider` Protocol,负责调用 SDK + "json" 兜底 + 宽容解析 + 异常包装。
- `src/ui_case_compiler/compiler/mock_llm_provider.py` — 删除。
- `src/ui_case_compiler/compiler/natural_language_compiler.py` — `__init__` 的 `provider` 改为必填,去掉 Mock 默认。
- `src/ui_case_compiler/compiler/__init__.py` — 移除 `MockLLMProvider`,新增 `DeepSeekProvider`。
- `src/ui_case_compiler/cli/main.py` — `compile-nl` 检查 api_key 并注入 `DeepSeekProvider`。
- `tests/compiler/test_deepseek_provider.py`(新) — provider 单元测试。
- `tests/compiler/test_natural_language_compiler.py` — 删 Mock 测试,保留 fake-provider 管线测试。
- `tests/cli/test_cli.py` — 重写 `test_compile_nl_command_writes_plan`,新增 api_key 缺失测试。

依赖顺序:Task 1(依赖)→ Task 2(配置)→ Task 3(provider)→ Task 4(去 Mock)→ Task 5(CLI)。

---

### Task 1: 添加 openai 依赖

**Files:**
- Modify: `pyproject.toml:7-13`(dependencies 列表)

**Interfaces:**
- Consumes: 无
- Produces: 运行时可 `import openai`。

- [ ] **Step 1: 修改 pyproject.toml 添加依赖**

把 `dependencies` 列表(当前 `pyproject.toml:7-13`)改为包含 openai:

```toml
dependencies = [
  "playwright>=1.45.0",
  "pydantic>=2.7.0",
  "typer>=0.12.0",
  "jinja2>=3.1.0",
  "rich>=13.7.0",
  "openai>=1.0.0"
]
```

- [ ] **Step 2: 安装依赖**

Run: `.venv/Scripts/python.exe -m pip install -e '.[dev]'`
Expected: 成功安装 openai(及其依赖 httpx 等),无错误。

- [ ] **Step 3: 验证可导入**

Run: `.venv/Scripts/python.exe -c "import openai; print(openai.__version__)"`
Expected: 打印版本号(如 `1.x.x`),无 `ModuleNotFoundError`。

- [ ] **Step 4: 提交**

```bash
git add pyproject.toml
git commit -m "build: 添加 openai 依赖用于 DeepSeek 接入

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 2: 新增 LLMConfig 配置

**Files:**
- Modify: `src/ui_case_compiler/config.py`
- Test: `tests/test_config.py`

**Interfaces:**
- Consumes: 无
- Produces:
  - `LLMConfig(BaseModel)`,字段 `api_key: str | None`、`base_url: str`、`model: str`、`timeout_s: int`。
  - `RuntimeConfig.llm: LLMConfig`。
  - `load_config() -> RuntimeConfig`,从环境变量 `DEEPSEEK_API_KEY` / `LLM_BASE_URL` / `LLM_MODEL` 读取。

- [ ] **Step 1: 写失败测试**

在 `tests/test_config.py` 末尾追加(先看文件顶部已有的 import,复用 `from ui_case_compiler.config import ...`,并新增 `LLMConfig`;若需要 `monkeypatch` 直接用 pytest fixture):

```python
def test_llm_config_defaults(monkeypatch) -> None:
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.delenv("LLM_BASE_URL", raising=False)
    monkeypatch.delenv("LLM_MODEL", raising=False)

    from ui_case_compiler.config import load_config

    config = load_config()

    assert config.llm.api_key is None
    assert config.llm.base_url == "https://api.deepseek.com"
    assert config.llm.model == "deepseek-chat"
    assert config.llm.timeout_s == 60


def test_llm_config_reads_environment(monkeypatch) -> None:
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test")
    monkeypatch.setenv("LLM_BASE_URL", "https://custom.example")
    monkeypatch.setenv("LLM_MODEL", "deepseek-reasoner")

    from ui_case_compiler.config import load_config

    config = load_config()

    assert config.llm.api_key == "sk-test"
    assert config.llm.base_url == "https://custom.example"
    assert config.llm.model == "deepseek-reasoner"
```

确保 `tests/test_config.py` 顶部有 `from ui_case_compiler.config import LLMConfig`(若原文件用其他 import 风格,保持一致;`LLMConfig` 可能仅在函数内 import,如上所示则顶部不必加)。

- [ ] **Step 2: 运行测试确认失败**

Run: `.venv/Scripts/python.exe -m pytest tests/test_config.py -v --basetemp="$TEMP/uicase_pt"`
Expected: 两个新测试 FAIL(`AttributeError: 'RuntimeConfig' object has no attribute 'llm'`)。

- [ ] **Step 3: 实现 LLMConfig 与 load_config**

把 `src/ui_case_compiler/config.py` 完整替换为:

```python
import os
from pathlib import Path

from pydantic import BaseModel, Field


class LLMConfig(BaseModel):
    """Configuration for the compile-time LLM provider (DeepSeek, OpenAI-compatible)."""

    api_key: str | None = None
    base_url: str = "https://api.deepseek.com"
    model: str = "deepseek-chat"
    timeout_s: int = Field(default=60, gt=0)


class RuntimeConfig(BaseModel):
    """Runtime settings shared by CLI, runner, storage, and reporter modules."""

    browser: str = "chromium"
    headless: bool = True
    timeout_ms: int = Field(default=10_000, gt=0)
    output_dir: Path = Path(".ui-case-compiler")
    screenshot_on_failure: bool = True
    trace_enabled: bool = True
    video_enabled: bool = False
    llm: LLMConfig = Field(default_factory=LLMConfig)


def load_config() -> RuntimeConfig:
    """Load runtime configuration, reading LLM settings from the environment."""

    llm = LLMConfig(
        api_key=os.environ.get("DEEPSEEK_API_KEY"),
        base_url=os.environ.get("LLM_BASE_URL", "https://api.deepseek.com"),
        model=os.environ.get("LLM_MODEL", "deepseek-chat"),
    )
    return RuntimeConfig(llm=llm)
```

- [ ] **Step 4: 运行测试确认通过**

Run: `.venv/Scripts/python.exe -m pytest tests/test_config.py -v --basetemp="$TEMP/uicase_pt"`
Expected: 全部 PASS(含原有配置测试)。

- [ ] **Step 5: 类型与风格检查**

Run: `.venv/Scripts/python.exe -m ruff check src/ui_case_compiler/config.py && .venv/Scripts/python.exe -m mypy src`
Expected: ruff All checks passed;mypy Success。

- [ ] **Step 6: 提交**

```bash
git add src/ui_case_compiler/config.py tests/test_config.py
git commit -m "feat: 新增 LLMConfig 从环境变量读取模型配置

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 3: 实现 DeepSeekProvider

**Files:**
- Create: `src/ui_case_compiler/compiler/deepseek_provider.py`
- Test: `tests/compiler/test_deepseek_provider.py`

**Interfaces:**
- Consumes: `LLMConfig`(Task 2);`from ui_case_compiler.errors import CompilationError`。
- Produces:
  - `DeepSeekProvider`,`__init__(self, config: LLMConfig)`。
  - `async def generate_plan_json(self, prompt: str) -> str`(满足 `LLMProvider` Protocol)。
  - 内部行为:prompt 无 "json" 字样时追加提示;调 SDK 带 `response_format={"type": "json_object"}`、`temperature=0`;宽容解析剥 markdown 围栏;SDK/网络异常包装为 `CompilationError`。

- [ ] **Step 1: 写失败测试**

创建 `tests/compiler/test_deepseek_provider.py`:

```python
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
    noisy = 'Here is the plan:\n{"id": "p", "name": "P", "source": "natural_language", "steps": []}\nDone.'
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
```

- [ ] **Step 2: 运行测试确认失败**

Run: `.venv/Scripts/python.exe -m pytest tests/compiler/test_deepseek_provider.py -v --basetemp="$TEMP/uicase_pt"`
Expected: FAIL(`ModuleNotFoundError: No module named 'ui_case_compiler.compiler.deepseek_provider'`)。

- [ ] **Step 3: 实现 DeepSeekProvider**

创建 `src/ui_case_compiler/compiler/deepseek_provider.py`:

```python
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
```

- [ ] **Step 4: 运行测试确认通过**

Run: `.venv/Scripts/python.exe -m pytest tests/compiler/test_deepseek_provider.py -v --basetemp="$TEMP/uicase_pt"`
Expected: 全部 8 个测试 PASS。

- [ ] **Step 5: 类型与风格检查**

Run: `.venv/Scripts/python.exe -m ruff check src/ui_case_compiler/compiler/deepseek_provider.py tests/compiler/test_deepseek_provider.py && .venv/Scripts/python.exe -m mypy src`
Expected: ruff All checks passed;mypy Success。

- [ ] **Step 6: 提交**

```bash
git add src/ui_case_compiler/compiler/deepseek_provider.py tests/compiler/test_deepseek_provider.py
git commit -m "feat: 实现 DeepSeekProvider(宽容解析 + json 兜底)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 4: 去 Mock 化

**Files:**
- Delete: `src/ui_case_compiler/compiler/mock_llm_provider.py`
- Modify: `src/ui_case_compiler/compiler/natural_language_compiler.py:19-25`
- Modify: `src/ui_case_compiler/compiler/__init__.py`
- Modify: `tests/compiler/test_natural_language_compiler.py`

**Interfaces:**
- Consumes: `DeepSeekProvider`(Task 3,用于 `__init__` 导出)。
- Produces:
  - `NaturalLanguageCompiler.__init__(self, provider: LLMProvider, prompt_builder: PromptBuilder | None = None)` — `provider` 必填。
  - `compiler/__init__.py` 导出不再含 `MockLLMProvider`,新增 `DeepSeekProvider`。

- [ ] **Step 1: 改写管线测试(删 Mock 测试)**

编辑 `tests/compiler/test_natural_language_compiler.py`:
- 删除 `test_mock_provider_generates_valid_plan`(第 31-41 行)——它依赖 Mock 默认 provider。
- 删除其顶部不再使用的 import:`from ui_case_compiler.schema.steps import ClickStep, NavigateStep`(仅该测试使用)。
- 其余测试(`test_non_json_provider_response_raises_compilation_error`、`test_invalid_dsl_provider_response_raises_validation_error`、`test_provider_is_only_needed_during_compilation`、`test_provider_protocol_matches_counting_provider`)**保留不变**——它们都显式传入本地 fake provider,不依赖 Mock。

- [ ] **Step 2: 运行确认现有测试仍引用 Mock 而失败(基线)**

Run: `.venv/Scripts/python.exe -m pytest tests/compiler/test_natural_language_compiler.py -v --basetemp="$TEMP/uicase_pt"`
Expected: 保留的 4 个测试此刻仍 PASS(Mock 尚未删,`NaturalLanguageCompiler` 仍可无参构造)。这一步确认删测试没误伤保留用例。

- [ ] **Step 3: 让 provider 必填**

编辑 `src/ui_case_compiler/compiler/natural_language_compiler.py`,把 `__init__`(当前第 19-25 行)改为:

```python
    def __init__(
        self,
        provider: LLMProvider,
        prompt_builder: PromptBuilder | None = None,
    ) -> None:
        self._provider = provider
        self._prompt_builder = prompt_builder or PromptBuilder()
```

同时删除文件顶部 `from ui_case_compiler.compiler.mock_llm_provider import MockLLMProvider`(第 8 行)。

- [ ] **Step 4: 删除 Mock 文件**

Run: `git rm src/ui_case_compiler/compiler/mock_llm_provider.py`
Expected: 文件被删除并暂存。

- [ ] **Step 5: 更新 compiler/__init__.py**

把 `src/ui_case_compiler/compiler/__init__.py` 完整替换为:

```python
from ui_case_compiler.compiler.deepseek_provider import DeepSeekProvider
from ui_case_compiler.compiler.llm_provider import LLMProvider
from ui_case_compiler.compiler.natural_language_compiler import NaturalLanguageCompiler
from ui_case_compiler.compiler.page_context_collector import PageContext, PageContextCollector

__all__ = [
    "DeepSeekProvider",
    "LLMProvider",
    "NaturalLanguageCompiler",
    "PageContext",
    "PageContextCollector",
]
```

- [ ] **Step 6: 运行测试确认通过**

Run: `.venv/Scripts/python.exe -m pytest tests/compiler/ -v --basetemp="$TEMP/uicase_pt"`
Expected: `test_natural_language_compiler.py` 保留的 4 个 + `test_deepseek_provider.py` 的 8 个全部 PASS,无 import 错误。

- [ ] **Step 7: 类型与风格检查**

Run: `.venv/Scripts/python.exe -m ruff check . && .venv/Scripts/python.exe -m mypy src`
Expected: ruff All checks passed;mypy Success(确认无残留对 `MockLLMProvider` 的引用)。

- [ ] **Step 8: 提交**

```bash
git add -A
git commit -m "refactor: 删除 MockLLMProvider,provider 改为必填

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 5: CLI 接入 DeepSeekProvider

**Files:**
- Modify: `src/ui_case_compiler/cli/main.py:101-115`(compile-nl 命令与相关 import)
- Test: `tests/cli/test_cli.py:76-90`(重写)+ 新增 api_key 缺失测试

**Interfaces:**
- Consumes: `load_config()`(Task 2)、`DeepSeekProvider`(Task 3)、`NaturalLanguageCompiler`(Task 4,provider 必填)。
- Produces: `compile-nl` 命令行为——缺 api_key 报错非 0 退出;有 api_key 时用 `DeepSeekProvider` 编译。

- [ ] **Step 1: 写失败测试(重写 compile-nl 测试 + 新增缺 key 测试)**

编辑 `tests/cli/test_cli.py`。把 `test_compile_nl_command_writes_plan`(第 76-90 行)替换为下面两个测试,并在文件顶部 import 区加入 `from unittest.mock import patch`:

```python
def test_compile_nl_command_requires_api_key(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    text_path = tmp_path / "case.txt"
    context_path = tmp_path / "context.json"
    text_path.write_text("Click the Login button", encoding="utf-8")
    context_path.write_text('{"url": "https://example.test/login"}', encoding="utf-8")

    result = runner.invoke(
        app,
        ["compile-nl", str(text_path), "--context", str(context_path)],
    )

    assert result.exit_code == 1
    assert "API key" in result.output


def test_compile_nl_command_writes_plan(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test")
    text_path = tmp_path / "case.txt"
    context_path = tmp_path / "context.json"
    output_path = tmp_path / "plan.json"
    text_path.write_text("Click the Login button", encoding="utf-8")
    context_path.write_text('{"url": "https://example.test/login"}', encoding="utf-8")

    fake_json = (
        '{"id": "nl", "name": "NL", "source": "natural_language",'
        ' "steps": [{"id": "step-001", "type": "navigate", "url": "https://example.test"}]}'
    )

    async def fake_generate(self, prompt: str) -> str:
        return fake_json

    with patch(
        "ui_case_compiler.compiler.deepseek_provider.DeepSeekProvider.generate_plan_json",
        fake_generate,
    ):
        result = runner.invoke(
            app,
            ["compile-nl", str(text_path), "--context", str(context_path), "-o", str(output_path)],
        )

    assert result.exit_code == 0
    assert output_path.exists()
    assert "natural_language" in output_path.read_text(encoding="utf-8")
```

注意:`DeepSeekProvider.__init__` 在 api_key 存在时会构造 `AsyncOpenAI` 客户端但不发起网络请求;patch 掉 `generate_plan_json` 即可避免真实调用。

- [ ] **Step 2: 运行测试确认失败**

Run: `.venv/Scripts/python.exe -m pytest tests/cli/test_cli.py::test_compile_nl_command_requires_api_key tests/cli/test_cli.py::test_compile_nl_command_writes_plan -v --basetemp="$TEMP/uicase_pt"`
Expected: FAIL——当前 `compile-nl` 仍构造无参 `NaturalLanguageCompiler()`(Task 4 已使其 provider 必填,会 TypeError;或缺 key 未报 "API key")。

- [ ] **Step 3: 修改 compile-nl 命令**

编辑 `src/ui_case_compiler/cli/main.py`。

先更新 import(第 10-11 行附近),把:

```python
from ui_case_compiler.compiler import NaturalLanguageCompiler, PageContext
from ui_case_compiler.config import RuntimeConfig, load_config
```

改为:

```python
from ui_case_compiler.compiler import DeepSeekProvider, NaturalLanguageCompiler, PageContext
from ui_case_compiler.config import RuntimeConfig, load_config
```

再把 `compile_nl_command`(当前第 101-115 行)改为:

```python
@app.command("compile-nl")
def compile_nl_command(
    text_path: Path,
    context_path: Path = CONTEXT_OPTION,
    output: Path | None = OUTPUT_OPTION,
) -> None:
    """将自然语言用例编译为可执行计划。"""

    try:
        config_value = load_config()
        if not config_value.llm.api_key:
            msg = "未配置模型 API key，请设置环境变量 DEEPSEEK_API_KEY"
            raise UiCaseCompilerError(msg)
        provider = DeepSeekProvider(config_value.llm)
        text = text_path.read_text(encoding="utf-8")
        context = PageContext.model_validate_json(context_path.read_text(encoding="utf-8"))
        plan = asyncio.run(NaturalLanguageCompiler(provider=provider).compile(text, context))
        _write_or_print_plan(plan, output)
    except (UiCaseCompilerError, ValidationError, OSError) as exc:
        _fail(exc)
```

(`UiCaseCompilerError` 已在文件第 12 行 import;错误信息含 "API key" 以匹配测试断言。)

- [ ] **Step 4: 运行测试确认通过**

Run: `.venv/Scripts/python.exe -m pytest tests/cli/ -v --basetemp="$TEMP/uicase_pt"`
Expected: 全部 PASS(含 help、validate、compile-recording 及两个新 compile-nl 测试)。

- [ ] **Step 5: 全量测试 + 类型 + 风格**

Run: `.venv/Scripts/python.exe -m pytest -q --basetemp="$TEMP/uicase_pt" && .venv/Scripts/python.exe -m ruff check . && .venv/Scripts/python.exe -m mypy src`
Expected: pytest 全绿(比 v1 少 1 个删掉的 Mock 测试,多 10 个新测试);ruff All checks passed;mypy Success。

- [ ] **Step 6: 提交**

```bash
git add src/ui_case_compiler/cli/main.py tests/cli/test_cli.py
git commit -m "feat: compile-nl 接入 DeepSeekProvider,缺 api_key 即报错

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## 端到端验证(需用户 api_key,不在自动化测试内)

实现全部完成后,用户配置真实 key 手动确认:

```powershell
$env:DEEPSEEK_API_KEY = "<your-key>"
ui-case compile-nl examples/natural_language/login.txt --context examples/context/login.json
```

Expected: 输出一份 `source: "natural_language"` 的合法 ExecutablePlan JSON。若模型输出不符合 DSL,会以 `PlanValidationError` 报错退出(符合「失败即报错」设计)。

---

## Self-Review

**Spec coverage:**
- 去 Mock 化 → Task 4 ✓
- api_key 缺失即报错 → Task 5(命令检查)+ Task 3(provider 构造检查)✓
- DeepSeekProvider + 宽容解析 + json 兜底 → Task 3 ✓
- LLMConfig 环境变量配置 → Task 2 ✓
- openai 依赖 → Task 1 ✓
- CLI 注入 + 不加 --mock → Task 5 ✓
- 编译管线零改动 → 各任务仅改 provider/config/cli,未触 schema/runner/reporter/storage ✓
- 端到端验证需用户 key → 文档末尾 ✓

**Placeholder scan:** 无 TBD/TODO;每个 code step 含完整代码;命令含预期输出。✓

**Type consistency:**
- `LLMConfig` 字段 `api_key/base_url/model/timeout_s` 在 Task 2 定义,Task 3 `DeepSeekProvider.__init__` 与 Task 5 一致引用 ✓
- `DeepSeekProvider.__init__(config: LLMConfig)` 与 `generate_plan_json(prompt: str) -> str` 在 Task 3 定义,Task 5 patch 路径与实现类路径一致 ✓
- `NaturalLanguageCompiler.__init__(provider, ...)` 必填在 Task 4 定义,Task 5 以 `provider=provider` 调用 ✓
- Task 3 provider 私有属性 `_client`,测试用 `provider._client = client` 注入,与实现一致 ✓
