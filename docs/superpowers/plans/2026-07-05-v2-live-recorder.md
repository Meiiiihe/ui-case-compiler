# v2 子项目② 真实录制实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 用 Playwright 注入脚本实时捕获用户浏览器操作,产出与离线格式一致的 RecordedEvent,复用现有 RecordingCompiler 编译为可执行计划。

**Architecture:** 新增 `recorder_script.js`(页面内注入,监听 click/input/change 并采集 8 字段,通过 expose_binding 回调 Python)+ `LiveRecorder`(启动 headed 浏览器、add_init_script 注入、收集事件、framenavigated 记录导航、终端回车停止),CLI 新增 `record` 命令。现有 recorder 管线(RecordedEvent 契约、EventNormalizer、LocatorGenerator、RecordingCompiler、离线 compile-recording)零改动。

**Tech Stack:** Python 3.11、Playwright for Python(async_api)、注入 JS、pytest / pytest-asyncio、Typer、ruff、mypy strict。

## Global Constraints

- Python 版本 `>=3.11`。
- 现有 recorder 管线零改动:`recorder_session.py`(RecordedEvent/RecordedElement/RecordingCompiler)、`event_normalizer.py`、`locator_generator.py`、`event_collector.py`、离线 `compile-recording` 命令都不动。
- 捕获四类核心事件:click / input / change / navigation。不扩展新事件类型。
- 采集全部 8 字段:tag / text / role / label / placeholder / test_id / css / xpath;role/label 在 JS 侧做 DOM 推断。
- navigation 由 Python 侧 `page.on("framenavigated")` 捕获主 frame,不在 JS 监听。
- 注入机制:`context.add_init_script` + `context.expose_binding("__uicaseRecord", ...)`。
- `record` 命令强制 headed(headless=False)。
- 连续 input 归并、mousemove 丢弃交给现有 EventNormalizer,不在 JS 或 LiveRecorder 重复。
- `_wait_for_stop` 抽成可注入钩子,测试替换为立即返回。
- 集成测试用模拟操作(page.click/page.fill),不需真人;依赖 `playwright install chromium`(已装)。
- 全程 ruff + mypy strict 绿。
- 提交信息结尾:`Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`。

## 现有契约(实现须对齐,不可改动)

`RecordedEvent`(recorder_session.py):
```python
type: Literal["click", "input", "change", "navigation", "mousemove"]
timestamp: int  # >= 0
value: str | None = None
url: str | None = None
element: RecordedElement | None = None
```
`RecordedElement`:
```python
tag: str
text / role / label / placeholder / test_id / css / xpath: str | None = None
```
`EventCollector().collect(raw: Sequence[Mapping]) -> list[RecordedEvent]`(校验入口)。
`RecordingCompiler().compile(events: list[RecordedEvent], name: str) -> ExecutablePlan`。
CLI 已有 `NAME_OPTION`(默认 "Recorded Flow")、`OUTPUT_OPTION`、`_write_or_print_plan(plan, output)`、`_fail(exc)`。

---

## File Structure

- `src/ui_case_compiler/recorder/recorder_script.js`(新) — 注入脚本,纯 JS,监听事件 + 采集 8 字段 + 调 `window.__uicaseRecord(payload)`。
- `src/ui_case_compiler/recorder/live_recorder.py`(新) — `LiveRecorder` 类,驱动浏览器、注入、收集、停止,返回 `list[RecordedEvent]`。
- `src/ui_case_compiler/cli/main.py`(改) — 新增 `record` 命令 + import。
- `tests/recorder/test_recorder_script.py`(新) — 注入脚本字段推断的 Playwright 集成测试。
- `tests/recorder/test_live_recorder.py`(新) — LiveRecorder 事件收集/停止的集成测试。
- `tests/cli/test_cli.py`(改) — 新增 record 命令单元测试(patch LiveRecorder)。

任务顺序:Task 1(注入脚本 + 其集成测试)→ Task 2(LiveRecorder + 其集成测试)→ Task 3(CLI record 命令)。

---

### Task 1: 注入脚本 recorder_script.js

**Files:**
- Create: `src/ui_case_compiler/recorder/recorder_script.js`
- Test: `tests/recorder/test_recorder_script.py`

