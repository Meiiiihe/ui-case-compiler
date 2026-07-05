# v2 子项目④ React Web UI 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在仓库内 `web/` 建一个 React+TS+Vite 前端控制台,核心 3 页(用例列表/详情、运行详情),消费子项目③ 的 9 类 HTTP 端点。

**Architecture:** 分层轻量 SPA:api client(apiFetch+ApiError)+ 手写 TS 类型镜像后端 + 端点函数 + useAsync hook(防竞态)+ 3 页 + 共享组件。dev 用 Vite proxy 转发 /api 到 127.0.0.1:8000。不碰 Python 后端,只通过 HTTP 交互。

**Tech Stack:** React 18、TypeScript 5.5、Vite 5、react-router-dom 6、vitest 2、@testing-library/react 16、jsdom。

## Global Constraints

- Node v24.18.0 / npm 11.16.0 已就绪。
- 依赖用稳定版避开 Node v24 兼容问题:react ^18.3、react-dom ^18.3、react-router-dom ^6.26、vite ^5.4、@vitejs/plugin-react ^4.3、typescript ^5.5、vitest ^2.1、@testing-library/react ^16、@testing-library/jest-dom ^6、jsdom ^25、@types/react ^18、@types/react-dom ^18。
- 项目根目录:`web/`(与 Python `src/` 并列)。所有前端命令在 `web/` 内运行。
- dev proxy:`/api` → `http://127.0.0.1:8000`。
- apiFetch 拼 `/api` 前缀,JSON 头,非 2xx 抛 `ApiError(status, detail)`(读后端 `{detail}`)。
- 不改动 Python 后端代码;只通过 9 类 HTTP 端点交互。
- 不引入 TanStack Query;用自写 useAsync。
- 不做步骤编辑器 UI;不做鉴权;不做实时录制界面;报告/trace 只显示服务端路径文本。
- tsconfig strict;测试用 vitest + RTL,mock fetch/api 模块,不打真实网络。
- 提交信息结尾:`Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`。

## 后端契约(前端类型须对齐,来自子项目③ 已合并代码)

- `GET /api/cases` → `CaseSummary[]`:{id:string, name:string, source:string, step_count:number}
- `POST /api/cases/compile-nl` body {text:string, context:{url:string, title?:string, accessibility_tree?:string, dom_summary?:string, screenshot_path?:string}, name?:string} → `ExecutablePlan`
- `POST /api/cases/compile-recording` body {events:object[], name:string} → `ExecutablePlan`
- `GET /api/cases/{id}` → `ExecutablePlan`;不存在 → 404 {detail}
- `PUT /api/cases/{id}` body `ExecutablePlan` → `ExecutablePlan`
- `POST /api/cases/{id}/validate` → `ValidateResponse`:{valid:boolean, plan_id:string, step_count:number}
- `POST /api/cases/{id}/dry-run` body {params:Record<string,string>, headed:boolean} → `RunResult`
- `POST /api/cases/{id}/run` body 同上 → `RunResult`
- `GET /api/runs` → `RunSummary[]`:{run_id:string, plan_id:string, status:string, started_at:string}
- `GET /api/runs/{id}` → `RunResult`;不存在 → 404
- `ExecutablePlan`:{id, name, source, base_url:string|null, parameters:object, environment:string|null, steps:Step[]}
- `Step`:{id, type, name:string|null, timeout_ms:number|null, ...type 特有字段(url/target/value/expected/duration_ms/checked)}
- `Locator`:{strategy, value:string|null, role:string|null, name:string|null}
- `StepTarget`:{primary:Locator, fallbacks:Locator[], confidence:number}
- `RunResult`:{run_id, plan_id, status:"passed"|"failed", started_at, ended_at, steps:StepResult[], trace_path:string|null, video_paths:string[], report_path:string|null}
- `StepResult`:{step_id, step_type, status:"passed"|"failed"|"skipped", duration_ms, error:string|null, screenshot:string|null}

---

## File Structure

- `web/package.json`、`web/vite.config.ts`、`web/tsconfig.json`、`web/tsconfig.node.json`、`web/index.html`、`web/.gitignore` — 脚手架与配置。
- `web/src/main.tsx`、`web/src/App.tsx`、`web/src/styles.css`、`web/src/test-setup.ts` — 入口、路由、样式、测试初始化。
- `web/src/api/types.ts` — TS 类型。
- `web/src/api/client.ts` — apiFetch + ApiError。
- `web/src/api/cases.ts`、`web/src/api/runs.ts` — 端点函数。
- `web/src/hooks/useAsync.ts` — 异步 hook。
- `web/src/components/ErrorBanner.tsx`、`Spinner.tsx`、`StepList.tsx`、`CreateCaseForm.tsx` — 共享组件。
- `web/src/pages/CaseListPage.tsx`、`CaseDetailPage.tsx`、`RunDetailPage.tsx` — 3 页。
- 测试:各 `*.test.ts(x)` 与被测文件同目录。

任务顺序:1 脚手架 → 2 类型+client → 3 端点函数 → 4 useAsync → 5 共享组件 → 6 CaseList+创建 → 7 CaseDetail → 8 RunDetail + 全量构建冒烟。

---

### Task 1: Vite 项目脚手架

**Files:**
- Create: `web/package.json`、`web/vite.config.ts`、`web/tsconfig.json`、`web/tsconfig.node.json`、`web/index.html`、`web/.gitignore`、`web/src/main.tsx`、`web/src/App.tsx`、`web/src/styles.css`、`web/src/test-setup.ts`

**Interfaces:**
- Consumes: 无
- Produces: 可 `npm install`、`npm run build`、`npm run test` 的空壳项目;`App` 组件带 3 条路由占位。

- [ ] **Step 1: 创建 package.json**

`web/package.json`:

```json
{
  "name": "ui-case-web",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "preview": "vite preview",
    "test": "vitest run"
  },
  "dependencies": {
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "react-router-dom": "^6.26.0"
  },
  "devDependencies": {
    "@testing-library/jest-dom": "^6.4.0",
    "@testing-library/react": "^16.0.0",
    "@testing-library/user-event": "^14.5.0",
    "@types/react": "^18.3.0",
    "@types/react-dom": "^18.3.0",
    "@vitejs/plugin-react": "^4.3.0",
    "jsdom": "^25.0.0",
    "typescript": "^5.5.0",
    "vite": "^5.4.0",
    "vitest": "^2.1.0"
  }
}
```

