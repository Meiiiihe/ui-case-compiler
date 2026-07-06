# 演示指南

这份文档用于面试或自我复盘时快速演示项目。建议先演示本地稳定用例，再演示百度真实网页用例，最后讲失败调试能力。

## 演示前检查

确认后端测试和前端构建通过：

```powershell
cd F:\ui-auto-test\ui_case_compiler
.\.venv\Scripts\Activate.ps1
python -m pytest
python -m ruff check src tests
python -m mypy src

cd F:\ui-auto-test\ui_case_compiler\web
npm.cmd test
npm.cmd run build
```

启动服务：

```powershell
cd F:\ui-auto-test\ui_case_compiler
.\.venv\Scripts\Activate.ps1
ui-case serve
```

另开一个终端：

```powershell
cd F:\ui-auto-test\ui_case_compiler\web
npm.cmd run dev -- --host 127.0.0.1 --port 5173
```

打开：

```text
http://127.0.0.1:5173/
```

## Demo 1：本地登录用例

这个 Demo 最稳定，适合证明项目基础链路完整。

### CLI 演示

```powershell
cd F:\ui-auto-test\ui_case_compiler
.\.venv\Scripts\Activate.ps1
$PAGE_URL = python -c "from pathlib import Path; print(Path('examples/pages/login.html').resolve().as_uri())"
ui-case run examples\plans\login.json --param loginPageUrl=$PAGE_URL --headed
```

讲解点：

- `examples/pages/login.html` 是本地测试页面，不受外网影响。
- `examples/plans/login.json` 是结构化可执行计划。
- 计划里用 `${loginPageUrl}` 做运行时参数替换。
- 执行后生成 `RunResult`、HTML 报告、trace。

### Web 控制台演示

1. 打开 Web 控制台。
2. 找到或创建登录用例。
3. 进入用例详情页。
4. 点击“试运行”或“正式运行”。
5. 进入运行详情页。
6. 展示步骤结果、报告入口、trace 入口。

## Demo 2：实时录制百度搜索

这个 Demo 展示“用户操作一次 -> 自动生成步骤 -> 后续可重复执行”。

录制流程：

1. 打开 Web 控制台首页。
2. 切到“实时录制”。
3. 输入起始 URL：

```text
https://www.baidu.com/
```

4. 点击开始录制。
5. 在打开的浏览器里执行：
   - 点击搜索框
   - 输入 `王俊凯`
   - 点击 `百度一下`
6. 回到控制台点击“停止并生成步骤”。
7. 进入生成的用例详情页。
8. 点击“试运行”。

讲解点：

- 录制阶段收集用户操作事件。
- 编译阶段把事件转换成 `navigate / click / fill` 等 DSL 步骤。
- 回归阶段直接执行 DSL，不再依赖人工重复操作。
- 对百度这类富输入框，执行器有点击后键盘输入兜底。

## Demo 3：直接运行百度示例计划

如果不想现场录制，可以直接运行示例计划：

```powershell
cd F:\ui-auto-test\ui_case_compiler
.\.venv\Scripts\Activate.ps1
ui-case run examples\plans\baidu-search.json --headed
```

这个用例执行：

1. 打开百度首页。
2. 输入 `王俊凯`。
3. 点击 `百度一下`。
4. 验证页面里出现 `王俊凯`。

注意：外网页面可能触发验证码、网络限制或页面改版。如果失败，不要慌，正好可以演示失败调试能力。

## Demo 4：失败调试页

如果某个用例失败，进入运行详情页，按这个顺序讲：

1. 先看第一个 failed 步骤。
2. 看错误信息，比如 `matched 0 elements` 或 `none were usable for input`。
3. 看失败截图，判断页面是否打开到了预期状态。
4. 看 locator 候选，判断主 locator 和备用 locator 是否可靠。
5. 下载 trace，用 Playwright trace viewer 查看完整执行过程。
6. 跳到用例步骤，定位原始 DSL。

可以重点讲这句话：

```text
传统自动化报告只能告诉我失败了，这个项目把失败步骤、页面截图、trace、locator 和原始 DSL 关联起来，方便定位问题。
```

## 面试追问准备

### 为什么要“编译”自然语言，而不是每一步都问大模型？

因为大规模回归里每一步都调用模型会慢、贵、且不稳定。项目采用“创建时编译，执行时跑计划”的方式，让回归执行接近普通 Playwright 脚本。

### 为什么需要 locator fallback？

真实页面经常变化。单个 CSS / XPath 很容易失效，所以每个目标元素保留主 locator 和多个备用 locator，提高执行成功率。

### 为什么百度搜索框会失败？

百度新版首页可能是富输入框结构，页面上看起来是搜索框，但 `#kw` 不一定是 Playwright 可直接 `fill` 的真实输入节点。项目现在支持 `fill` 失败后点击目标并用键盘输入兜底。

### 这个项目和直接写 Playwright 脚本有什么区别？

直接写脚本需要懂代码和页面定位。这个项目把用例创建方式提升到自然语言和录制操作，再统一编译成 DSL，降低测试用例创建门槛，同时保留 Playwright 的稳定执行能力。

### 当前项目边界是什么？

- 适合学习、演示和小规模本地回归。
- 还没有多用户权限、分布式执行、复杂 CI 调度。
- AI 自动修复 locator 还可以作为后续优化方向。