**Interfaces:**
- Consumes: 无(纯 JS + Playwright 测试)。
- Produces: 一个 JS 脚本,注入后监听 document 的 click/input/change,对每个事件构造 `{type, timestamp, value?, element:{tag,text,role,label,placeholder,test_id,css,xpath}}` 并调用 `window.__uicaseRecord(payload)`。测试通过 expose_binding 收集 payload。

- [ ] **Step 1: 写失败测试**

创建 `tests/recorder/test_recorder_script.py`:

```python
from pathlib import Path

import pytest
from playwright.async_api import async_playwright


def _script() -> str:
    root = Path(__file__).resolve().parents[2]
    return (root / "src" / "ui_case_compiler" / "recorder" / "recorder_script.js").read_text(
        encoding="utf-8"
    )


def _login_url() -> str:
    root = Path(__file__).resolve().parents[2]
    return (root / "examples" / "pages" / "login.html").resolve().as_uri()


async def _collect_with(actions) -> list[dict]:
    events: list[dict] = []
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        context = await browser.new_context()
        await context.expose_binding(
            "__uicaseRecord",
            lambda source, payload: events.append(payload),
        )
        await context.add_init_script(script=_script())
        page = await context.new_page()
        await page.goto(_login_url())
        await actions(page)
        await page.wait_for_timeout(100)
        await browser.close()
    return events


@pytest.mark.asyncio
async def test_click_captures_button_role_and_text() -> None:
    async def actions(page):
        await page.click("button[type=submit]")

    events = await _collect_with(actions)
    clicks = [e for e in events if e["type"] == "click"]
    assert clicks, "expected at least one click event"
    element = clicks[-1]["element"]
    assert element["tag"] == "button"
    assert element["role"] == "button"
    assert element["text"] == "Login"


@pytest.mark.asyncio
async def test_input_captures_label_from_ancestor_label() -> None:
    async def actions(page):
        await page.fill("#username", "alice")

    events = await _collect_with(actions)
    inputs = [e for e in events if e["type"] == "input"]
    assert inputs, "expected at least one input event"
    last = inputs[-1]
    assert last["value"] == "alice"
    element = last["element"]
    assert element["tag"] == "input"
    assert element["label"] == "Username"
    assert element["role"] == "textbox"
    assert element["css"] == "#username"


@pytest.mark.asyncio
async def test_element_always_has_xpath() -> None:
    async def actions(page):
        await page.click("button[type=submit]")

    events = await _collect_with(actions)
    element = [e for e in events if e["type"] == "click"][-1]["element"]
    assert element["xpath"]
    assert element["xpath"].startswith("/")
```

- [ ] **Step 2: 运行测试确认失败**

Run: `.venv/Scripts/python.exe -m pytest tests/recorder/test_recorder_script.py -v --basetemp="$TEMP/uicase_pt" -p no:cacheprovider`
Expected: FAIL(`FileNotFoundError` 读不到 recorder_script.js)。

- [ ] **Step 3: 实现注入脚本**

创建 `src/ui_case_compiler/recorder/recorder_script.js`:

```javascript
(() => {
  if (window.__uicaseRecorderInstalled) return;
  window.__uicaseRecorderInstalled = true;

  const IMPLICIT_ROLES = {
    a: (el) => (el.hasAttribute("href") ? "link" : null),
    button: () => "button",
    select: () => "combobox",
    textarea: () => "textbox",
  };

  function inputRole(el) {
    const type = (el.getAttribute("type") || "text").toLowerCase();
    if (type === "checkbox") return "checkbox";
    if (type === "radio") return "radio";
    if (type === "button" || type === "submit" || type === "reset") return "button";
    return "textbox";
  }

  function roleOf(el) {
    const explicit = el.getAttribute("role");
    if (explicit) return explicit;
    const tag = el.tagName.toLowerCase();
    if (tag === "input") return inputRole(el);
    const fn = IMPLICIT_ROLES[tag];
    return fn ? fn(el) : null;
  }

  function trimText(value) {
    if (!value) return null;
    const line = value.trim().split("\n")[0].trim();
    if (!line) return null;
    return line.length > 200 ? line.slice(0, 200) : line;
  }

  function labelOf(el) {
    const aria = el.getAttribute("aria-label");
    if (aria && aria.trim()) return aria.trim();
    const labelledby = el.getAttribute("aria-labelledby");
    if (labelledby) {
      const ref = document.getElementById(labelledby);
      const text = trimText(ref && ref.textContent);
      if (text) return text;
    }
    if (el.id) {
      const forLabel = document.querySelector(`label[for="${el.id}"]`);
      const text = trimText(forLabel && forLabel.textContent);
      if (text) return text;
    }
    const ancestor = el.closest("label");
    if (ancestor) {
      const clone = ancestor.cloneNode(true);
      clone.querySelectorAll("input, textarea, select").forEach((n) => n.remove());
      const text = trimText(clone.textContent);
      if (text) return text;
    }
    return null;
  }

  function cssOf(el) {
    if (el.id) return `#${el.id}`;
    const parts = [];
    let node = el;
    while (node && node.nodeType === 1 && node.tagName.toLowerCase() !== "html") {
      let selector = node.tagName.toLowerCase();
      const parent = node.parentElement;
      if (parent) {
        const siblings = Array.from(parent.children).filter(
          (c) => c.tagName === node.tagName
        );
        if (siblings.length > 1) {
          selector += `:nth-of-type(${siblings.indexOf(node) + 1})`;
        }
      }
      parts.unshift(selector);
      if (node.id) {
        parts[0] = `#${node.id}`;
        break;
      }
      node = node.parentElement;
    }
    return parts.join(" > ");
  }

  function xpathOf(el) {
    const parts = [];
    let node = el;
    while (node && node.nodeType === 1) {
      let index = 1;
      let sibling = node.previousElementSibling;
      while (sibling) {
        if (sibling.tagName === node.tagName) index += 1;
        sibling = sibling.previousElementSibling;
      }
      parts.unshift(`${node.tagName.toLowerCase()}[${index}]`);
      node = node.parentElement;
    }
    return "/" + parts.join("/");
  }

  function attr(el, name) {
    const value = el.getAttribute(name);
    return value && value.trim() ? value.trim() : null;
  }

  function describe(el) {
    return {
      tag: el.tagName.toLowerCase(),
      text: trimText(el.textContent),
      role: roleOf(el),
      label: labelOf(el),
      placeholder: attr(el, "placeholder"),
      test_id: attr(el, "data-testid"),
      css: cssOf(el),
      xpath: xpathOf(el),
    };
  }

  function send(type, el, extra) {
    if (!el || el.nodeType !== 1) return;
    const payload = { type, timestamp: Date.now(), element: describe(el) };
    if (extra && "value" in extra) payload.value = extra.value;
    if (window.__uicaseRecord) window.__uicaseRecord(payload);
  }

  document.addEventListener(
    "click",
    (event) => {
      if (event.button !== 0) return;
      send("click", event.target, null);
    },
    true
  );
  document.addEventListener(
    "input",
    (event) => send("input", event.target, { value: event.target.value }),
    true
  );
  document.addEventListener(
    "change",
    (event) => send("change", event.target, { value: event.target.value }),
    true
  );
})();
```

- [ ] **Step 4: 运行测试确认通过**

Run: `.venv/Scripts/python.exe -m pytest tests/recorder/test_recorder_script.py -v --basetemp="$TEMP/uicase_pt" -p no:cacheprovider`
Expected: 3 个测试 PASS(会真实启动 chromium,较慢)。

- [ ] **Step 5: 风格检查**

Run: `.venv/Scripts/python.exe -m ruff check tests/recorder/test_recorder_script.py && .venv/Scripts/python.exe -m mypy src`
Expected: ruff All checks passed;mypy Success(.js 不受 mypy/ruff 检查)。

- [ ] **Step 6: 提交**

```bash
git add src/ui_case_compiler/recorder/recorder_script.js tests/recorder/test_recorder_script.py
git commit -m "feat: 注入脚本 recorder_script.js 采集 8 字段并回调 Python

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 2: LiveRecorder

**Files:**
- Create: `src/ui_case_compiler/recorder/live_recorder.py`
- Test: `tests/recorder/test_live_recorder.py`

**Interfaces:**
- Consumes: `recorder_script.js`(Task 1);`EventCollector`、`RecordedEvent`(现有);`RuntimeConfig`(现有)。
- Produces:
  - `LiveRecorder`,`__init__(self, config: RuntimeConfig | None = None, wait_for_stop: Callable[[], Awaitable[None]] | None = None)`。
  - `async def record(self, url: str) -> list[RecordedEvent]`。
  - 默认 `wait_for_stop` 用 `asyncio.to_thread(input, ...)`;测试注入立即返回的钩子。