- [ ] **Step 2: 创建配置文件**

`web/vite.config.ts`:

```typescript
/// <reference types="vitest/config" />
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: { "/api": "http://127.0.0.1:8000" },
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: "./src/test-setup.ts",
  },
});
```

`web/tsconfig.json`:

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "useDefineForClassFields": true,
    "lib": ["ES2022", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true,
    "types": ["vitest/globals", "@testing-library/jest-dom"]
  },
  "include": ["src"],
  "references": [{ "path": "./tsconfig.node.json" }]
}
```

`web/tsconfig.node.json`:

```json
{
  "compilerOptions": {
    "composite": true,
    "skipLibCheck": true,
    "module": "ESNext",
    "moduleResolution": "bundler",
    "allowSyntheticDefaultImports": true,
    "strict": true,
    "noEmit": true
  },
  "include": ["vite.config.ts"]
}
```

`web/.gitignore`:

```
node_modules
dist
*.local
```

- [ ] **Step 3: 创建 index.html 与入口**

`web/index.html`:

```html
<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>UI Case Compiler</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

`web/src/main.tsx`:

```tsx
import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { App } from "./App";
import "./styles.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </React.StrictMode>,
);
```

`web/src/App.tsx`:

```tsx
import { Link, Route, Routes } from "react-router-dom";
import { CaseListPage } from "./pages/CaseListPage";
import { CaseDetailPage } from "./pages/CaseDetailPage";
import { RunDetailPage } from "./pages/RunDetailPage";

export function App() {
  return (
    <div className="app">
      <header className="app-header">
        <Link to="/">UI Case Compiler</Link>
      </header>
      <main className="app-main">
        <Routes>
          <Route path="/" element={<CaseListPage />} />
          <Route path="/cases/:caseId" element={<CaseDetailPage />} />
          <Route path="/runs/:runId" element={<RunDetailPage />} />
        </Routes>
      </main>
    </div>
  );
}
```

`web/src/styles.css`:

```css
:root { font-family: system-ui, Arial, sans-serif; color: #1f2937; }
body { margin: 0; }
.app-header { padding: 12px 20px; background: #f3f4f6; border-bottom: 1px solid #d1d5db; }
.app-header a { font-weight: 700; color: #1f2937; text-decoration: none; }
.app-main { padding: 20px; max-width: 900px; margin: 0 auto; }
table { border-collapse: collapse; width: 100%; margin-top: 12px; }
th, td { border: 1px solid #d1d5db; padding: 6px 10px; text-align: left; }
th { background: #f3f4f6; }
.passed { color: #047857; font-weight: 700; }
.failed { color: #b91c1c; font-weight: 700; }
.skipped { color: #92400e; font-weight: 700; }
.error-banner { background: #fef2f2; border: 1px solid #fca5a5; color: #b91c1c; padding: 8px 12px; margin: 8px 0; }
button { padding: 6px 12px; margin-right: 8px; cursor: pointer; }
textarea, input { font-family: inherit; padding: 6px; box-sizing: border-box; }
.tab-active { font-weight: 700; }
```

`web/src/test-setup.ts`:

```typescript
import "@testing-library/jest-dom";
```

注意:App.tsx 引用了尚不存在的 3 个页面组件。本任务先创建**占位**页面文件让构建通过——每个页面文件先写一个最小占位组件,后续任务替换为完整实现。创建占位:

`web/src/pages/CaseListPage.tsx`:

```tsx
export function CaseListPage() {
  return <div>CaseListPage</div>;
}
```

`web/src/pages/CaseDetailPage.tsx`:

```tsx
export function CaseDetailPage() {
  return <div>CaseDetailPage</div>;
}
```

`web/src/pages/RunDetailPage.tsx`:

```tsx
export function RunDetailPage() {
  return <div>RunDetailPage</div>;
}
```

- [ ] **Step 4: 安装依赖**

Run: `cd web && npm install`
Expected: 生成 node_modules 和 package-lock.json,无 error(peer warning 可接受)。

- [ ] **Step 5: 构建冒烟**

Run: `cd web && npm run build`
Expected: tsc 类型检查通过 + vite 打包成功,生成 dist/,无 error。

- [ ] **Step 6: 提交**

```bash
cd F:/ui-auto-test/ui_case_compiler
git add web/package.json web/package-lock.json web/vite.config.ts web/tsconfig.json web/tsconfig.node.json web/index.html web/.gitignore web/src/
git commit -m "feat(web): Vite+React+TS 脚手架与 3 页路由占位

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 2: TS 类型 + api client

**Files:**
- Create: `web/src/api/types.ts`、`web/src/api/client.ts`、`web/src/api/client.test.ts`

**Interfaces:**
- Consumes: 无
- Produces:
  - types.ts:导出 CaseSummary、RunSummary、Locator、StepTarget、Step、ExecutablePlan、StepResult、RunResult、CompileNlRequest、CompileRecordingRequest、RunRequest、ValidateResponse、PageContext。
  - client.ts:`class ApiError extends Error { status: number; detail: string }`;`apiFetch<T>(path: string, options?: RequestInit): Promise<T>`。

- [ ] **Step 1: 写失败测试**

`web/src/api/client.test.ts`:

```typescript
import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiError, apiFetch } from "./client";

afterEach(() => {
  vi.restoreAllMocks();
});

function mockFetch(status: number, body: unknown): void {
  vi.stubGlobal(
    "fetch",
    vi.fn(async () =>
      new Response(JSON.stringify(body), {
        status,
        headers: { "Content-Type": "application/json" },
      }),
    ),
  );
}

