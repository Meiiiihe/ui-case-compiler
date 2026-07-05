# v2 子项目②：真实录制设计

**状态:** 待用户审阅
**日期:** 2026-07-05
**范围:** UI Case Compiler v2 的第二个子项目——用 Playwright 注入脚本实时捕获用户操作，替换离线 JSON 事件流录制。

## 背景

v1 的录制能力是"离线"的：用户需要手工准备一份 `RecordedEvent` JSON 文件，交给 `compile-recording` 命令编译。v2 要提供真实录制：启动一个有界面浏览器，用户实际操作，脚本实时捕获交互事件并编译为可执行计划。

这是 v2 四个有序子项目的第二个：

```
① 真实模型 Provider（已完成，已合并 master）
② 真实录制（本 spec）        ← Playwright 注入脚本实时捕获
③ HTTP API 层
④ React Web UI
```

## recorder 现状核验

现有离线录制管线（`compile-recording` 命令）：

```
JSON 文件 → EventCollector.load_json() → list[RecordedEvent]
          → RecordingCompiler.compile()
              → EventNormalizer.normalize()   （去 mousemove、归并连续 input）
              → LocatorGenerator.generate()    （role>label>placeholder>test_id>text>css>xpath）
              → ExecutablePlan
```

关键洞察：`RecordedEvent` / `RecordedElement` 数据契约是整条管线的中枢。EventNormalizer、LocatorGenerator、RecordingCompiler 都只依赖这个契约，不关心事件来源。因此子项目② 的本质是：新增一个"实时捕获源"，产出同样的 `list[RecordedEvent]`，喂给已有的 RecordingCompiler——与子项目① 复用 LLMProvider 扩展点是同一套路。

`RecordedElement` 的 8 个字段（tag/text/role/label/placeholder/test_id/css/xpath）正是注入 JS 要从 DOM 元素采集的信息。

## 已确定的关键决策

| 决策点 | 结论 |
|--------|------|
| 启停交互 | `ui-case record <url>` 启动有界面（headed）浏览器；用户操作完后在终端按回车停止；随后自动编译输出。 |
| 采集字段 | 全部 8 个字段，注入 JS 实现 role/label 的 DOM 推断（隐式角色、`<label>` 关联、aria-label 等）。 |
| 捕获事件 | 四类核心：click / input / change / navigation。RecordedEvent 契约不变，RecordingCompiler 零改动。 |
| 注入机制 | `add_init_script`（每次导航后自动重注入，不丢事件）+ `expose_binding`（页面 JS 直接回调 Python）。 |
| 方案 | 方案 A：新增 LiveRecorder + recorder_script.js，复用现有管线，现有 recorder 模块零改动，离线 `compile-recording` 命令保留。 |

## 方案选择

采用**方案 A**：新增一个"实时捕获源"适配到已验证的 RecordedEvent 契约，现有 normalizer / locator_generator / compiler 一行不改。备选方案 B（LiveRecorder 内联去噪，与 EventNormalizer 职责重复）和方案 C（跳过 RecordedEvent 直接产出计划，重写定位器逻辑进 JS）都在重复已良好工作的代码，弃用。

## 架构与文件结构

### 新增文件

```
src/ui_case_compiler/recorder/
  recorder_script.js       注入脚本：监听事件 + 采集 8 字段 + 回调 Python
  live_recorder.py         LiveRecorder：驱动浏览器 + 收集 RecordedEvent
```

### 修改文件

- `src/ui_case_compiler/cli/main.py`：新增 `record` 命令。

### 完全不改

`recorder_session.py`（RecordedEvent/RecordedElement 契约 + RecordingCompiler）、`event_normalizer.py`、`locator_generator.py`、`event_collector.py`、离线 `compile-recording` 命令。

### 数据流

```
record <url>
  → LiveRecorder.record(url)  →  list[RecordedEvent]   （与离线 JSON 格式一致）
  → RecordingCompiler().compile(events, name)          （现有，零改动）
      → EventNormalizer（去噪/归并） → LocatorGenerator（定位器）
  → ExecutablePlan
  → 输出 / 保存
```

LiveRecorder 单一职责：产出与离线 JSON 完全相同结构的 RecordedEvent 列表；之后完全走已验证的现有管线。

## 注入脚本 recorder_script.js

在浏览器页面内运行，监听事件、采集字段、通过 `expose_binding` 暴露的 `__uicaseRecord` 回调把事件推给 Python。

### 事件映射

```
click 事件   → {type: "click",  element, timestamp}
input 事件   → {type: "input",  element, value, timestamp}
change 事件  → {type: "change", element, value, timestamp}
```

navigation 不在 JS 监听——由 Python 侧 `page.on("framenavigated")` 捕获主 frame 导航，比 JS 侧页面卸载时机更可靠。

### 8 字段采集