- [ ] **Step 1: 写失败测试**

创建 `tests/recorder/test_live_recorder.py`:

```python
from pathlib import Path

import pytest

from ui_case_compiler.recorder.live_recorder import LiveRecorder
from ui_case_compiler.recorder.recorder_session import RecordedEvent, RecordingCompiler


def _login_url() -> str:
    root = Path(__file__).resolve().parents[2]
    return (root / "examples" / "pages" / "login.html").resolve().as_uri()


@pytest.mark.asyncio
async def test_record_collects_navigation_and_interactions() -> None:
    async def drive(page) -> None:
        await page.fill("#username", "alice")
        await page.fill("#password", "secret")
        await page.click("button[type=submit]")

    recorder = LiveRecorder(wait_for_stop=_driver_stop(drive))
    events = await recorder.record(_login_url())

    assert all(isinstance(e, RecordedEvent) for e in events)
    types = [e.type for e in events]
    assert types[0] == "navigation"
    assert "input" in types
    assert "click" in types


@pytest.mark.asyncio
async def test_recorded_events_compile_to_plan() -> None:
    async def drive(page) -> None:
        await page.fill("#username", "alice")
        await page.click("button[type=submit]")

    recorder = LiveRecorder(wait_for_stop=_driver_stop(drive))
    events = await recorder.record(_login_url())
    plan = RecordingCompiler().compile(events, "Recorded Login")

    assert plan.source == "recording"
    step_types = [s.type for s in plan.steps]
    assert step_types[0] == "navigate"
    assert "fill" in step_types
    assert "click" in step_types


def _driver_stop(drive):
    """Build a wait_for_stop hook that drives the page then returns."""

    async def hook(page) -> None:
        await page.wait_for_timeout(100)
        await drive(page)
        await page.wait_for_timeout(100)

    return hook
```

注意:测试需要在录制会话内拿到 `page` 来模拟操作,因此 `wait_for_stop` 钩子签名接收 `page`。实现须把 page 传给钩子。

- [ ] **Step 2: 运行测试确认失败**

Run: `.venv/Scripts/python.exe -m pytest tests/recorder/test_live_recorder.py -v --basetemp="$TEMP/uicase_pt" -p no:cacheprovider`
Expected: FAIL(`ModuleNotFoundError: ... live_recorder`)。

- [ ] **Step 3: 实现 LiveRecorder**

创建 `src/ui_case_compiler/recorder/live_recorder.py`:

```python
from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

from playwright.async_api import Frame, Page, async_playwright

from ui_case_compiler.config import RuntimeConfig, load_config
from ui_case_compiler.recorder.event_collector import EventCollector
from ui_case_compiler.recorder.recorder_session import RecordedEvent

_SCRIPT_PATH = Path(__file__).with_name("recorder_script.js")
_STOP_PROMPT = "按回车结束录制..."

WaitForStop = Callable[[Page], Awaitable[None]]


class LiveRecorder:
    """Capture live browser interactions via an injected script."""

    def __init__(
        self,
        config: RuntimeConfig | None = None,
        wait_for_stop: WaitForStop | None = None,
    ) -> None:
        self._config = config or load_config()
        self._wait_for_stop = wait_for_stop or self._default_wait_for_stop
        self._collector = EventCollector()

    async def record(self, url: str) -> list[RecordedEvent]:
        raw_events: list[dict[str, Any]] = []
        script = _SCRIPT_PATH.read_text(encoding="utf-8")

        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=False)
            context = await browser.new_context()

            async def on_record(source: Any, payload: dict[str, Any]) -> None:
                raw_events.append(payload)

            await context.expose_binding("__uicaseRecord", on_record)
            await context.add_init_script(script=script)
            page = await context.new_page()

            def on_navigated(frame: Frame) -> None:
                if frame is page.main_frame:
                    raw_events.append(
                        {"type": "navigation", "timestamp": 0, "url": frame.url}
                    )

            page.on("framenavigated", on_navigated)
            await page.goto(url)
            await self._wait_for_stop(page)
            await browser.close()

        return self._collector.collect(raw_events)

    async def _default_wait_for_stop(self, page: Page) -> None:
        _ = page
        await asyncio.to_thread(input, _STOP_PROMPT)
```

