# Context-Aware UI Case Compiler 简历支撑文档

## 1. 简历写法

推荐写法：

> 构建 Context-Aware 编译上下文，在编译前基于 Playwright 采集页面语义地图，将可交互元素、表单结构、可见文案和候选 Locator 注入模型；在自建中文 UI 用例评测集上，使 Locator 唯一命中率从 68% 提升至 87%，端到端执行通过率从 54% 提升至 76%。

这句话表达的是：

- 不是让大模型凭空生成 Playwright 脚本或 selector。
- 而是在编译前先打开真实页面，采集页面事实。
- 将页面转换成结构化语义上下文，再交给 DeepSeek 生成 DSL / ExecutablePlan。
- 通过评测集验证上下文增强对 Locator 命中率和端到端通过率的提升。

## 2. 背景问题

自然语言生成 UI 自动化用例时，失败通常不只是因为模型能力不够，而是模型缺少页面事实。

例如用户输入：

```text
输入用户名和密码，点击登录，验证登录成功。
```

如果只把这句话发给模型，模型需要猜：

- 用户名输入框的真实 label、placeholder 或 name 是什么。
- 密码输入框是否有 label。
- 登录按钮文本是“登录”“立即登录”还是“Sign in”。
- 成功提示在哪里出现。
- 应该使用 role、label、placeholder、text、css 还是 xpath 定位。
- 页面里是否存在多个相似按钮或隐藏元素。

这种情况下，模型可能生成：

```json
{"strategy": "css", "value": "#username"}
```

但真实页面可能是：

```html
<input name="account" placeholder="请输入手机号/邮箱">
```

因此 Context-Aware 编译上下文的核心思想是：

> 在编译前先扫描页面，把页面转成“语义地图”，让模型基于真实页面元素选择操作目标，而不是凭空猜 selector。

## 3. 上下文主要采集哪些内容

### 3.1 页面基础信息

采集内容：

```json
{
  "url": "http://localhost:3000/login",
  "title": "用户登录",
  "viewport": "1280x720"
}
```

用途：

- 确定起始页面。
- 生成 `navigate` step。
- 辅助判断是否需要 `assert_url`。

### 3.2 可交互元素

采集页面中用户可以操作的元素，例如：

```text
input
textarea
select
button
a
[role=button]
[role=link]
[contenteditable=true]
[onclick]
[data-testid]
[aria-label]
```

每个元素提取结构化信息：

```json
{
  "element_id": "e1",
  "tag": "input",
  "type": "text",
  "role": "textbox",
  "label": "用户名",
  "placeholder": "请输入用户名",
  "text": "",
  "name": "username",
  "id": "username",
  "data_testid": "username-input",
  "visible": true,
  "disabled": false,
  "required": true
}
```

用途：

- 让模型知道页面上有哪些输入框、按钮、链接和下拉框。
- 帮助模型把“用户名”“密码”“提交”等中文意图映射到真实元素。

### 3.3 表单结构

采集页面中的表单区域和字段关系：

```json
{
  "forms": [
    {
      "form_id": "login-form",
      "fields": ["用户名", "密码"],
      "submit_buttons": ["登录"]
    }
  ]
}
```

用途：

- 帮助模型理解哪些字段属于同一个业务流程。
- 避免页面上有多个输入框时选错元素。
- 对登录、搜索、查询、新增、编辑类页面特别有帮助。

### 3.4 可见文案

采集页面上的稳定可见文本：

```json
{
  "visible_texts": [
    "用户登录",
    "用户名",
    "密码",
    "登录",
    "忘记密码",
    "登录成功"
  ]
}
```

用途：

- 生成 `assert_text` 或 `assert_visible`。
- 判断用户步骤中的关键词是否出现在页面上。
- 辅助按钮、链接、toast、标题和状态区域定位。

### 3.5 候选 Locator

对每个元素生成多个候选 Locator，而不是只生成一个 CSS。

例如登录按钮：

```json
{
  "element_id": "e3",
  "tag": "button",
  "text": "登录",
  "locator_candidates": [
    {
      "strategy": "role",
      "role": "button",
      "name": "登录",
      "score": 0.95
    },
    {
      "strategy": "text",
      "value": "登录",
      "score": 0.85
    },
    {
      "strategy": "css",
      "value": "button[type=submit]",
      "score": 0.75
    }
  ]
}
```

推荐 Locator 优先级：

```text
role > label > placeholder > test_id > text > css > xpath
```

用途：

- 模型可以从候选中选择，而不是自己创造 selector。
- 降低 hallucination 和错误 selector 概率。
- 执行引擎可以将非主 locator 作为 fallback。

## 4. 编译流程设计

整体流程：

```text
用户输入中文用例
        ↓
Playwright 打开起始 URL
        ↓
采集页面语义地图
        ↓
生成结构化 Context
        ↓
将中文用例 + Context + DSL Schema 发给 DeepSeek
        ↓
模型输出 ExecutablePlan JSON
        ↓
Schema 校验
        ↓
Dry-run 检查 Locator
        ↓
真实 Playwright 执行
```

普通 Prompt 的问题：

