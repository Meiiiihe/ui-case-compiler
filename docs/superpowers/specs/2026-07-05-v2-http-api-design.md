# v2 子项目③：HTTP API 层设计

**状态:** 待用户审阅
**日期:** 2026-07-05
**范围:** UI Case Compiler v2 的第三个子项目——用 FastAPI 包一层 HTTP API，复用现有 Python 核心，为子项目④ Web UI 提供后端。

## 背景

前两个子项目让核心能力可用：① 真实模型编译自然语言，② 真实录制。但它们只能通过 CLI 调用。子项目④ 的 React Web UI 需要一个 HTTP API 来驱动编译、执行、查询。本子项目就是这个 API 层。

v2 四个有序子项目：

```
① 真实模型 Provider（已完成，已合并）
② 真实录制（已完成，已合并）
③ HTTP API 层（本 spec）      ← FastAPI 复用 Python 核心
④ React Web UI
```

API 草图源自 module-design.md 第 12.5 节，本 spec 据澄清结论细化。

## storage 现状与能力缺口

现有 repository 只支持按 id 精确读写单条：

- `CaseRepository`：`save_plan` / `load_plan(plan_id)` / `mark_status`——无"列出所有 cases"。
- `RunRepository`：`save_result` / `load_result(run_id)`——无"列出所有 runs"。

`GET /api/cases` 和 `GET /api/runs` 需要列表能力，因此本子项目给两个 repository 各加 `list_summaries()` 方法（职责内聚在 storage 层）。

`ExecutablePlan` 和 `RunResult` 都是完整 Pydantic 模型，可直接作为 API 响应，无需重复定义。

## 已确定的关键决策

| 决策点 | 结论 |
|--------|------|
| API 范围 | 全盘 9 类端点（GET /cases、compile-nl、compile-recording、GET/PUT case、validate、dry-run、run、GET /runs、GET /run）。 |
| 执行模型 | run / dry-run 同步阻塞（请求等到执行完返回 RunResult）。实时录制不进 API（保留 CLI）；API 的 compile-recording 只接离线事件 JSON 上传。 |
| list 实现 | CaseRepository / RunRepository 各加 `list_summaries()` 扫目录，职责在 storage 层。 |
| 鉴权/CORS | 本地无鉴权，默认绑 127.0.0.1，CORS 允许本地前端源。符合 module-design「不做多用户/权限」。 |
| 安全边界 | 服务默认只绑 127.0.0.1；host 可配但文档警示绑 0.0.0.0 会把无鉴权 API 暴露到网络。 |
| 技术栈 | FastAPI + uvicorn，方案 A（分层：app / routes / service / models / dependencies）。 |

## 方案选择

采用**方案 A**：分层 FastAPI 应用，薄路由 + service 编排层 + API 模型层。路由只做 HTTP 翻译，业务编排集中在 service，持久化复用现有 repository。备选方案 B（单文件）9 端点堆一起难测试、耦合；方案 C（每资源一 router）对 9 端点 MVP 过早分层。均弃用。

## 架构与文件结构

### 新增文件

```
src/ui_case_compiler/api/
  __init__.py
  app.py           create_app() 工厂：FastAPI 实例 + CORS + 路由注册 + 异常处理器
  routes.py        9 个端点，薄路由：请求 → 调 service → 返回响应模型
  service.py       ApiService：业务编排，复用现有 compiler/recorder/runner/storage/reporter
  models.py        API 特有的请求/响应模型
  dependencies.py  FastAPI Depends：提供 config、ApiService
```

### 修改文件

- `storage/case_repository.py`：加 `list_summaries()`。
- `storage/run_repository.py`：加 `list_summaries()`。
- `cli/main.py`：加 `serve` 命令（uvicorn 启动）。
- `config.py`：加 `ApiConfig`，挂到 `RuntimeConfig.api`。
- `pyproject.toml`：加 `fastapi>=0.110`、`uvicorn>=0.29`。