说明:
- navigation 事件 `timestamp` 用 0(RecordedEvent 要求 `>= 0`;真实相对顺序由 append 顺序保证,normalizer 不依赖 timestamp 数值)。
- expose_binding 的回调签名首参是 source(BindingSource),第二个是 JS 传来的 payload。
- click/input 的 timestamp 来自 JS 的 `Date.now()`(int),满足 `>= 0`。

- [ ] **Step 4: 运行测试确认通过**

Run: `.venv/Scripts/python.exe -m pytest tests/recorder/test_live_recorder.py -v --basetemp="$TEMP/uicase_pt" -p no:cacheprovider`
Expected: 2 个测试 PASS(启动 headed chromium;CI/无显示环境下 chromium headless=False 仍可运行,Playwright 用内置无头显示)。

- [ ] **Step 5: 类型与风格检查**

Run: `.venv/Scripts/python.exe -m ruff check src/ui_case_compiler/recorder/live_recorder.py tests/recorder/test_live_recorder.py && .venv/Scripts/python.exe -m mypy src`
Expected: ruff All checks passed;mypy Success。

- [ ] **Step 6: 提交**

```bash
git add src/ui_case_compiler/recorder/live_recorder.py tests/recorder/test_live_recorder.py
git commit -m "feat: 实现 LiveRecorder 实时捕获浏览器操作

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 3: CLI record 命令

**Files:**
- Modify: `src/ui_case_compiler/cli/main.py`
- Test: `tests/cli/test_cli.py`

**Interfaces:**
- Consumes: `LiveRecorder`(Task 2);现有 `RecordingCompiler`、`NAME_OPTION`、`OUTPUT_OPTION`、`_write_or_print_plan`、`_fail`。
- Produces: `record` CLI 命令——`ui-case record <url> [--name] [-o]`,录制→编译→输出计划。

- [ ] **Step 1: 写失败测试**

在 `tests/cli/test_cli.py` 末尾追加(顶部已 import `patch`):

```python
def test_record_command_writes_plan(tmp_path) -> None:
    output_path = tmp_path / "plan.json"

    events = [
        {"type": "navigation", "timestamp": 0, "url": "https://example.test/login"},
        {
            "type": "input",
            "timestamp": 1,
            "value": "alice",
            "element": {"tag": "input", "label": "Username", "css": "#username"},
        },
        {
            "type": "click",
            "timestamp": 2,
            "element": {"tag": "button", "role": "button", "text": "Login"},
        },
    ]

    async def fake_record(self, url: str):
        from ui_case_compiler.recorder.event_collector import EventCollector

        return EventCollector().collect(events)

    with patch(
        "ui_case_compiler.recorder.live_recorder.LiveRecorder.record",
        fake_record,
    ):
        result = runner.invoke(
            app,
            ["record", "https://example.test/login", "--name", "Rec", "-o", str(output_path)],
        )

    assert result.exit_code == 0
    assert output_path.exists()
    assert "recording" in output_path.read_text(encoding="utf-8")
```

- [ ] **Step 2: 运行测试确认失败**

Run: `.venv/Scripts/python.exe -m pytest tests/cli/test_cli.py::test_record_command_writes_plan -v --basetemp="$TEMP/uicase_pt" -p no:cacheprovider`
Expected: FAIL(`record` 命令不存在,typer 报 no such command,exit_code != 0)。

- [ ] **Step 3: 实现 record 命令**

编辑 `src/ui_case_compiler/cli/main.py`。

在 recorder 相关 import 附近(现有 `from ui_case_compiler.recorder.recorder_session import RecordingCompiler` 之后)加:

```python
from ui_case_compiler.recorder.live_recorder import LiveRecorder
```

在 `compile_recording_command` 定义之后新增命令:

```python
@app.command("record")
def record_command(
    url: str,
    name: str = NAME_OPTION,
    output: Path | None = OUTPUT_OPTION,
) -> None:
    """启动浏览器实时录制用户操作并编译为可执行计划。"""

    try:
        events = asyncio.run(LiveRecorder().record(url))
        plan = RecordingCompiler().compile(events, name)
        _write_or_print_plan(plan, output)
    except (UiCaseCompilerError, ValidationError, OSError) as exc:
        _fail(exc)