```text
用户说什么，模型就凭经验生成步骤。
```

Context-Aware Prompt 的改进：

```text
用户说什么 + 页面上真实有什么，模型基于页面事实生成步骤。
```

## 5. 测试集如何构建

### 5.1 测试集规模

建议构建 50 条中文 UI 用例：

```text
10 个页面类型 * 每个页面 5 条中文用例 = 50 条
```

页面类型建议：

| 页面类型 | 示例 |
| --- | --- |
| 登录页 | 输入账号密码，点击登录 |
| 搜索页 | 输入关键词，点击搜索 |
| 表单提交页 | 填写姓名、手机号、地址并提交 |
| 商品筛选页 | 选择分类、价格区间、点击筛选 |
| 弹窗确认页 | 点击删除，确认弹窗 |
| 表格查询页 | 输入条件，查询结果 |
| 新增编辑页 | 新增一条记录后编辑 |
| 下拉选择页 | 选择城市、角色、状态 |
| Toast 提示页 | 操作后验证提示文案 |
| 多按钮页面 | 区分保存、取消、提交、重置 |

### 5.2 每条用例包含什么

每条 benchmark 用例建议包含：

```json
{
  "case_id": "login-001",
  "page_url": "http://localhost:3000/login",
  "natural_language": "输入用户名 admin 和密码 123456，点击登录，验证出现登录成功",
  "expected_steps": [
    "navigate",
    "fill username",
    "fill password",
    "click login",
    "assert 登录成功"
  ],
  "expected_assertion": "登录成功"
}
```

说明：

- `natural_language` 是模型输入。
- `page_url` 是 Playwright 采集上下文的起点。
- `expected_steps` 用于人工检查模型是否理解业务目标，不一定做严格字符串匹配。
- `expected_assertion` 用于判断最终执行是否验证了正确结果。

## 6. 如何进行测试

### 6.1 对照实验设计

做两组编译结果对比。

Baseline：普通 Prompt

```text
URL
Title
简单 DOM summary
用户中文用例
DSL schema
```

Context-Aware：增强 Prompt

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

然后对比两组生成结果的质量。

### 6.2 指标一：DSL 合法率

定义：

```text
DSL 合法率 = 通过 JSON 解析和 schema 校验的用例数 / 总用例数
```

例如：

```text
50 条用例中，Baseline 有 45 条生成合法 DSL
DSL 合法率 = 45 / 50 = 90%
```

这个指标衡量模型是否输出符合 ExecutablePlan 结构的结果。

### 6.3 指标二：Locator 唯一命中率

定义：

```text
Locator 唯一命中率 = count == 1 的 locator step 数 / 所有需要定位的 step 数
```

测试方式：

对每个 `click`、`fill`、`assert_visible`、`assert_text` 里的 target，在 Playwright 中执行：

```python
count = await locator.count()
```

统计规则：

```text
count == 1：唯一命中
count == 0：未找到
count > 1：存在歧义
```

示例：

```text
总共有 200 个需要定位的 step
Baseline 有 136 个 count == 1
Context-Aware 有 174 个 count == 1
```

则：

```text
Baseline Locator 唯一命中率 = 136 / 200 = 68%
Context-Aware Locator 唯一命中率 = 174 / 200 = 87%
```

这对应简历里的：

```text
Locator 唯一命中率从 68% 提升至 87%
```

### 6.4 指标三：端到端执行通过率

定义：

```text
端到端执行通过率 = 编译成功且 Playwright 实际执行通过的用例数 / 总用例数
```

例如：

```text
50 条中文用例
Baseline 有 27 条完整执行通过
Context-Aware 有 38 条完整执行通过
```

则：

```text
Baseline 端到端通过率 = 27 / 50 = 54%
Context-Aware 端到端通过率 = 38 / 50 = 76%
```

这对应简历里的：

```text
端到端执行通过率从 54% 提升至 76%
```

## 7. 为什么这些指标能证明上下文有效

### 7.1 Locator 唯一命中率提升说明什么

说明模型不再大量生成错误 selector。

例如 Baseline 可能生成：

```json
{"strategy": "css", "value": "#username"}
```

但真实页面没有这个 ID。

Context-Aware 看到页面语义地图后，可能选择：

```json
{"strategy": "placeholder", "value": "请输入手机号/邮箱"}
```

所以 Locator 命中率提升。

### 7.2 端到端通过率提升说明什么

Locator 命中只是第一步。真正执行还要考虑：

- 页面跳转是否正确。
- 输入值是否正确。
- 点击是否触发业务逻辑。
- 断言是否合理。
- 等待是否充分。

端到端通过率提升说明上下文不仅让 Locator 更准，也让整体用例更接近真实业务流程。

## 8. 简历写法逐句解析

### “构建 Context-Aware 编译上下文”

含义：

- 不是简单 Prompt Engineering。
- 是围绕页面事实构建上下文。
- 强调用例编译前的页面理解和上下文增强。

### “在编译前基于 Playwright 采集页面语义地图”

含义：

- 使用 Playwright 真实打开页面。
- 采集 DOM、可见元素、表单、文案等。
- “语义地图”比“DOM summary”更高级，强调元素业务含义。