### 完全不改

schema、runner、reporter、compiler、recorder 的核心逻辑；所有现有 CLI 命令。

### 端点 → service → 核心

| 端点 | service 编排 |
|------|------|
| `GET /api/cases` | CaseRepository.list_summaries |
| `POST /api/cases/compile-nl` | DeepSeekProvider + NaturalLanguageCompiler → save_plan |
| `POST /api/cases/compile-recording` | EventCollector + RecordingCompiler → save_plan（离线 JSON 上传）|
| `GET /api/cases/{id}` | CaseRepository.load_plan |
| `PUT /api/cases/{id}` | validate + save_plan（覆盖）|
| `POST /api/cases/{id}/validate` | load_plan + validate_plan |
| `POST /api/cases/{id}/dry-run` | DryRunService（同步）|
| `POST /api/cases/{id}/run` | PlanRunner.run（同步）+ 保存 RunResult |
| `GET /api/runs` / `GET /api/runs/{id}` | RunRepository.list_summaries / load_result |

## 请求/响应模型（api/models.py）

只定义 API 特有模型；单个计划/运行结果直接用 ExecutablePlan / RunResult 作 response_model。

```python
class CompileNlRequest(BaseModel):
    text: str
    context: PageContext          # 复用现有 PageContext
    name: str | None = None

class CompileRecordingRequest(BaseModel):
    events: list[dict]            # 离线事件流，交 EventCollector 校验
    name: str = "Recorded Flow"

class RunRequest(BaseModel):
    params: dict[str, str] = {}   # 运行时参数（对应 CLI --param）
    headed: bool = False

class ValidateResponse(BaseModel):
    valid: bool
    plan_id: str
    step_count: int

class ErrorResponse(BaseModel):
    detail: str
```

列表摘要模型 `CaseSummary` / `RunSummary` 定义在 **storage 层**（api 复用），避免 storage 反向依赖 api：

```python
# storage 层
class CaseSummary(BaseModel):
    id: str
    name: str
    source: str
    step_count: int

class RunSummary(BaseModel):
    run_id: str
    plan_id: str
    status: str
    started_at: datetime
```

## service.py 编排

```python
class ApiService:
    def __init__(self, config: RuntimeConfig) -> None:
        self._config = config
        store = FileStore(config.output_dir)
        self._cases = CaseRepository(store)
        self._runs = RunRepository(store)

    def list_cases(self) -> list[CaseSummary]: ...
    async def compile_nl(self, req: CompileNlRequest) -> ExecutablePlan:
        if not self._config.llm.api_key:
            raise CompilationError("未配置模型 API key")
        provider = DeepSeekProvider(self._config.llm)
        plan = await NaturalLanguageCompiler(provider=provider).compile(req.text, req.context)
        self._cases.save_plan(plan)
        return plan
    def compile_recording(self, req: CompileRecordingRequest) -> ExecutablePlan:
        events = EventCollector().collect(req.events)
        plan = RecordingCompiler().compile(events, req.name)
        self._cases.save_plan(plan)
        return plan
    def get_case(self, case_id: str) -> ExecutablePlan: ...       # 不存在 → 404 语义
    def update_case(self, case_id: str, plan: ExecutablePlan) -> ExecutablePlan: ...
        # 若 body plan.id 与 path case_id 不一致 → 抛 PlanValidationError（422）
    def validate_case(self, case_id: str) -> ValidateResponse: ...
    async def dry_run(self, case_id: str, req: RunRequest) -> RunResult: ...
    async def run(self, case_id: str, req: RunRequest) -> RunResult: ...  # + save_result
    def list_runs(self) -> list[RunSummary]: ...
    def get_run(self, run_id: str) -> RunResult: ...              # 不存在 → 404 语义
```