```

(`asyncio`、`Path`、`RecordingCompiler`、`NAME_OPTION`、`OUTPUT_OPTION`、`UiCaseCompilerError`、`ValidationError`、`_write_or_print_plan`、`_fail` 均已在文件中。)

- [ ] **Step 4: 运行测试确认通过**

Run: `.venv/Scripts/python.exe -m pytest tests/cli/test_cli.py -v --basetemp="$TEMP/uicase_pt" -p no:cacheprovider`
Expected: 全部 PASS(含新 record 测试与所有现有 CLI 测试)。

- [ ] **Step 5: 全量测试 + 类型 + 风格**

Run: `.venv/Scripts/python.exe -m pytest -q --basetemp="$TEMP/uicase_pt" -p no:cacheprovider && .venv/Scripts/python.exe -m ruff check . && .venv/Scripts/python.exe -m mypy src`
Expected: pytest 全绿(比子项目① 的 60 多出:3 recorder_script + 2 live_recorder + 1 CLI record = 66);ruff All checks passed;mypy Success。

- [ ] **Step 6: 提交**

```bash
git add src/ui_case_compiler/cli/main.py tests/cli/test_cli.py
git commit -m "feat: 新增 record 命令实时录制并编译

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## 端到端手动验证(需用户)

实现完成后手动确认真实录制闭环:

```powershell
$PAGE_URL = python -c "from pathlib import Path; print(Path('examples/pages/login.html').resolve().as_uri())"
ui-case record $PAGE_URL --name "My Login" -o my-recording.json
# 浏览器弹出后:填用户名、填密码、点 Login,回到终端按回车
```

Expected: 终端输出计划已写入 my-recording.json;打开该文件应看到 source=recording、navigate/fill/fill/click 步骤,locator 含 label/role 候选。可再 `ui-case validate my-recording.json` 确认合法。

---

## Self-Review

**Spec coverage:**
- 注入脚本采集 8 字段 + role/label 推断 → Task 1 ✓
- click/input/change 捕获 → Task 1(JS 监听)✓
- navigation 由 Python framenavigated 捕获 → Task 2 ✓
- add_init_script + expose_binding → Task 2 ✓
- headed 强制 → Task 2(launch headless=False)✓
- 终端回车停止 + 可注入钩子 → Task 2(_default_wait_for_stop / wait_for_stop 参数)✓
- 复用 EventCollector 校验 + RecordingCompiler → Task 2 返回 collect 结果、Task 3 compile ✓
- record CLI 命令 → Task 3 ✓
- 离线 compile-recording 保留、现有管线零改动 → 无任务触碰 recorder_session/normalizer/locator_generator/event_collector/compile-recording ✓
- 归并/去噪交给现有 normalizer → JS 与 LiveRecorder 均不做归并 ✓
- 集成测试用模拟操作 → Task 1/2 用 page.click/page.fill ✓
- CLI patch 单测 → Task 3 ✓
- 端到端手动验证 → 文档末尾 ✓

**Placeholder scan:** 无 TBD/TODO;每个 code step 含完整代码;命令含预期输出。✓

**Type consistency:**
- `LiveRecorder.__init__(config, wait_for_stop)` 与 `record(url) -> list[RecordedEvent]` 在 Task 2 定义;Task 3 用 `LiveRecorder().record(url)` 一致 ✓
- `wait_for_stop` 签名 `Callable[[Page], Awaitable[None]]`,Task 2 测试的 `_driver_stop` 返回 `hook(page)` 一致,实现 `_default_wait_for_stop(self, page)` 一致 ✓
- JS payload 结构 `{type, timestamp, value?, element:{8 字段}}` 与 RecordedEvent/RecordedElement 字段名(test_id 不是 testId)一致 ✓
- Task 3 fake_record 用 `EventCollector().collect(events)` 返回 list[RecordedEvent],与 LiveRecorder.record 返回类型一致 ✓

**一处风险标注:** Task 2 测试在 `wait_for_stop` 钩子里驱动 page 操作 —— 这是测试专用的钩子用法(生产钩子是等回车)。实现必须把 `page` 传给钩子,已在 `_wait_for_stop(page)` 签名和 `_default_wait_for_stop(self, page)` 中体现;生产默认钩子忽略 page 参数(`_ = page`)。