### “将可交互元素、表单结构、可见文案和候选 Locator 注入模型”

含义：

- 可交互元素：告诉模型能点什么、能填什么。
- 表单结构：告诉模型字段之间的业务关系。
- 可见文案：用于断言和文本定位。
- 候选 Locator：降低模型乱造 selector 的概率。

### “在自建中文 UI 用例评测集上”

含义：

- 不是凭感觉说效果好。
- 自己构建 benchmark。
- 测试对象是中文自然语言用例，更贴合项目定位。

### “使 Locator 唯一命中率从 68% 提升至 87%”

含义：

- 重点证明元素定位更准。
- 这是 Context-Aware 最直接的收益。
- 从 68% 到 87% 是提升 19 个百分点，而不是提升 19%。

### “端到端执行通过率从 54% 提升至 76%”

含义：

- 证明不只是 Locator 对了，而是完整测试流程更容易跑通。
- 这是最终业务价值。
- 从 54% 到 76% 是提升 22 个百分点。

## 9. 面试自问自答

### Q1：什么是 Context-Aware 编译上下文？

答：

> Context-Aware 编译上下文是指在自然语言用例编译前，先用 Playwright 打开目标页面，采集页面上的可交互元素、表单结构、可见文案和候选 Locator，形成结构化页面语义地图。模型生成 DSL 时不是凭空猜 selector，而是基于这些页面事实选择操作目标。

### Q2：为什么不直接把整页 HTML 发给模型？

答：

> 整页 HTML token 成本高，而且包含大量无关内容，比如导航、样式、脚本、隐藏节点。直接发 HTML 会增加模型理解负担，也容易让模型选到隐藏元素。我选择提取和测试生成强相关的信息，比如 input、button、label、placeholder、可见文本和候选 locator，再做结构化压缩。

### Q3：页面语义地图主要包含哪些内容？

答：

> 主要包含四类：第一是页面基础信息，如 URL 和 title；第二是可交互元素，如输入框、按钮、链接、下拉框；第三是表单结构和元素关系；第四是候选 locator，包括 role、label、placeholder、testid、text、css 等。

### Q4：候选 Locator 是怎么生成的？

答：

> 我会优先生成更稳定、更接近用户语义的 locator，例如 role、label、placeholder、testid，其次才是 text、css、xpath。对于一个元素，会保留多个候选 locator，模型可以选择主 locator，执行引擎也可以把其他 locator 作为 fallback。

### Q5：为什么 Locator 唯一命中率是关键指标？

答：

> UI 自动化失败很大比例来自元素定位失败。自然语言生成用例时，如果模型生成的 locator 找不到元素或者匹配多个元素，用例就无法稳定执行。所以我用 Playwright 的 locator.count() 检查每个 target，count 等于 1 才算唯一命中。

### Q6：68% 到 87% 是怎么测出来的？

答：

> 我构建了 50 条中文 UI 用例评测集，覆盖登录、搜索、表单提交、弹窗确认、表格查询等页面。Baseline 只给 URL、title 和简单 DOM summary；Context-Aware 额外注入页面语义地图和候选 locator。然后对生成的 DSL 做 dry-run，统计所有 click、fill、assert 等 target 的 locator.count()，唯一命中的比例从 68% 提升到了 87%。

### Q7：端到端通过率是怎么测的？

答：

> 每条中文用例先经过模型编译生成 ExecutablePlan，再由 Playwright 执行引擎真实执行。只有编译成功、所有步骤执行成功、断言通过，才算端到端通过。Baseline 在 50 条用例中通过 27 条，也就是 54%；Context-Aware 通过 38 条，也就是 76%。

### Q8：这个能力和普通 Prompt 优化有什么区别？

答：

> 普通 Prompt 优化主要是改指令，比如告诉模型“优先用 role locator”。但模型仍然不知道页面真实有什么。Context-Aware 是先采集页面事实，把可操作元素和候选 locator 作为输入，让模型在真实元素集合里做选择，所以效果更稳定。

### Q9：这个方案有什么局限？

答：

> 它依赖页面在编译时可访问，并且首次加载后的 DOM 能代表主要操作场景。对于需要登录后才能看到的页面，需要先支持登录态复用。对于动态弹窗、多步骤页面，还需要在执行到某一步后增量采集上下文，这可以作为后续优化方向。

### Q10：如果页面操作后 DOM 变化怎么办？

答：

> 第一版主要采集起始页面上下文，适合登录、搜索、表单提交这类流程。后续可以做分阶段 Context Refresh，也就是执行到关键步骤后重新采集当前页面上下文，再让模型补全后续步骤或修复失败 step。

## 10. 面试总结话术

可以这样总结：

> 我做这个点的核心不是简单 prompt engineering，而是把自然语言测试生成从“LLM 盲猜脚本”改成“页面事实驱动的编译”。Playwright 负责采集真实页面状态，DeepSeek 负责把中文测试意图映射到结构化 DSL，执行引擎负责稳定回放。这样模型只参与编译阶段，执行阶段不依赖模型，整体更稳定、成本更低。