| 字段 | 采集方式 |
|------|---------|
| `tag` | `el.tagName.toLowerCase()` |
| `text` | `el.textContent` 裁剪首行、trim、限长 |
| `role` | 显式 `role` 属性；否则按 tagName 推断隐式角色（button→button、a[href]→link、input[type]→textbox/checkbox/radio、select→combobox 等） |
| `label` | 优先 `aria-label`；否则 `aria-labelledby` 指向元素文本；否则祖先 `<label>` 或 `for=id` 关联的 `<label>` 文本 |
| `placeholder` | `placeholder` 属性 |
| `test_id` | `data-testid` 属性 |
| `css` | 有 id 用 `#id`；否则 tag + nth-of-type 路径 |
| `xpath` | 生成绝对 xpath 路径 |

对 login.html 验证：username 输入框 → tag=input、role=textbox（推断）、label="Username"（祖先 `<label>` 文本）、css="#username"；Login 按钮 → tag=button、role=button、text="Login"。结果与现有 `examples/recordings/login-events.json` 手写结构对齐。

### 回调协议

JS 侧调用 `window.__uicaseRecord(payload)`，payload 为 plain object（type/element/value/timestamp）。Python 侧回调把原始 dict append 到列表，停止后统一 `EventCollector.collect()` 校验（复用现有校验入口）。

### 噪声处理

JS 侧只做最小过滤（忽略非左键 click、无 target 事件）；连续 input 归并、mousemove 丢弃全部交给现有 EventNormalizer，不在 JS 重复。

## LiveRecorder 生命周期

```python
async def record(url) -> list[RecordedEvent]:
    raw_events: list[dict] = []
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=False)   # record 强制 headed
        context = await browser.new_context()
        await context.expose_binding(
            "__uicaseRecord",
            lambda source, payload: raw_events.append(payload),
        )
        await context.add_init_script(script=<recorder_script.js 内容>)
        page = await context.new_page()
        page.on("framenavigated", <append nav event if main frame>)
        await page.goto(url)
        await self._wait_for_stop()      # 等终端回车
        await browser.close()
    return EventCollector().collect(raw_events)
```

### 终端回车停止

阻塞式 `input()` 不能直接进 async 循环。用 `asyncio.to_thread(input, "按回车结束录制...")` 把阻塞读放到线程并 `await`；期间 Playwright 事件循环照常收事件。回车返回即触发关闭。`_wait_for_stop` 抽成可注入钩子，测试可替换为立即返回。

### 时序

`framenavigated` 在 `goto` 时先触发一次首页导航，正好对应离线格式第一条 navigation 事件，符合 RecordingCompiler 用首个 navigation 作 base_url 的逻辑。

## CLI record 命令

```
ui-case record <url> [--name "Recorded Flow"] [-o out.json]
    events = asyncio.run(LiveRecorder().record(url))
    plan = RecordingCompiler().compile(events, name)
    _write_or_print_plan(plan, output)      # 复用现有辅助函数
    异常走 (UiCaseCompilerError, ValidationError, OSError) → _fail
```

复用现有 `NAME_OPTION` / `OUTPUT_OPTION` 定义。离线 `compile-recording` 命令保留不动，两种录制源并存。

## 错误处理

| 场景 | 异常 | 出口 |
|------|------|------|
| 录制事件为空（无可执行事件） | `RecordingError`（RecordingCompiler 现有逻辑） | CLI 非 0 退出 |
| 采集到的事件结构非法 | `RecordingError`（EventCollector.collect） | CLI 非 0 退出 |
| 元素无任何可用定位信息 | `RecordingError`（LocatorGenerator 现有逻辑） | CLI 非 0 退出 |
| 浏览器启动/导航失败 | Playwright 异常 → 冒泡 | CLI 非 0 退出 |

## 测试策略

真实录制涉及浏览器 + 人工交互，核心逻辑用 Playwright 集成测试（模拟操作，无需真人）覆盖：

1. **注入脚本字段推断**（Playwright 集成测试，需 chromium）：headless 加载本地 `login.html`，注入脚本，用 `page.click()`/`page.fill()` 模拟操作，断言 `__uicaseRecord` 收到的 payload 字段正确（role=textbox、label=Username、Login 按钮 role=button 等）。测的是真实注入脚本在真实 DOM 上的行为。

2. **LiveRecorder 事件收集/停止**（Playwright 集成测试）：`_wait_for_stop` 注入为立即返回，模拟操作驱动，断言返回的 `list[RecordedEvent]` 结构正确、能喂给 RecordingCompiler 产出合法计划。

3. **CLI record 命令**（单元测试，不开浏览器）：patch `LiveRecorder.record` 返回固定事件列表，断言命令产出计划、写文件。

4. **端到端手动验证**（需用户）：`ui-case record <本地 login.html file URL>`，手动填表单点登录，回车，确认产出合法计划。

全程 ruff + mypy strict 绿。集成测试依赖 `playwright install chromium`（v1 已装），比纯单测慢（需起浏览器），这是真实录制无法回避的取舍——选择测真实注入脚本行为。

## 非目标（本子项目不做）

- 不做浏览器扩展插件（明确用 Playwright 注入脚本）。
- 不扩展新事件类型（键盘按键、悬停等），维持 RecordedEvent 四类核心契约。
- 不改动现有 normalizer / locator_generator / compiler / 离线命令。
- 不在 JS 侧重复实现去噪/归并/定位器生成。
- 不做 HTTP API、Web UI（属于子项目 ③④）。