要点：
- service 层无任何 HTTP 概念，纯业务编排，可脱离 FastAPI 单元测试。
- 编译/运行错误抛现有异常家族（CompilationError / PlanValidationError / StorageError），由 app.py 异常处理器统一转 HTTP。
- run / dry-run 是 async（现有 PlanRunner.run 即 async），端点 await 它，天然同步阻塞语义。
- **service 的 get/load 方法显式处理"文件不存在 → 404 语义"**，不靠解析 StorageError 消息。

## storage 新增

```python
# CaseRepository
def list_summaries(self) -> list[CaseSummary]:
    # 扫 plans/*.json，读每个提取 id/name/source/step_count
# RunRepository
def list_summaries(self) -> list[RunSummary]:
    # 扫 runs/*.json，提取 run_id/plan_id/status/started_at
```

## app.py 异常映射与 CORS

```python
def create_app(config: RuntimeConfig | None = None) -> FastAPI:
    config = config or load_config()
    app = FastAPI(title="UI Case Compiler API")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.api.cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.state.service = ApiService(config)
    app.include_router(router)
    _register_exception_handlers(app)
    return app
```

异常 → HTTP 状态码：

| 异常 | HTTP | 场景 |
|------|------|------|
| `PlanValidationError` | 422 | 计划/DSL 校验失败 |
| `CompilationError` | 400 | 编译失败、缺 api_key、模型返回非法 |
| `RecordingError` | 400 | 离线事件非法 |
| not-found（service 抛出的明确语义） | 404 | case/run 不存在 |
| `StorageError`（其他） | 500 | 读写失败 |
| 其他 `UiCaseCompilerError` | 500 | 兜底 |

处理器统一返回 `{"detail": "<message>"}`（ErrorResponse 结构）。

## config 扩展

```python
class ApiConfig(BaseModel):
    host: str = "127.0.0.1"        # 环境变量 API_HOST，默认只绑本地
    port: int = 8000               # API_PORT
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]
# 挂到 RuntimeConfig.api: ApiConfig
```

## CLI serve 命令

```python
@app.command("serve")
def serve_command(host: str | None = None, port: int | None = None) -> None:
    config = load_config()
    uvicorn.run(
        create_app(config),
        host=host or config.api.host,
        port=port or config.api.port,
    )
```

文档警示：绑 0.0.0.0 会把无鉴权 API 暴露到网络，仅在受信网络下这么做。

## 错误处理

见异常映射表。核心原则：service 抛现有异常家族 + not-found 语义，app.py 集中转 HTTP 状态码，响应体统一 `{"detail": ...}`。执行失败（run 里某步 failed）不是 HTTP 错误——返回 200 + status=failed 的 RunResult。

## 测试策略

1. **service 单元测试**（不起 HTTP）：构造 `ApiService` + 临时 output_dir，测 list/get/compile-recording/validate 纯逻辑；compile_nl patch 掉 DeepSeekProvider；run/dry-run 对本地 login.html 真实跑（复用现有 PlanRunner 集成模式）。
2. **API 端点测试**（FastAPI TestClient，不起真实服务器）：GET /cases、GET /runs 列表；compile-recording 上传离线事件 → 200；compile-nl patch provider → 200；GET case 存在→200/不存在→404；validate 合法→valid/非法→422；run 对本地页→200 + RunResult；缺 api_key 的 compile-nl→400；CORS 头存在性。
3. **storage list_summaries 单元测试**：写几个 plan/run 文件，断言列表正确。
4. 全程 ruff + mypy strict 绿。

依赖：`fastapi>=0.110`、`uvicorn>=0.29`；TestClient 需要 httpx（openai 已引入）。

## 非目标（本子项目不做）

- 不做鉴权/多用户/权限（module-design 非目标）。
- 不做后台任务队列（run 同步阻塞）。
- 实时录制不进 API（保留 CLI）。
- 不改动 schema/runner/reporter/compiler/recorder 核心逻辑与现有 CLI 命令。
- 不做 React 前端（子项目④）。
- 默认不绑 0.0.0.0。
