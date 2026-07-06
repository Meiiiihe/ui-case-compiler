# UI Case Compiler

UI Case Compiler 是一个本地 UI 自动化测试学习项目，目标是把“自然语言用例”和“用户录制操作”编译成稳定可重复执行的测试计划，降低直接手写 Selenium / Playwright 脚本的门槛。

项目核心使用 Python + Playwright 执行测试，后端使用 FastAPI，前端使用 React + TypeScript + Vite。

## 适合展示的亮点

- 自然语言测试描述可以编译为结构化 `ExecutablePlan`。
- 录制一次页面操作，可以生成 `navigate / click / fill / assert` 等标准步骤。
- 执行阶段不需要每一步都调用大模型，回归执行更稳定、成本更低。
- 支持 locator fallback、参数化、失败截图、Playwright trace、HTML 报告。
- Web 控制台可以查看用例、试运行、正式运行、批量数据驱动和失败调试。
- 失败步骤可以定位到截图、错误信息、原始 DSL、主 locator 和备用 locator。
- 针对百度这类富输入框场景，`fill` 失败后会自动尝试点击后键盘输入兜底。

## 项目结构

```text
ui_case_compiler/
  src/ui_case_compiler/
    api/          FastAPI 接口和服务编排
    cli/          命令行入口
    compiler/     自然语言用例编译
    data/         CSV / TSV / XLSX 数据解析
    recorder/     录制事件收集和步骤编译
    reporter/     RunResult、HTML 报告、批量结果
    runner/       Playwright 执行器、locator 解析、批量执行
    schema/       Step DSL 和 ExecutablePlan
    storage/      本地 JSON 存储
  web/            React 前端控制台
  examples/       本地页面、示例计划、录制事件、自然语言用例
  tests/          后端测试
  docs/           使用指南和演示脚本
```

## 环境要求

推荐环境：

| 项目 | 版本 |
| --- | --- |
| Python | 3.11+，推荐 3.12 |
| Node.js | 18+ |
| 浏览器自动化 | Playwright Chromium |
| 操作系统 | Windows / macOS / Linux |

下面命令以 Windows PowerShell 为例。

## 安装依赖

进入项目目录：

```powershell
cd F:\ui-auto-test\ui_case_compiler
```

创建并激活 Python 虚拟环境：

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

如果本机没有 `py` 启动器，可以使用：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

安装 Python 依赖和 Playwright 浏览器：

```powershell
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
python -m playwright install chromium
```

安装前端依赖：

```powershell
cd F:\ui-auto-test\ui_case_compiler\web
npm.cmd install
```

PowerShell 里建议使用 `npm.cmd`，避免 `npm.ps1` 执行策略问题。

## 启动 Web 控制台

终端 1：启动后端 API。

```powershell
cd F:\ui-auto-test\ui_case_compiler
.\.venv\Scripts\Activate.ps1
ui-case serve
```

默认地址：

```text
http://127.0.0.1:8000
```

终端 2：启动前端。

```powershell
cd F:\ui-auto-test\ui_case_compiler\web
npm.cmd run dev -- --host 127.0.0.1 --port 5173
```

浏览器打开：

```text
http://127.0.0.1:5173/
```

如果 `5173` 被占用，以 Vite 终端输出的实际地址为准。

## 快速 Demo 1：本地登录页面

这个 Demo 最稳定，适合第一次验证项目是否跑通。

生成本地页面 URL：

```powershell
cd F:\ui-auto-test\ui_case_compiler
$PAGE_URL = python -c "from pathlib import Path; print(Path('examples/pages/login.html').resolve().as_uri())"
$PAGE_URL
```

运行示例计划：

```powershell
ui-case validate examples\plans\login.json
ui-case run examples\plans\login.json --param loginPageUrl=$PAGE_URL
```

预期结果：

```text
Run status: passed
Report: .ui-case-compiler\reports\run-xxxx.html
Trace: .ui-case-compiler\artifacts\run-xxxx\trace.zip
```

这个计划会执行：

1. 打开本地登录页面。
2. 输入用户名 `demo@example.com`。
3. 输入密码 `secret`。
4. 点击 `Login`。
5. 验证页面出现 `Welcome back`。

## 快速 Demo 2：百度搜索