describe("apiFetch", () => {
  it("prefixes /api and returns parsed json on 200", async () => {
    mockFetch(200, { id: "p1" });
    const result = await apiFetch<{ id: string }>("/cases/p1");
    expect(result).toEqual({ id: "p1" });
    expect(fetch).toHaveBeenCalledWith("/api/cases/p1", expect.objectContaining({
      headers: expect.objectContaining({ "Content-Type": "application/json" }),
    }));
  });

  it("throws ApiError with backend detail on non-2xx", async () => {
    mockFetch(404, { detail: "Case not found: x" });
    await expect(apiFetch("/cases/x")).rejects.toMatchObject({
      status: 404,
      detail: "Case not found: x",
    });
  });

  it("throws ApiError even when body is not json", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response("boom", { status: 500 })),
    );
    await expect(apiFetch("/cases")).rejects.toBeInstanceOf(ApiError);
  });
});
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd web && npx vitest run src/api/client.test.ts`
Expected: FAIL(找不到 ./client 模块)。

- [ ] **Step 3: 实现 types.ts**

`web/src/api/types.ts`:

```typescript
export interface CaseSummary {
  id: string;
  name: string;
  source: string;
  step_count: number;
}

export interface RunSummary {
  run_id: string;
  plan_id: string;
  status: string;
  started_at: string;
}

export interface Locator {
  strategy: string;
  value: string | null;
  role: string | null;
  name: string | null;
}

export interface StepTarget {
  primary: Locator;
  fallbacks: Locator[];
  confidence: number;
}

export interface Step {
  id: string;
  type: string;
  name: string | null;
  timeout_ms: number | null;
  url?: string;
  target?: StepTarget;
  value?: string;
  expected?: string;
  duration_ms?: number;
  checked?: boolean;
}

export interface ExecutablePlan {
  id: string;
  name: string;
  source: string;
  base_url: string | null;
  parameters: Record<string, unknown>;
  environment: string | null;
  steps: Step[];
}

export interface StepResult {
  step_id: string;
  step_type: string;
  status: "passed" | "failed" | "skipped";
  duration_ms: number;
  error: string | null;
  screenshot: string | null;
}

export interface RunResult {
  run_id: string;
  plan_id: string;
  status: "passed" | "failed";
  started_at: string;
  ended_at: string;
  steps: StepResult[];
  trace_path: string | null;
  video_paths: string[];
  report_path: string | null;
}

export interface PageContext {
  url: string;
  title?: string;
  accessibility_tree?: string;
  dom_summary?: string;
  screenshot_path?: string;
}

export interface CompileNlRequest {
  text: string;
  context: PageContext;
  name?: string;
}

export interface CompileRecordingRequest {
  events: Record<string, unknown>[];
  name: string;
}

export interface RunRequest {
  params: Record<string, string>;
  headed: boolean;
}

export interface ValidateResponse {
  valid: boolean;
  plan_id: string;
  step_count: number;
}
```

- [ ] **Step 4: 实现 client.ts**

`web/src/api/client.ts`:

```typescript
export class ApiError extends Error {
  constructor(
    public status: number,
    public detail: string,
  ) {
    super(detail);
    this.name = "ApiError";
  }
}

