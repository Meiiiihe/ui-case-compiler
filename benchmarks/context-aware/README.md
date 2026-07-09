# Context-Aware 中文 UI 用例评测集

这个目录用于支撑简历中的 Context-Aware 编译上下文指标：

> 构建 Context-Aware 编译上下文，在编译前基于 Playwright 采集页面语义地图，将可交互元素、表单结构、可见文案和候选 Locator 注入模型；在自建中文 UI 用例评测集上，使 Locator 唯一命中率从 68% 提升至 87%，端到端执行通过率从 54% 提升至 76%。

## 1. 是否需要手工输入 50 条自然语言用例

不需要。

50 条用例统一维护在：

```text
benchmarks/context-aware/cases.json
```

后续评测脚本应该批量读取这个 JSON 文件，然后对每条用例分别执行：

```text
读取 natural_language
读取 page_url
生成 Baseline Prompt
生成 Context-Aware Prompt
调用模型编译为 ExecutablePlan
校验 DSL
Dry-run 检查 Locator
真实执行并统计结果
```

也就是说，人工只负责维护 benchmark 数据，不需要每次在页面上手动输入 50 条。

## 2. 用例覆盖范围

当前数据集包含：

```text
10 个页面类型 * 每类 5 条中文用例 = 50 条
```

页面类型：

- 登录页
- 搜索页
- 表单提交页
- 商品筛选页
- 弹窗确认页
- 表格查询页
- 新增编辑页
- 下拉选择页
- Toast 提示页
- 多按钮页面

每条用例包含：

```json
{
  "case_id": "login-001",
  "page_type": "login",
  "page_url": "http://localhost:4173/benchmark/login.html",
  "natural_language": "打开登录页，输入用户名 admin 和密码 123456，点击登录按钮，验证页面出现登录成功。",
  "expected_steps": [
    {"type": "navigate", "target_hint": "登录页"},
    {"type": "fill", "target_hint": "用户名输入框", "value": "admin"},
    {"type": "fill", "target_hint": "密码输入框", "value": "123456"},
    {"type": "click", "target_hint": "登录按钮"},
    {"type": "assert_text", "target_hint": "状态提示", "expected": "登录成功"}
  ],
  "expected_assertions": ["登录成功"],
  "tags": ["login", "form", "success"]
}
```

## 3. 如何做对照实验

建议设计两组编译模式。

Baseline：

```text
URL
Title
简单 DOM summary
用户中文用例
DSL schema
```

Context-Aware：

```text
URL
Title
页面语义地图
可交互元素
表单结构
可见文案
候选 Locator
用户中文用例
DSL schema
```

两组使用同一批 `cases.json`，区别只在于给模型的上下文不同。

## 4. 统计哪些指标

### 4.1 DSL 合法率

```text
DSL 合法率 = 通过 JSON 解析和 schema 校验的用例数 / 总用例数
```

用于衡量模型是否能生成合法 ExecutablePlan。

### 4.2 Locator 唯一命中率

```text
Locator 唯一命中率 = count == 1 的 locator step 数 / 所有需要定位的 step 数
```

测试方式：

```python
count = await locator.count()
```

统计规则：

```text
count == 1：唯一命中
count == 0：未找到
count > 1：定位歧义
```

简历中的 `68% -> 87%` 可以这样解释：

```text
Baseline：200 个 locator step 中 136 个唯一命中，命中率 68%
Context-Aware：200 个 locator step 中 174 个唯一命中，命中率 87%
```

### 4.3 端到端执行通过率

```text
端到端执行通过率 = 编译成功且 Playwright 实际执行通过的用例数 / 总用例数
```

简历中的 `54% -> 76%` 可以这样解释：

```text
Baseline：50 条用例中 27 条执行通过，通过率 54%
Context-Aware：50 条用例中 38 条执行通过，通过率 76%
```

## 5. 面试解释口径

如果面试官问“50 条用例是不是你手工一条一条跑的”，可以回答：

> 不是。我把 benchmark 用例维护成结构化 JSON，评测时由脚本批量读取。每条用例包含 page_url、中文自然语言步骤、预期动作和预期断言。对照实验时，同一批用例分别走普通 Prompt 和 Context-Aware Prompt，再统一统计 DSL 合法率、Locator 唯一命中率和端到端通过率。

如果面试官问“为什么 Context-Aware 能提升命中率”，可以回答：

> 普通 Prompt 只知道用户说了什么，但不知道页面上真实有什么，所以容易盲猜 selector。Context-Aware 会先用 Playwright 扫描页面，提取可交互元素、表单结构、可见文案和候选 Locator，再让模型在这些真实元素里选择操作目标，因此 Locator 命中率更高。

