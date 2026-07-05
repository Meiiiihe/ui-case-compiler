from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from ui_case_compiler.api.routes import router
from ui_case_compiler.api.service import ApiService, NotFoundError
from ui_case_compiler.config import RuntimeConfig, load_config
from ui_case_compiler.errors import (
    CompilationError,
    PlanValidationError,
    RecordingError,
    StorageError,
    UiCaseCompilerError,
)


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


def _register_exception_handlers(app: FastAPI) -> None:
    def _json(status: int, detail: str) -> JSONResponse:
        return JSONResponse(status_code=status, content={"detail": detail})

    @app.exception_handler(NotFoundError)
    async def _not_found(request: Request, exc: NotFoundError) -> JSONResponse:
        return _json(404, str(exc))

    @app.exception_handler(PlanValidationError)
    async def _validation(request: Request, exc: PlanValidationError) -> JSONResponse:
        return _json(422, str(exc))

    @app.exception_handler(CompilationError)
    async def _compilation(request: Request, exc: CompilationError) -> JSONResponse:
        return _json(400, str(exc))

    @app.exception_handler(RecordingError)
    async def _recording(request: Request, exc: RecordingError) -> JSONResponse:
        return _json(400, str(exc))

    @app.exception_handler(StorageError)
    async def _storage(request: Request, exc: StorageError) -> JSONResponse:
        return _json(500, str(exc))

    @app.exception_handler(UiCaseCompilerError)
    async def _base(request: Request, exc: UiCaseCompilerError) -> JSONResponse:
        return _json(500, str(exc))
