# v2 子项目①：真实模型 Provider 设计

**状态:** 待用户审阅
**日期:** 2026-07-05
**范围:** UI Case Compiler v2 的第一个子项目——用真实模型替换 Mock，实现智能化自然语言编译。

## 背景

v1 已交付完整的 UI 用例编译与执行闭环（自然语言 / 录制 → 统一 DSL → Playwright 重放 → 报告）。自然语言编译当前走 `MockLLMProvider`，返回固定 JSON，仅用于演示和测试。

v2 的整体目标包含四项能力，经讨论确定拆分为**四个有序子项目**，各自独立走 spec → plan → 实现：

```
① 真实模型 Provider（本 spec，能力 1+2）  ← 最小、风险低、可独立验证
② 真实录制（能力 3）        Playwright 注入脚本实时捕获
③ HTTP API 层（能力 4 地基）  FastAPI 复用 Python 核心
④ React Web UI（能力 4）     Vite + TypeScript 消费 API
```

本文档只覆盖子项目①。②③④ 各自后续单独设计。

## 已确定的关键决策

| 决策点 | 结论 |
|--------|------|
| Agent 职责边界 | 仅做「自然语言 + 页面上下文 → ExecutablePlan」编译。执行阶段保持纯 Playwright 重放，不介入模型。v1「回归不依赖模型」的理念完整保留。 |
| 编译方式 | 简单 Agent + 静态快照。用户/录制器提供 `PageContext`（URL、可访问性树、DOM 摘要、截图路径），一次性交给模型。编译时**不**打开真实页面探索。 |
| 接入形态 | 简单 API 接入，**不**引入 Claude Code / skill / MCP 等复杂 agent。 |
| 目标模型 | **DeepSeek**（OpenAI 兼容接口）。使用 `openai` Python SDK 走兼容端点。 |
| 输出可靠性 | `response_format=json_object` + 宽容解析。校验失败即报错，**不**做回环重试。 |
| Prompt | 保持 v1 `PromptBuilder` 现状，本子项目**不重写** prompt。 |
| Mock | **删除**。强制走 AI；未配置 api_key 直接报错终止，**不**回落 Mock。 |
| 交付方式 | 四项能力拆为四个有序子项目。 |

## 方案选择

采用**方案 A（最小落地）**：新增一个实现 v1 已有 `LLMProvider` Protocol 的真实 provider，编译管线本身零改动。用户明确目标模型只有 DeepSeek，因此不需要多 provider 抽象，也不重写 prompt。

## v1 编译管线核验结论

在采用方案 A（复用 v1 管线）前，已核验整条编译链路：

- `PromptBuilder`（`prompt_builder.py`）：有空文本 / 空 URL 校验，逻辑正确。
- `NaturalLanguageCompiler._parse_plan_json`（`natural_language_compiler.py:33`）：JSON 解析失败报 `CompilationError`，非 dict 报错，正确。
- `validate_plan`（`validation.py:13`）：Pydantic 校验失败转 `PlanValidationError`，正确。
- 测试覆盖非 JSON、非法 DSL、provider 只在编译期调用，覆盖到位。

**结论：管线代码没有 bug，方案 A 复用成立。** 但真实接入会暴露 3 个在 Mock 下不显现的适配隐患：

| # | 隐患 | 位置 | 处理 |
|---|------|------|------|
| 1 | JSON 提取不够宽容——真实模型常把 JSON 包在 ```` ```json ```` 围栏或前后加解释文字，`json.loads` 整串会失败 | `natural_language_compiler.py:35` | **在新 provider 内部**做宽容解析，不污染管线方法 |
| 2 | DeepSeek 的 `response_format=json_object` 硬性要求 prompt 含 "json" 字样，否则报错；v1 prompt 无小写 "json" | `prompt_builder.py` | provider 内部检测并兜底追加 |
| 3 | v1 prompt 未给字段级 schema，模型可能漏字段（如 role 定位缺 `role`）或多塞字段被 `extra="forbid"` 拒 | schema | **已知风险**，由「不重写 prompt + 失败即报错」决策承担，通过报错暴露 |

隐患 1、2 收敛在新 provider 内部解决，管线零改动；隐患 3 是 prompt 现状的质量上限，符合既定决策。

## 架构与改动面

核心思路：只做加法，复用 v1 留好的 `LLMProvider` 扩展点，把真实实现注入 `NaturalLanguageCompiler`。

### 新增文件

```
src/ui_case_compiler/compiler/deepseek_provider.py
```

`DeepSeekProvider` 类，实现 `LLMProvider` Protocol（`generate_plan_json(prompt: str) -> str`），内部用 `openai` SDK 走 DeepSeek 的 OpenAI 兼容 `chat/completions` 接口。

### 修改文件（最小）

- `config.py`：扩展 `RuntimeConfig`，新增 `LLMConfig` 段，`load_config()` 从环境变量读取。
- `compiler/__init__.py`：移除 `MockLLMProvider` 导出，新增 `DeepSeekProvider` 导出。
- `cli/main.py`：`compile-nl` 命令检查 api_key（缺失即报错退出），构造 `DeepSeekProvider` 注入编译器。
- `pyproject.toml`：新增 `openai>=1.0` 依赖。

### 删除

- `src/ui_case_compiler/compiler/mock_llm_provider.py`
- `NaturalLanguageCompiler.__init__` 中 `provider or MockLLMProvider()` 的默认回落，改为 `provider` 必填。

### 完全不改

`NaturalLanguageCompiler`（已接受任意 provider）、`PromptBuilder`、`schema/`、`runner/`、`reporter/`、`storage/`、以及 validate / run / dry-run / compile-recording 命令。

### 数据流（不变）

```
compile-nl 文本 + context
  → PromptBuilder.build()                        （不变）
  → DeepSeekProvider.generate_plan_json()         （新）
  → NaturalLanguageCompiler._parse_plan_json()    （不变）
  → validate_plan() Pydantic 校验                 （不变）
  → ExecutablePlan
