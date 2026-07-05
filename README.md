# UI Case Compiler

UI Case Compiler 是一个 UI 自动化用例编译平台，用来验证两种低门槛用例创建方式：

- 自然语言用例编译为可执行计划。
- 用户操作录制事件流编译为可执行计划。

核心执行层使用 Python + Playwright；Web 控制台使用 React + TypeScript + Vite，通过本地 FastAPI 调用 Python 核心能力。

## 快速开始

进入项目目录：

```powershell
cd F:\ui-auto-test\ui_case_compiler
```

创建虚拟环境并安装 Python 依赖：

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e '.[dev]'
python -m playwright install chromium
```

验证核心能力：

```powershell
ui-case --help
python -m pytest
python -m ruff check .
python -m mypy src
```

运行本地登录页 CLI 示例：

```powershell
$PAGE_URL = python -c "from pathlib import Path; print(Path('examples/pages/login.html').resolve().as_uri())"
ui-case validate examples\plans\login.json
ui-case run examples\plans\login.json --param loginPageUrl=$PAGE_URL
```

执行完成后，报告、trace 和运行结果会输出到 `.ui-case-compiler/`。

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
npm.cmd install
npm.cmd run dev -- --host 127.0.0.1 --port 5173
```

浏览器打开：

```text
http://127.0.0.1:5173/
```

如果 `5173` 被占用，Vite 会自动切换到下一个端口，请以终端输出为准。

> Windows PowerShell 里直接运行 `npm` 可能触发 `npm.ps1` 执行策略错误，建议使用 `npm.cmd`。

## 前端验证

```powershell
cd F:\ui-auto-test\ui_case_compiler\web
npm.cmd test
npm.cmd run build
```

## 当前能力范围

- 统一步骤 DSL 和可执行计划。
- Playwright Python 执行器。
- HTML 报告、截图、trace、本地 JSON 存储。
- 离线录制事件流编译。
- 真实浏览器录制能力。
- 自然语言编译接口，支持 DeepSeek/OpenAI-compatible Provider。
- FastAPI HTTP API。
- React Web 控制台。
- CLI 命令：`serve`、`validate`、`run`、`dry-run`、`record`、`compile-recording`、`compile-nl`。

## 文档

- 第一版核心能力文档：[docs/v1-user-guide.md](docs/v1-user-guide.md)
- v2 设计与实施计划：[docs/superpowers](docs/superpowers)
