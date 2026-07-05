from __future__ import annotations

from datetime import datetime
from pathlib import Path

from pydantic import BaseModel

from ui_case_compiler.reporter.run_result import RunResult
from ui_case_compiler.storage.file_store import FileStore


class RunSummary(BaseModel):
    run_id: str
    plan_id: str
    status: str
    started_at: datetime


class RunRepository:
    """Persist run results."""

    def __init__(self, store: FileStore) -> None:
        self._store = store

    def save_result(self, result: RunResult) -> Path:
        path = self._store.root / "runs" / f"{result.run_id}.json"
        self._store.write_json(path, result.model_dump(mode="json"))
        return path

    def load_result(self, run_id: str) -> RunResult:
        path = self._store.root / "runs" / f"{run_id}.json"
        return RunResult.model_validate(self._store.read_json(path))

    def list_summaries(self) -> list[RunSummary]:
        runs_dir = self._store.root / "runs"
        if not runs_dir.exists():
            return []
        summaries: list[RunSummary] = []
        for path in sorted(runs_dir.glob("*.json")):
            result = RunResult.model_validate(self._store.read_json(path))
            summaries.append(
                RunSummary(
                    run_id=result.run_id,
                    plan_id=result.plan_id,
                    status=result.status,
                    started_at=result.started_at,
                )
            )
        return summaries

