# Context-Aware 中文 UI 用例评测集

本目录用于比较 Baseline 与 Context-Aware 两种编译策略在同一批中文 UI 用例上的表现。正式结果仅以 `run_benchmark.py` 生成的 `results/summary.json` 为准；未生成并提交带运行配置的结果前，不声明具体提升幅度。

## 数据集

评测数据统一维护在：

```text
benchmarks/context-aware/cases.json
```

当前包含：

```text
10 个页面类型 * 每类 5 条中文用例 = 50 条用例
```

数据集中的姓名、手机号、邮箱、账号和密码均为合成测试数据。

页面文件位于：

```text
web/public/benchmark/
```

Vite preview 启动后，页面地址形如：

```text
http://localhost:4173/benchmark/login.html
```

## 对照实验

评测脚本对同一批 `cases.json` 分别跑两组：

Baseline：

```text
URL
页面标题
简单 DOM 摘要
用户中文用例
DSL schema
```

Context-Aware：

```text
URL
页面标题
页面语义地图
可交互元素
表单结构
可见文案
候选 Locator
用户中文用例
DSL schema
```

## 指标

DSL 合法率：

```text
通过 JSON 解析和 ExecutablePlan schema 校验的用例数 / 总用例数
```

计划忠实率：

```text
步骤类型与顺序、输入值和期望断言均符合数据集真值的用例数 / 总用例数
```

Locator 唯一命中率：

```text
count == 1 的 locator step 数 / 所有需要定位元素的 step 数
```

该指标只衡量 Locator 是否唯一匹配，不单独证明匹配元素的业务语义正确性。

脚本会同时统计：

```text
primary_locator_unique_rate
resolved_locator_unique_rate
```

端到端通过率：

```text
同时通过计划忠实度校验，并由 Playwright 实际执行通过的用例数 / 总用例数
```

## 运行方式

在仓库根目录安装依赖并构建前端，然后启动 benchmark 页面服务：

```powershell
cd web
npm.cmd run build
npm.cmd run preview -- --host 127.0.0.1 --port 4173
```

在另一个终端回到仓库根目录，通过环境变量配置 DeepSeek API key，再运行真实 LLM 评测：

```powershell
$env:DEEPSEEK_API_KEY = "你的 key"
python benchmarks\context-aware\run_benchmark.py
```

只做本地 smoke test，不调用模型：

```powershell
python benchmarks\context-aware\run_benchmark.py --provider echo --limit 2
```

结果输出：

```text
benchmarks/context-aware/results/summary.json
```

## 设计说明

benchmark 用例维护成结构化 JSON，每条包含 `page_url`、中文自然语言用例、期望动作和期望断言。评测脚本批量读取同一批用例，分别使用 Baseline Prompt 和 Context-Aware Prompt，再统一统计 DSL 合法率、Locator 唯一命中率和端到端通过率。

Baseline Prompt 只包含简化的页面信息；Context-Aware Prompt 会先用 Playwright 扫描页面，提取可交互元素、表单结构、可见文案和候选 Locator，再让模型基于真实页面信息选择操作目标。
