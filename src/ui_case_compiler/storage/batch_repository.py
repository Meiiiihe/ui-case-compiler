from __future__ import annotations

from datetime import datetime
from pathlib import Path

from pydantic import BaseModel

from ui_case_compiler.reporter.batch_result import BatchRunResult
from ui_case_compiler.storage.file_store import FileStore


class BatchRunSummary(BaseModel):
    batch_id: str
    plan_id: str
    status: str
    total: int
    passed: int
    failed: int
    started_at: datetime


class BatchRunRepository:
    """Persist data-driven batch run results."""

    def __init__(self, store: FileStore) -> None:
        self._store = store

    def save_result(self, result: BatchRunResult) -> Path:
        path = self._store.root / "batches" / f"{result.batch_id}.json"
        self._store.write_json(path, result.model_dump(mode="json"))
        return path

    def load_result(self, batch_id: str) -> BatchRunResult:
        path = self._store.root / "batches" / f"{batch_id}.json"
        return BatchRunResult.model_validate(self._store.read_json(path))

    def list_summaries(self) -> list[BatchRunSummary]:
        batches_dir = self._store.root / "batches"
        if not batches_dir.exists():
            return []
        summaries: list[BatchRunSummary] = []
        for path in sorted(batches_dir.glob("*.json")):
            result = BatchRunResult.model_validate(self._store.read_json(path))
            summaries.append(
                BatchRunSummary(
                    batch_id=result.batch_id,
                    plan_id=result.plan_id,
                    status=result.status,
                    total=result.total,
                    passed=result.passed,
                    failed=result.failed,
                    started_at=result.started_at,
                )
            )
        return summaries
