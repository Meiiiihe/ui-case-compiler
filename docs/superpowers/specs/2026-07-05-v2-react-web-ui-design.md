# v2 子项目④：React Web UI 设计

**状态:** 待用户审阅
**日期:** 2026-07-05
**范围:** UI Case Compiler v2 的第四个（最后一个）子项目——React 前端控制台，消费子项目③ 的 HTTP API。

## 背景

前三个子项目让核心能力可用并暴露为 HTTP API：① 真实模型编译、② 真实录制、③ FastAPI 9 类端点。本子项目提供一个 React Web 控制台，让用户在浏览器里创建用例、查看步骤、执行、看结果——无需 CLI。

这是 v2 四个有序子项目的最后一个，也是唯一引入第二种语言（TypeScript）和前端构建链的：

```
① 真实模型 Provider（已完成，已合并）
② 真实录制（已完成，已合并）
③ HTTP API 层（已完成，已合并）
④ React Web UI（本 spec）    ← Vite + TS 消费 API
```

## 环境前提

Node v24.18.0 + npm 11.16.0 已就绪（用户已安装）。依赖版本选稳定版（React 18 / Vite 5 / vitest 2），避免 Node v24 尖端兼容问题。

## 已确定的关键决策

| 决策点 | 结论 |
|--------|------|
| 页面范围 | 核心 3 页：用例列表（含创建入口）、用例详情、运行详情。 |
| 创建入口 | 两种：NL 表单（text + 页面上下文 → compile-nl）+ 录制事件 JSON 上传（→ compile-recording）。实时录制不在 API，故 Web 不提供实时录制。 |
| 技术栈 | React + TS + Vite + 轻量自写 fetch 封装（不引 TanStack Query）+ react-router-dom。 |
| 项目位置 | 仓库内 `web/` 独立 Vite 项目，与 Python `src/` 并列。 |
| 后端连接 | dev 用 Vite proxy 转发 `/api` → http://127.0.0.1:8000。 |
| 方案 | 方案 A：分层轻量 SPA（api client + types + useAsync hook + 3 页 + 组件）。 |

## 方案选择

采用**方案 A**：薄封装层（apiFetch）+ 清晰分层（api / hooks / pages / components），依赖最少却完整可测。备选方案 B（页面内直接 fetch）逻辑散落难维护；方案 C（React Router loader）对 3 页规模过度设计。均弃用。

## 架构与项目结构

```
web/
  package.json          React+TS+Vite+react-router-dom+vitest
  vite.config.ts        dev proxy: /api → http://127.0.0.1:8000
  tsconfig.json         strict 模式，jsx: react-jsx，moduleResolution: bundler
  index.html
  src/
    main.tsx            入口：挂载 App + Router
    App.tsx             路由定义（3 页）
    test-setup.ts       vitest + @testing-library/jest-dom 初始化
    api/
      client.ts         apiFetch 封装 + ApiError
      types.ts          手写 TS 类型镜像后端模型
      cases.ts          用例相关端点函数
      runs.ts           运行相关端点函数
    hooks/
      useAsync.ts       轻量 loading/error/data + 竞态防护
    pages/
      CaseListPage.tsx
      CaseDetailPage.tsx
      RunDetailPage.tsx
    components/
      ErrorBanner.tsx
      Spinner.tsx
      StepList.tsx
      CreateCaseForm.tsx
    styles.css
```

数据流：

```
页面组件 → useAsync(() => api.xxx()) → apiFetch(/api/...) → Vite proxy → FastAPI(127.0.0.1:8000)
```

纯前端，不碰 Python 代码；只通过 9 类 HTTP 端点交互。

## TS 类型（api/types.ts，手写镜像后端）

- `CaseSummary` {id, name, source, step_count}
- `RunSummary` {run_id, plan_id, status, started_at}
- `Locator` / `StepTarget` / `Step` / `ExecutablePlan`（详情页展示步骤）
- `StepResult` / `RunResult`
- 请求体：`CompileNlRequest`（text, context{url,...}, name?）、`CompileRecordingRequest`（events, name）、`RunRequest`（params, headed）
- `ValidateResponse` {valid, plan_id, step_count}

## api 封装

### client.ts