```

## 去 Mock 化

- 删除 `mock_llm_provider.py`。
- `NaturalLanguageCompiler.__init__` 的 `provider` 参数改为必填（不传则报错），去掉 Mock 默认回落。
- `compiler/__init__.py` 移除 `MockLLMProvider`。
- 测试 `test_natural_language_compiler.py`：删除 `test_mock_provider_generates_valid_plan`；保留使用本地 fake provider（`NonJsonProvider` / `InvalidDslProvider` / `CountingProvider`）的管线测试——它们测的是管线契约，不依赖 Mock 实现。

## DeepSeekProvider 内部设计

`__init__(config: LLMConfig)`：用 `config.base_url` / `config.api_key` / `config.timeout_s`
构造 `openai.OpenAI` 客户端（或异步客户端），保存 `config.model` 备用。

```
generate_plan_json(prompt) 流程：
  1. 若 prompt 未含 "json" 字样 → 追加一行 "Return the result as a JSON object."
     （兜住 DeepSeek json_object 的硬性要求，隐患 2）
  2. 调 openai SDK:
       client.chat.completions.create(
         model=<config.model>,
         messages=[{"role": "user", "content": prompt}],
         response_format={"type": "json_object"},
         temperature=0,
       )
  3. 取 choices[0].message.content
  4. 宽容解析：剥掉 ```json ``` 围栏、trim 前后非 JSON 文本，提取第一个完整 JSON 对象
     （隐患 1）
  5. 返回纯 JSON 字符串，交给管线现有的 _parse_plan_json + validate_plan
  网络 / SDK 异常 → 包装为 CompilationError
```

宽容解析与 "json" 兜底都封闭在 provider 内部，管线零改动。

## 配置

`config.py` 扩展：

```python
class LLMConfig(BaseModel):
    api_key: str | None = None                  # 环境变量 DEEPSEEK_API_KEY
    base_url: str = "https://api.deepseek.com"  # 环境变量 LLM_BASE_URL 可覆盖
    model: str = "deepseek-chat"                # 环境变量 LLM_MODEL 可覆盖
    timeout_s: int = 60
```

- 挂到 `RuntimeConfig.llm: LLMConfig`，与现有运行配置并列，不影响 runner / reporter。
- `load_config()` 从 `os.environ` 读取，不硬编码任何密钥。

## CLI

`compile-nl` 命令流程：

```
compile-nl <text> --context <ctx> [-o out.json]
  1. load_config() → 取 llm 配置
  2. if not llm.api_key: 报错退出（非 0），提示配置 DEEPSEEK_API_KEY
  3. provider = DeepSeekProvider(llm)
  4. NaturalLanguageCompiler(provider=provider).compile(...)
```

不加 `--mock` 开关（强制 AI）。validate / run / dry-run / compile-recording 命令完全不动。

## 依赖

`pyproject.toml` 新增 `openai>=1.0`（DeepSeek 官方推荐用 openai SDK 走兼容接口）。

## 错误处理

| 场景 | 异常 | 出口 |
|------|------|------|
| 未配置 api_key | `CompilationError` | CLI 非 0 退出，提示配置 DEEPSEEK_API_KEY |
| 网络 / SDK 调用失败 | `CompilationError`（包装原异常） | CLI 非 0 退出 |
| 模型返回非 JSON（宽容解析后仍失败） | `CompilationError` | CLI 非 0 退出 |
| JSON 不符合 DSL | `PlanValidationError` | CLI 非 0 退出 |

## 测试策略

单元测试**不打真实网络**：

- 新增 `tests/compiler/test_deepseek_provider.py`，用 monkeypatch / fake 替换 SDK client：
  - 宽容解析：```` ```json 围栏 ````、前后带文字、纯 JSON 三种输入都能提取。
  - "json" 兜底：prompt 无 "json" 时被追加。
  - SDK 抛异常 → 包装为 `CompilationError`。
- `test_natural_language_compiler.py`：删 Mock 测试，保留 fake-provider 管线测试。
- CLI 测试：api_key 缺失 → 非 0 退出 + 错误信息；有 key 时用 fake provider 跑通。
- ruff / mypy strict 全绿。

### 端到端验证（需用户参与）

真实对接 DeepSeek 需要用户的 api_key，不进测试（不把密钥写入测试）。实现完成后提供一条手动验证命令，用户配置 key 后自行运行确认：

```powershell
$env:DEEPSEEK_API_KEY = "<your-key>"
ui-case compile-nl examples/natural_language/login.txt --context examples/context/login.json
```

## 非目标（本子项目不做）

- 不重写 prompt（保持 v1 现状）。
- 不做回环重试。
- 不做多 provider 抽象（目标仅 DeepSeek）。
- 不做真实录制、HTTP API、Web UI（属于子项目 ②③④）。
- 不保留任何 Mock 回落路径。
- 编译时不打开真实页面探索。