这个 Demo 适合展示真实网页、动态页面和富输入框兜底能力。外网页面可能受网络、验证码、页面改版影响，所以它更适合作为“真实场景演示”，不是最稳定的 CI 用例。

Web 控制台录制方式：

1. 打开 `http://127.0.0.1:5173/`。
2. 在“实时录制”里输入起始 URL：

```text
https://www.baidu.com/
```

3. 点击开始录制。
4. 在打开的浏览器里点击搜索框，输入 `王俊凯`，点击 `百度一下`。
5. 回到控制台点击“停止并生成步骤”。
6. 进入生成的用例详情页，点击“试运行”或“正式运行”。
7. 如果失败，进入运行详情页查看失败截图、trace、locator 和原始 DSL。

也可以直接运行示例计划：

```powershell
ui-case run examples\plans\baidu-search.json --headed
```

`--headed` 会打开有界面浏览器，方便观察真实页面。

## 自然语言编译

自然语言编译需要配置 DeepSeek API Key。当前实现使用 OpenAI-compatible 调用方式。

临时设置当前 PowerShell 会话：

```powershell
$env:DEEPSEEK_API_KEY = "你的 key"
```

持久写入用户环境变量：

```powershell
setx DEEPSEEK_API_KEY "你的 key"
```

执行 `setx` 后需要重新打开终端。

示例自然语言用例：

```text
打开登录页面，输入用户名 demo@example.com，输入密码 secret，点击 Login 按钮，验证页面出现 Welcome back。
```

CLI 编译示例：

```powershell
ui-case compile-nl examples\natural_language\login.txt --context examples\context\login.json -o .ui-case-compiler\plans\login-nl.json
```

## 录制能力

Web 控制台推荐使用实时录制：

1. 输入起始 URL。
2. 点击开始录制。
3. 在 Playwright 打开的浏览器里完成一次测试流程。
4. 点击停止并生成步骤。
5. 系统会把操作编译成 `ExecutablePlan` 并保存到本地。

CLI 也支持实时录制：

```powershell
ui-case record https://www.baidu.com/ --name "Baidu Search" -o .ui-case-compiler\plans\baidu-recorded.json
```

也支持离线事件 JSON 编译：

```powershell
ui-case compile-recording examples\recordings\login-events.json --name "Login Recording" -o .ui-case-compiler\plans\login-recording.json
```

## 失败调试

执行失败后，运行详情页会展示：

- 失败步骤。
- 错误信息。
- 失败截图。
- Playwright trace 下载入口。
- HTML 报告入口。
- 对应的原始步骤 DSL。
- 主 locator 和 fallback locator。

常见失败原因：

| 现象 | 可能原因 | 排查方式 |
| --- | --- | --- |
| `matched 0 elements` | 页面结构变化、locator 不稳定 | 看原始 locator 和截图 |
| `matched 1 elements but none were usable for input` | 命中了不可编辑节点 | 查看截图，必要时使用录制重新生成 |
| 后续步骤 `skipped` | 前置步骤失败且开启失败即停止 | 先修第一个 failed 步骤 |
| 百度/Google 搜索失败 | 外网页面改版、验证码、网络限制 | 使用 headed 模式和 trace 查看 |

查看 trace：

```powershell
python -m playwright show-trace .ui-case-compiler\artifacts\run-xxxx\trace.zip
```

## 批量数据驱动

Web 控制台支持 CSV / TSV / XLSX 批量数据驱动。适合登录、表单提交等“步骤相同，输入数据不同”的回归场景。

示例 CSV：

```csv
loginPageUrl,username,password,expectedText
file:///F:/ui-auto-test/ui_case_compiler/examples/pages/login.html,demo@example.com,secret,Welcome back
file:///F:/ui-auto-test/ui_case_compiler/examples/pages/login.html,wrong@example.com,bad,Invalid credentials
```

在用例详情页上传数据文件，设置并发数，然后点击批量执行即可。

## 测试和质量检查

后端：

```powershell
cd F:\ui-auto-test\ui_case_compiler
.\.venv\Scripts\Activate.ps1
python -m pytest
python -m ruff check src tests
python -m mypy src
```

前端：

```powershell
cd F:\ui-auto-test\ui_case_compiler\web
npm.cmd test
npm.cmd run build
```

当前验证结果：

```text
pytest: 95 passed
frontend test: 22 passed
ruff: passed
mypy: passed
frontend build: passed
```