```typescript
export class ApiError extends Error {
  constructor(public status: number, public detail: string) { super(detail); }
}

export async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const resp = await fetch(`/api${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!resp.ok) {
    const body = await resp.json().catch(() => ({ detail: resp.statusText }));
    throw new ApiError(resp.status, body.detail ?? "请求失败");
  }
  return resp.json() as Promise<T>;
}
```

统一：拼 `/api` 前缀（走 proxy）、JSON 头、非 2xx 抛 ApiError（带后端 detail）。

### cases.ts / runs.ts

每个端点一个类型化函数：listCases、compileNl、compileRecording、getCase、updateCase、validateCase、dryRun、runCase、listRuns、getRun。

### hooks/useAsync.ts

接受异步函数，返回 `{data, error, loading, run}`；用递增请求 id 防竞态（只接受最后一次请求结果）；捕获 ApiError 存 error。

## 3 页交互

### CaseListPage（`/`）

- 挂载 listCases() → 表格显示 id/name/source/step_count，点击行跳 `/cases/{id}`。
- 创建区 CreateCaseForm，两个 tab：
  - NL tab：textarea(text) + url（必填）+ 可选 title/dom_summary → compileNl → 成功跳详情。
  - 录制 tab：textarea 粘贴事件 JSON + name → compileRecording → 成功跳详情。
- 错误用 ErrorBanner 显示后端 detail（如缺 api_key 的 400）。

### CaseDetailPage（`/cases/:id`）

- getCase(id) → 元信息（id/name/source/base_url）+ StepList（每步 type/target 概要/value/expected）。
- 三按钮：Validate（→ valid/step_count）、Dry-run、Run。
- Run/Dry-run 提供简单参数输入（key=value 行组成 params）→ 调用后跳 `/runs/{run_id}`。

### RunDetailPage（`/runs/:id`）

- getRun(id) → run_id/plan_id/status（passed/failed 高亮）/起止时间。
- 步骤结果表：step_id/type/status/耗时/error。
- 报告/trace：后端 RunResult 的 report_path/trace_path 是**服务端本地路径**，不是 HTTP 可访问 URL——前端只**显示路径文本**，不做链接下载（避免点了 404 的假链接）。见"已知限制"。

## Vite/TS 配置

```typescript
// vite.config.ts
export default defineConfig({
  plugins: [react()],
  server: { proxy: { "/api": "http://127.0.0.1:8000" } },
  test: { environment: "jsdom", globals: true, setupFiles: "./src/test-setup.ts" },
});
```

依赖版本（稳定版）：

```
dependencies:  react ^18.3, react-dom ^18.3, react-router-dom ^6.26
devDependencies: vite ^5.4, @vitejs/plugin-react ^4.3, typescript ^5.5,
                 vitest ^2.1, @testing-library/react ^16, @testing-library/jest-dom ^6,
                 jsdom ^25, @types/react ^18, @types/react-dom ^18
```

tsconfig：strict，jsx react-jsx，moduleResolution bundler。

## 测试策略

vitest + React Testing Library，不打真实网络：

1. **api/client**：mock fetch，验证拼 /api 前缀、2xx 返回 JSON、非 2xx 抛 ApiError 带 detail。
2. **useAsync**：loading→data 流转、error 捕获、竞态（后发先至只保留最后结果）。
3. **页面组件**：vi.mock api 模块，渲染各页，断言 CaseList 渲染行 + 创建表单提交 + 缺 url 校验；CaseDetail 渲染步骤 + 点 Run 调 runCase；RunDetail 渲染状态/步骤/路径文本。
4. **构建冒烟**：npm run build 成功（tsc 类型检查 + vite 打包）。

本地验证：npm install → npm run test 全绿 → npm run build 成功。端到端手动验证需用户起后端：`ui-case serve` + `npm run dev`，浏览器验证真实调通。

## 已知限制（归入子项目③ 后续增强）

报告/trace 是服务端本地路径，不是 API 可访问资源。要让 Web UI 真正打开报告，后端需加静态文件服务端点（如 `GET /api/runs/{id}/report`）——属于子项目③ 范畴，不在本子项目。本子项目前端只显示路径文本。

## 非目标（本子项目不做）

- 不做鉴权/登录（沿用 v2 本地无鉴权定位）。
- 不做实时录制界面（实时录制不在 API，保留 CLI）。
- 不引入 TanStack Query 等重数据层。
- 不改动 Python 后端代码（仅通过 HTTP 交互）。
- 不做报告静态文件服务（归子项目③ 后续）。
- 不做生产部署配置（dev 为主，build 产物仅冒烟验证）。
- 不做步骤编辑器 UI（PUT /cases/{id} 仅用于创建后保存整份计划，详情页以展示+执行为主，不提供逐字段编辑）。