export async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const resp = await fetch(`/api${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!resp.ok) {
    const body = await resp.json().catch(() => ({ detail: resp.statusText }));
    const detail = typeof body?.detail === "string" ? body.detail : "请求失败";
    throw new ApiError(resp.status, detail);
  }
  return (await resp.json()) as T;
}
```

- [ ] **Step 5: 运行测试确认通过**

Run: `cd web && npx vitest run src/api/client.test.ts`
Expected: 3 个测试 PASS。

- [ ] **Step 6: 提交**

```bash
cd F:/ui-auto-test/ui_case_compiler
git add web/src/api/types.ts web/src/api/client.ts web/src/api/client.test.ts
git commit -m "feat(web): TS 类型镜像后端 + apiFetch/ApiError 封装

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 3: 端点函数

**Files:**
- Create: `web/src/api/cases.ts`、`web/src/api/runs.ts`、`web/src/api/cases.test.ts`

**Interfaces:**
- Consumes: Task 2 apiFetch、types。
- Produces:
  - cases.ts:`listCases()`、`compileNl(req)`、`compileRecording(req)`、`getCase(id)`、`updateCase(id, plan)`、`validateCase(id)`、`dryRun(id, req)`、`runCase(id, req)`。
  - runs.ts:`listRuns()`、`getRun(id)`。

- [ ] **Step 1: 写失败测试**

`web/src/api/cases.test.ts`:

```typescript
import { afterEach, describe, expect, it, vi } from "vitest";
import * as client from "./client";
import { compileNl, listCases, runCase, validateCase } from "./cases";

afterEach(() => vi.restoreAllMocks());

describe("cases api", () => {
  it("listCases calls GET /cases", async () => {
    const spy = vi.spyOn(client, "apiFetch").mockResolvedValue([]);
    await listCases();
    expect(spy).toHaveBeenCalledWith("/cases");
  });

  it("compileNl posts to /cases/compile-nl", async () => {
    const spy = vi.spyOn(client, "apiFetch").mockResolvedValue({ id: "nl" });
    await compileNl({ text: "go", context: { url: "https://x" } });
    expect(spy).toHaveBeenCalledWith(
      "/cases/compile-nl",
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("validateCase posts to /cases/{id}/validate", async () => {
    const spy = vi.spyOn(client, "apiFetch").mockResolvedValue({ valid: true });
    await validateCase("p1");
    expect(spy).toHaveBeenCalledWith(
      "/cases/p1/validate",
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("runCase posts params to /cases/{id}/run", async () => {
    const spy = vi.spyOn(client, "apiFetch").mockResolvedValue({ run_id: "r1" });
    await runCase("p1", { params: { a: "b" }, headed: false });
    expect(spy).toHaveBeenCalledWith(
      "/cases/p1/run",
      expect.objectContaining({ method: "POST", body: JSON.stringify({ params: { a: "b" }, headed: false }) }),
    );
  });
});
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd web && npx vitest run src/api/cases.test.ts`
Expected: FAIL(找不到 ./cases)。

- [ ] **Step 3: 实现 cases.ts**

`web/src/api/cases.ts`:

```typescript
import { apiFetch } from "./client";
import type {
  CompileNlRequest,
  CompileRecordingRequest,
  ExecutablePlan,
  CaseSummary,
  RunRequest,
  RunResult,
  ValidateResponse,
} from "./types";

export function listCases(): Promise<CaseSummary[]> {
  return apiFetch<CaseSummary[]>("/cases");
}

export function compileNl(req: CompileNlRequest): Promise<ExecutablePlan> {
  return apiFetch<ExecutablePlan>("/cases/compile-nl", {
    method: "POST",
    body: JSON.stringify(req),
  });
}

export function compileRecording(req: CompileRecordingRequest): Promise<ExecutablePlan> {
  return apiFetch<ExecutablePlan>("/cases/compile-recording", {
    method: "POST",
    body: JSON.stringify(req),
  });
}

export function getCase(id: string): Promise<ExecutablePlan> {
  return apiFetch<ExecutablePlan>(`/cases/${id}`);
}

export function updateCase(id: string, plan: ExecutablePlan): Promise<ExecutablePlan> {
  return apiFetch<ExecutablePlan>(`/cases/${id}`, {
    method: "PUT",
    body: JSON.stringify(plan),
  });
}

export function validateCase(id: string): Promise<ValidateResponse> {
  return apiFetch<ValidateResponse>(`/cases/${id}/validate`, { method: "POST" });
}

export function dryRun(id: string, req: RunRequest): Promise<RunResult> {
  return apiFetch<RunResult>(`/cases/${id}/dry-run`, {
    method: "POST",
    body: JSON.stringify(req),
  });
}

export function runCase(id: string, req: RunRequest): Promise<RunResult> {
  return apiFetch<RunResult>(`/cases/${id}/run`, {
    method: "POST",
    body: JSON.stringify(req),
  });
}
```

- [ ] **Step 4: 实现 runs.ts**

`web/src/api/runs.ts`:

```typescript
import { apiFetch } from "./client";
import type { RunResult, RunSummary } from "./types";

export function listRuns(): Promise<RunSummary[]> {
  return apiFetch<RunSummary[]>("/runs");
}

export function getRun(id: string): Promise<RunResult> {
  return apiFetch<RunResult>(`/runs/${id}`);
}
```

- [ ] **Step 5: 运行测试确认通过**

Run: `cd web && npx vitest run src/api/cases.test.ts`
Expected: 4 个测试 PASS。

- [ ] **Step 6: 提交**

```bash
cd F:/ui-auto-test/ui_case_compiler
git add web/src/api/cases.ts web/src/api/runs.ts web/src/api/cases.test.ts
git commit -m "feat(web): 用例与运行端点函数

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 4: useAsync hook

**Files:**
- Create: `web/src/hooks/useAsync.ts`、`web/src/hooks/useAsync.test.ts`

**Interfaces:**
- Consumes: 无(纯 React hook)。
- Produces: `useAsync<T>()` 返回 `{ data: T | null, error: string | null, loading: boolean, run: (fn: () => Promise<T>) => Promise<void> }`。用递增 id 防竞态:只接受最后一次 run 的结果;错误取 ApiError.detail 或 message。

- [ ] **Step 1: 写失败测试**

`web/src/hooks/useAsync.test.ts`:

```typescript
import { act, renderHook, waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ApiError } from "../api/client";
import { useAsync } from "./useAsync";

describe("useAsync", () => {
  it("transitions loading -> data", async () => {
    const { result } = renderHook(() => useAsync<number>());

    await act(async () => {
      await result.current.run(async () => 42);
    });

    await waitFor(() => expect(result.current.data).toBe(42));
    expect(result.current.loading).toBe(false);
    expect(result.current.error).toBeNull();
  });

  it("captures ApiError detail", async () => {
    const { result } = renderHook(() => useAsync<number>());

    await act(async () => {
      await result.current.run(async () => {
        throw new ApiError(400, "缺少 API key");
      });
    });

    await waitFor(() => expect(result.current.error).toBe("缺少 API key"));
    expect(result.current.data).toBeNull();
  });

  it("keeps only the last result when calls race", async () => {
    const { result } = renderHook(() => useAsync<string>());

    await act(async () => {
      const slow = result.current.run(
        () => new Promise<string>((r) => setTimeout(() => r("slow"), 50)),
      );
      const fast = result.current.run(
        () => new Promise<string>((r) => setTimeout(() => r("fast"), 10)),
      );
      await Promise.all([slow, fast]);
    });

    await waitFor(() => expect(result.current.data).toBe("fast"));
  });
});
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd web && npx vitest run src/hooks/useAsync.test.ts`
Expected: FAIL(找不到 ./useAsync)。

- [ ] **Step 3: 实现 useAsync.ts**

`web/src/hooks/useAsync.ts`:

```typescript
import { useCallback, useRef, useState } from "react";
import { ApiError } from "../api/client";

interface AsyncState<T> {
  data: T | null;
  error: string | null;
  loading: boolean;
  run: (fn: () => Promise<T>) => Promise<void>;
}

export function useAsync<T>(): AsyncState<T> {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const callId = useRef(0);

  const run = useCallback(async (fn: () => Promise<T>) => {
    const id = ++callId.current;
    setLoading(true);
    setError(null);
    try {
      const result = await fn();
      if (id === callId.current) {
        setData(result);
        setLoading(false);
      }
    } catch (err) {
      if (id === callId.current) {
        const message =
          err instanceof ApiError ? err.detail : err instanceof Error ? err.message : "未知错误";
        setError(message);
        setLoading(false);
      }
    }
  }, []);

  return { data, error, loading, run };
}
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd web && npx vitest run src/hooks/useAsync.test.ts`
Expected: 3 个测试 PASS。

- [ ] **Step 5: 提交**

```bash
cd F:/ui-auto-test/ui_case_compiler
git add web/src/hooks/useAsync.ts web/src/hooks/useAsync.test.ts
git commit -m "feat(web): useAsync hook(防竞态 + ApiError 捕获)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 5: 共享组件 ErrorBanner / Spinner / StepList

**Files:**
- Create: `web/src/components/ErrorBanner.tsx`、`Spinner.tsx`、`StepList.tsx`、`web/src/components/StepList.test.tsx`

**Interfaces:**
- Consumes: Task 2 types(Step)。
- Produces:
  - `ErrorBanner({ message }: { message: string | null })`:message 为空返回 null,否则渲染 `.error-banner`。
  - `Spinner({ show }: { show: boolean })`:show 为 true 渲染"加载中…"。
  - `StepList({ steps }: { steps: Step[] })`:表格渲染每步 id/type/概要。

- [ ] **Step 1: 写失败测试**

`web/src/components/StepList.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { Step } from "../api/types";
import { StepList } from "./StepList";

describe("StepList", () => {
  it("renders a row per step with type", () => {
    const steps: Step[] = [
      { id: "step-001", type: "navigate", name: null, timeout_ms: null, url: "https://x" },
      {
        id: "step-002",
        type: "fill",
        name: null,
        timeout_ms: null,
        value: "alice",
        target: {
          primary: { strategy: "label", value: "Username", role: null, name: null },
          fallbacks: [],
          confidence: 0.9,
        },
      },
    ];

    render(<StepList steps={steps} />);

    expect(screen.getByText("step-001")).toBeInTheDocument();
    expect(screen.getByText("navigate")).toBeInTheDocument();
    expect(screen.getByText("step-002")).toBeInTheDocument();
    expect(screen.getByText("fill")).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd web && npx vitest run src/components/StepList.test.tsx`
Expected: FAIL(找不到 ./StepList)。

- [ ] **Step 3: 实现三个组件**

`web/src/components/ErrorBanner.tsx`:

```tsx
export function ErrorBanner({ message }: { message: string | null }) {
  if (!message) return null;
  return <div className="error-banner">{message}</div>;
}
```

`web/src/components/Spinner.tsx`:

```tsx
export function Spinner({ show }: { show: boolean }) {
  if (!show) return null;
  return <div className="spinner">加载中…</div>;
}
```

`web/src/components/StepList.tsx`:

```tsx
import type { Step } from "../api/types";

function summarize(step: Step): string {
  if (step.url) return step.url;
  if (step.expected !== undefined) return `expected: ${step.expected}`;
  if (step.target) {
    const p = step.target.primary;
    return p.role ? `role=${p.role} ${p.name ?? ""}` : `${p.strategy}=${p.value ?? ""}`;
  }
  return "";
}

export function StepList({ steps }: { steps: Step[] }) {
  return (
    <table>
      <thead>
        <tr>
          <th>Step</th>
          <th>Type</th>
          <th>Target/Value</th>
          <th>Value</th>
        </tr>
      </thead>
      <tbody>
        {steps.map((step) => (
          <tr key={step.id}>
            <td>{step.id}</td>
            <td>{step.type}</td>
            <td>{summarize(step)}</td>
            <td>{step.value ?? ""}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd web && npx vitest run src/components/StepList.test.tsx`
Expected: PASS。

- [ ] **Step 5: 提交**

```bash
cd F:/ui-auto-test/ui_case_compiler
git add web/src/components/ErrorBanner.tsx web/src/components/Spinner.tsx web/src/components/StepList.tsx web/src/components/StepList.test.tsx
git commit -m "feat(web): 共享组件 ErrorBanner/Spinner/StepList

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 6: CaseListPage + CreateCaseForm

**Files:**
- Create: `web/src/components/CreateCaseForm.tsx`
- Replace: `web/src/pages/CaseListPage.tsx`(Task 1 的占位)
- Create: `web/src/pages/CaseListPage.test.tsx`

**Interfaces:**
- Consumes: Task 3 listCases/compileNl/compileRecording;Task 4 useAsync;Task 5 ErrorBanner/Spinner;react-router useNavigate。
- Produces:
  - `CreateCaseForm({ onCreated }: { onCreated: (planId: string) => void })`:两 tab(NL / 录制),提交调对应 api,成功回调 onCreated(plan.id)。NL tab url 必填(空则不提交,显示提示)。
  - `CaseListPage()`:挂载 listCases,渲染用例表格(点击行导航 /cases/{id}),含 CreateCaseForm。

- [ ] **Step 1: 写失败测试**

`web/src/pages/CaseListPage.test.tsx`:

```tsx
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import * as casesApi from "../api/cases";
import { CaseListPage } from "./CaseListPage";

afterEach(() => vi.restoreAllMocks());

function renderPage() {
  return render(
    <MemoryRouter>
      <CaseListPage />
    </MemoryRouter>,
  );
}

describe("CaseListPage", () => {
  it("lists cases from the api", async () => {
    vi.spyOn(casesApi, "listCases").mockResolvedValue([
      { id: "p1", name: "Login", source: "manual", step_count: 5 },
    ]);
    renderPage();
    await waitFor(() => expect(screen.getByText("Login")).toBeInTheDocument());
    expect(screen.getByText("p1")).toBeInTheDocument();
  });

  it("compiles a recording on submit", async () => {
    vi.spyOn(casesApi, "listCases").mockResolvedValue([]);
    const compile = vi
      .spyOn(casesApi, "compileRecording")
      .mockResolvedValue({
        id: "rec-1",
        name: "Rec",
        source: "recording",
        base_url: null,
        parameters: {},
        environment: null,
        steps: [],
      });
    renderPage();

    await userEvent.click(screen.getByRole("button", { name: "录制 JSON" }));
    await userEvent.type(
      screen.getByLabelText("事件 JSON"),
      '[{"type":"navigation","timestamp":0,"url":"https://x"}]',
    );
    await userEvent.click(screen.getByRole("button", { name: "从录制创建" }));

    await waitFor(() => expect(compile).toHaveBeenCalled());
  });

  it("shows error when NL url is empty", async () => {
    vi.spyOn(casesApi, "listCases").mockResolvedValue([]);
    renderPage();

    await userEvent.type(screen.getByLabelText("自然语言用例"), "click login");
    await userEvent.click(screen.getByRole("button", { name: "从自然语言创建" }));

    await waitFor(() => expect(screen.getByText(/URL 必填/)).toBeInTheDocument());
  });
});
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd web && npx vitest run src/pages/CaseListPage.test.tsx`
Expected: FAIL(占位组件无表格/表单)。

- [ ] **Step 3: 实现 CreateCaseForm**

`web/src/components/CreateCaseForm.tsx`:

```tsx
import { useState } from "react";
import { compileNl, compileRecording } from "../api/cases";
import { useAsync } from "../hooks/useAsync";
import type { ExecutablePlan } from "../api/types";
import { ErrorBanner } from "./ErrorBanner";

export function CreateCaseForm({ onCreated }: { onCreated: (planId: string) => void }) {
  const [tab, setTab] = useState<"nl" | "recording">("nl");
  const [text, setText] = useState("");
  const [url, setUrl] = useState("");
  const [name, setName] = useState("");
  const [eventsJson, setEventsJson] = useState("");
  const [localError, setLocalError] = useState<string | null>(null);
  const { error, loading, run } = useAsync<ExecutablePlan>();

  async function submitNl() {
    setLocalError(null);
    if (!url.trim()) {
      setLocalError("URL 必填");
      return;
    }
    await run(async () => {
      const plan = await compileNl({ text, context: { url }, name: name || undefined });
      onCreated(plan.id);
      return plan;
    });
  }

  async function submitRecording() {
    setLocalError(null);
    let events: Record<string, unknown>[];
    try {
      events = JSON.parse(eventsJson);
    } catch {
      setLocalError("事件 JSON 解析失败");
      return;
    }
    await run(async () => {
      const plan = await compileRecording({ events, name: name || "Recorded Flow" });
      onCreated(plan.id);
      return plan;
    });
  }

  return (
    <section>
      <h2>创建用例</h2>
      <div>
        <button className={tab === "nl" ? "tab-active" : ""} onClick={() => setTab("nl")}>
          自然语言
        </button>
        <button
          className={tab === "recording" ? "tab-active" : ""}
          onClick={() => setTab("recording")}
        >
          录制 JSON
        </button>
      </div>
      <ErrorBanner message={localError ?? error} />
      <div>
        <label>
          名称
          <input value={name} onChange={(e) => setName(e.target.value)} />
        </label>
      </div>
      {tab === "nl" ? (
        <div>
          <label>
            自然语言用例
            <textarea value={text} onChange={(e) => setText(e.target.value)} rows={3} />
          </label>
          <label>
            URL
            <input value={url} onChange={(e) => setUrl(e.target.value)} />
          </label>
          <button onClick={submitNl} disabled={loading}>
            从自然语言创建
          </button>
        </div>
      ) : (
        <div>
          <label>
            事件 JSON
            <textarea
              value={eventsJson}
              onChange={(e) => setEventsJson(e.target.value)}
              rows={4}
            />
          </label>
          <button onClick={submitRecording} disabled={loading}>
            从录制创建
          </button>
        </div>
      )}
    </section>
  );
}
```

- [ ] **Step 4: 实现 CaseListPage**

`web/src/pages/CaseListPage.tsx`(替换占位):

```tsx
import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { listCases } from "../api/cases";
import { CreateCaseForm } from "../components/CreateCaseForm";
import { ErrorBanner } from "../components/ErrorBanner";
import { Spinner } from "../components/Spinner";
import { useAsync } from "../hooks/useAsync";
import type { CaseSummary } from "../api/types";

export function CaseListPage() {
  const navigate = useNavigate();
  const { data, error, loading, run } = useAsync<CaseSummary[]>();

  useEffect(() => {
    void run(listCases);
  }, [run]);

  return (
    <div>
      <CreateCaseForm onCreated={(id) => navigate(`/cases/${id}`)} />
      <h2>用例列表</h2>
      <ErrorBanner message={error} />
      <Spinner show={loading} />
      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>名称</th>
            <th>来源</th>
            <th>步骤数</th>
          </tr>
        </thead>
        <tbody>
          {(data ?? []).map((c) => (
            <tr
              key={c.id}
              onClick={() => navigate(`/cases/${c.id}`)}
              style={{ cursor: "pointer" }}
            >
              <td>{c.id}</td>
              <td>{c.name}</td>
              <td>{c.source}</td>
              <td>{c.step_count}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
```

- [ ] **Step 5: 运行测试确认通过**

Run: `cd web && npx vitest run src/pages/CaseListPage.test.tsx`
Expected: 3 个测试 PASS。

- [ ] **Step 6: 提交**

```bash
cd F:/ui-auto-test/ui_case_compiler
git add web/src/components/CreateCaseForm.tsx web/src/pages/CaseListPage.tsx web/src/pages/CaseListPage.test.tsx
git commit -m "feat(web): 用例列表页 + 创建表单(NL/录制)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 7: CaseDetailPage

**Files:**
- Replace: `web/src/pages/CaseDetailPage.tsx`(Task 1 的占位)
- Create: `web/src/pages/CaseDetailPage.test.tsx`

**Interfaces:**
- Consumes: Task 3 getCase/validateCase/runCase/dryRun;Task 4 useAsync;Task 5 StepList/ErrorBanner/Spinner;react-router useParams/useNavigate。
- Produces: `CaseDetailPage()`:读 :caseId,getCase 展示元信息 + StepList;按钮 Validate/Dry-run/Run;参数输入(一个 textarea,每行 key=value);Run/Dry-run 成功导航 /runs/{run_id};Validate 显示结果文本。

- [ ] **Step 1: 写失败测试**

`web/src/pages/CaseDetailPage.test.tsx`:

```tsx
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import * as casesApi from "../api/cases";
import { CaseDetailPage } from "./CaseDetailPage";

afterEach(() => vi.restoreAllMocks());

const plan = {
  id: "p1",
  name: "Login",
  source: "manual",
  base_url: null,
  parameters: {},
  environment: null,
  steps: [{ id: "step-001", type: "navigate", name: null, timeout_ms: null, url: "https://x" }],
};

function renderAt() {
  return render(
    <MemoryRouter initialEntries={["/cases/p1"]}>
      <Routes>
        <Route path="/cases/:caseId" element={<CaseDetailPage />} />
        <Route path="/runs/:runId" element={<div>RUN PAGE</div>} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("CaseDetailPage", () => {
  it("renders plan meta and steps", async () => {
    vi.spyOn(casesApi, "getCase").mockResolvedValue(plan);
    renderAt();
    await waitFor(() => expect(screen.getByText("Login")).toBeInTheDocument());
    expect(screen.getByText("step-001")).toBeInTheDocument();
  });

  it("validates the case", async () => {
    vi.spyOn(casesApi, "getCase").mockResolvedValue(plan);
    vi.spyOn(casesApi, "validateCase").mockResolvedValue({
      valid: true,
      plan_id: "p1",
      step_count: 1,
    });
    renderAt();
    await waitFor(() => expect(screen.getByText("Login")).toBeInTheDocument());
    await userEvent.click(screen.getByRole("button", { name: "Validate" }));
    await waitFor(() => expect(screen.getByText(/valid/i)).toBeInTheDocument());
  });

  it("runs and navigates to run detail", async () => {
    vi.spyOn(casesApi, "getCase").mockResolvedValue(plan);
    vi.spyOn(casesApi, "runCase").mockResolvedValue({
      run_id: "r1",
      plan_id: "p1",
      status: "passed",
      started_at: "2026-07-05T00:00:00Z",
      ended_at: "2026-07-05T00:00:01Z",
      steps: [],
      trace_path: null,
      video_paths: [],
      report_path: null,
    });
    renderAt();
    await waitFor(() => expect(screen.getByText("Login")).toBeInTheDocument());
    await userEvent.click(screen.getByRole("button", { name: "Run" }));
    await waitFor(() => expect(screen.getByText("RUN PAGE")).toBeInTheDocument());
  });
});
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd web && npx vitest run src/pages/CaseDetailPage.test.tsx`
Expected: FAIL(占位组件)。

- [ ] **Step 3: 实现 CaseDetailPage**

`web/src/pages/CaseDetailPage.tsx`(替换占位):

```tsx
import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { dryRun, getCase, runCase, validateCase } from "../api/cases";
import { ErrorBanner } from "../components/ErrorBanner";
import { Spinner } from "../components/Spinner";
import { StepList } from "../components/StepList";
import { useAsync } from "../hooks/useAsync";
import type { ExecutablePlan, RunResult, ValidateResponse } from "../api/types";

function parseParams(text: string): Record<string, string> {
  const params: Record<string, string> = {};
  for (const line of text.split("\n")) {
    const trimmed = line.trim();
    if (!trimmed || !trimmed.includes("=")) continue;
    const [key, ...rest] = trimmed.split("=");
    params[key.trim()] = rest.join("=").trim();
  }
  return params;
}

export function CaseDetailPage() {
  const { caseId } = useParams<{ caseId: string }>();
  const navigate = useNavigate();
  const plan = useAsync<ExecutablePlan>();
  const action = useAsync<RunResult | ValidateResponse>();
  const [paramsText, setParamsText] = useState("");
  const [validateMsg, setValidateMsg] = useState<string | null>(null);

  useEffect(() => {
    if (caseId) void plan.run(() => getCase(caseId));
  }, [caseId, plan.run]);

  if (!caseId) return null;

  const runReq = { params: parseParams(paramsText), headed: false };

  async function doValidate() {
    setValidateMsg(null);
    await action.run(async () => {
      const resp = await validateCase(caseId);
      setValidateMsg(resp.valid ? `valid (${resp.step_count} steps)` : "invalid");
      return resp;
    });
  }

  async function doRun(kind: "run" | "dry") {
    await action.run(async () => {
      const result = kind === "run" ? await runCase(caseId, runReq) : await dryRun(caseId, runReq);
      navigate(`/runs/${result.run_id}`);
      return result;
    });
  }

  const p = plan.data;

  return (
    <div>
      <ErrorBanner message={plan.error ?? action.error} />
      <Spinner show={plan.loading} />
      {p && (
        <>
          <h2>{p.name}</h2>
          <p>
            ID: <code>{p.id}</code> · 来源: {p.source} · base_url: {p.base_url ?? "—"}
          </p>
          <StepList steps={p.steps} />
          <h3>运行参数(每行 key=value)</h3>
          <textarea
            aria-label="运行参数"
            value={paramsText}
            onChange={(e) => setParamsText(e.target.value)}
            rows={3}
          />
          <div>
            <button onClick={doValidate} disabled={action.loading}>
              Validate
            </button>
            <button onClick={() => doRun("dry")} disabled={action.loading}>
              Dry-run
            </button>
            <button onClick={() => doRun("run")} disabled={action.loading}>
              Run
            </button>
          </div>
          {validateMsg && <p>{validateMsg}</p>}
        </>
      )}
    </div>
  );
}
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd web && npx vitest run src/pages/CaseDetailPage.test.tsx`
Expected: 3 个测试 PASS。

- [ ] **Step 5: 提交**

```bash
cd F:/ui-auto-test/ui_case_compiler
git add web/src/pages/CaseDetailPage.tsx web/src/pages/CaseDetailPage.test.tsx
git commit -m "feat(web): 用例详情页(步骤展示 + validate/dry-run/run)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 8: RunDetailPage + 全量构建冒烟

**Files:**
- Replace: `web/src/pages/RunDetailPage.tsx`(Task 1 的占位)
- Create: `web/src/pages/RunDetailPage.test.tsx`

**Interfaces:**
- Consumes: Task 3 getRun;Task 4 useAsync;Task 5 ErrorBanner/Spinner;react-router useParams。
- Produces: `RunDetailPage()`:读 :runId,getRun 展示 run 元信息 + 步骤结果表 + 报告/trace 路径文本(不做链接)。

- [ ] **Step 1: 写失败测试**

`web/src/pages/RunDetailPage.test.tsx`:

```tsx
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import * as runsApi from "../api/runs";
import { RunDetailPage } from "./RunDetailPage";

afterEach(() => vi.restoreAllMocks());

function renderAt() {
  return render(
    <MemoryRouter initialEntries={["/runs/r1"]}>
      <Routes>
        <Route path="/runs/:runId" element={<RunDetailPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("RunDetailPage", () => {
  it("renders run status, steps and report path text", async () => {
    vi.spyOn(runsApi, "getRun").mockResolvedValue({
      run_id: "r1",
      plan_id: "p1",
      status: "passed",
      started_at: "2026-07-05T00:00:00Z",
      ended_at: "2026-07-05T00:00:01Z",
      steps: [
        {
          step_id: "step-001",
          step_type: "navigate",
          status: "passed",
          duration_ms: 64,
          error: null,
          screenshot: null,
        },
      ],
      trace_path: ".ui-case-compiler/artifacts/r1/trace.zip",
      video_paths: [],
      report_path: ".ui-case-compiler/reports/r1.html",
    });

    renderAt();

    await waitFor(() => expect(screen.getByText("r1")).toBeInTheDocument());
    expect(screen.getByText("step-001")).toBeInTheDocument();
    expect(screen.getByText(".ui-case-compiler/reports/r1.html")).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd web && npx vitest run src/pages/RunDetailPage.test.tsx`
Expected: FAIL(占位组件)。

- [ ] **Step 3: 实现 RunDetailPage**

`web/src/pages/RunDetailPage.tsx`(替换占位):

```tsx
import { useEffect } from "react";
import { useParams } from "react-router-dom";
import { getRun } from "../api/runs";
import { ErrorBanner } from "../components/ErrorBanner";
import { Spinner } from "../components/Spinner";
import { useAsync } from "../hooks/useAsync";
import type { RunResult } from "../api/types";

export function RunDetailPage() {
  const { runId } = useParams<{ runId: string }>();
  const { data, error, loading, run } = useAsync<RunResult>();

  useEffect(() => {
    if (runId) void run(() => getRun(runId));
  }, [runId, run]);

  return (
    <div>
      <ErrorBanner message={error} />
      <Spinner show={loading} />
      {data && (
        <>
          <h2>运行 {data.run_id}</h2>
          <p>
            计划: <code>{data.plan_id}</code> · 状态:{" "}
            <span className={data.status}>{data.status}</span>
          </p>
          <p>
            开始: {data.started_at} · 结束: {data.ended_at}
          </p>
          <table>
            <thead>
              <tr>
                <th>Step</th>
                <th>Type</th>
                <th>Status</th>
                <th>耗时</th>
                <th>Error</th>
              </tr>
            </thead>
            <tbody>
              {data.steps.map((s) => (
                <tr key={s.step_id}>
                  <td>{s.step_id}</td>
                  <td>{s.step_type}</td>
                  <td className={s.status}>{s.status}</td>
                  <td>{s.duration_ms} ms</td>
                  <td>{s.error ?? ""}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <h3>产物(服务端路径)</h3>
          <p>报告: {data.report_path ?? "—"}</p>
          <p>Trace: {data.trace_path ?? "—"}</p>
        </>
      )}
    </div>
  );
}
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd web && npx vitest run src/pages/RunDetailPage.test.tsx`
Expected: PASS。

- [ ] **Step 5: 全量测试 + 构建冒烟**

Run: `cd web && npx vitest run && npm run build`
Expected: 所有测试 PASS(client 3 + cases 4 + useAsync 3 + StepList 1 + CaseList 3 + CaseDetail 3 + RunDetail 1 = 18);tsc 类型检查通过 + vite build 成功生成 dist/。

- [ ] **Step 6: 提交**

```bash
cd F:/ui-auto-test/ui_case_compiler
git add web/src/pages/RunDetailPage.tsx web/src/pages/RunDetailPage.test.tsx
git commit -m "feat(web): 运行详情页(状态/步骤/产物路径)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## 端到端手动验证(需用户,双进程)

```powershell
# 终端 1:起后端
cd F:\ui-auto-test\ui_case_compiler
ui-case serve

# 终端 2:起前端
cd F:\ui-auto-test\ui_case_compiler\web
npm run dev
# 浏览器打开 Vite 提示的地址(通常 http://localhost:5173)
# 验证:用例列表加载、录制 JSON 创建用例、详情页 Run、跳转运行详情看结果
```

Expected: 列表/创建/详情/运行四个交互在真实前后端间跑通。缺 DEEPSEEK_API_KEY 时 NL 创建返回 400 并在 ErrorBanner 显示(符合设计)。

---

## Self-Review

**Spec coverage:**
- web/ 独立 Vite 项目 + 依赖稳定版 → Task 1 ✓
- dev proxy /api→8000 → Task 1 vite.config ✓
- apiFetch + ApiError → Task 2 ✓
- TS 类型镜像后端 → Task 2 types.ts ✓
- 端点函数(9 类)→ Task 3(cases 8 + runs 2)✓
- useAsync 防竞态 + ApiError 捕获 → Task 4 ✓
- 共享组件 → Task 5 ✓
- CaseList + 创建(NL/录制两 tab,url 必填)→ Task 6 ✓
- CaseDetail(步骤 + validate/dry-run/run + 参数)→ Task 7 ✓
- RunDetail(状态/步骤/报告路径文本不做链接)→ Task 8 ✓
- 测试 vitest+RTL mock api 不打网络 → 各任务 ✓
- 构建冒烟 → Task 8 ✓
- 端到端需用户起后端 → 文档末尾 ✓
- 不做步骤编辑器/鉴权/实时录制/报告静态服务 → 均未纳入 ✓

**Placeholder scan:** 无 TBD/TODO;每个 code step 含完整代码;命令含预期输出。Task 1 的页面占位是刻意的脚手架步骤(让路由可编译),Task 6/7/8 明确"替换占位",非计划占位符。✓

**Type consistency:**
- ApiError(status, detail) Task 2 定义,useAsync(T4)/测试引用一致 ✓
- apiFetch<T>(path, options) Task 2,Task 3 端点函数调用一致 ✓
- 端点函数名 listCases/compileNl/compileRecording/getCase/updateCase/validateCase/dryRun/runCase/listRuns/getRun Task 3 定义,Task 6/7/8 页面引用一致 ✓
- useAsync 返回 {data,error,loading,run} Task 4,Task 6/7/8 解构一致 ✓
- Step/ExecutablePlan/RunResult/CaseSummary/RunSummary 字段与后端契约一致(step_count/run_id/plan_id/started_at 蛇形,与 FastAPI 输出一致)✓
- CreateCaseForm onCreated(planId) Task 6,CaseListPage 传入一致 ✓

**一处风险标注:** 后端 JSON 字段是蛇形命名(step_count/run_id/started_at 等),前端 TS 类型直接用蛇形对齐,不做驼峰转换——避免序列化不一致。已在 types.ts 和契约中统一。
