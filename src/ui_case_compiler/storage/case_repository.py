from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel

from ui_case_compiler.schema.executable_plan import ExecutablePlan
from ui_case_compiler.storage.file_store import FileStore

CaseStatus = Literal["draft", "ready"]


class CaseSummary(BaseModel):
    id: str
    name: str
    source: str
    step_count: int


class CaseRepository:
    """Persist executable plans and simple case state."""

    def __init__(self, store: FileStore) -> None:
        self._store = store

    def save_plan(self, plan: ExecutablePlan) -> Path:
        path = self._store.root / "plans" / f"{plan.id}.json"
        self._store.write_json(path, plan.model_dump(mode="json"))
        return path

    def load_plan(self, plan_id: str) -> ExecutablePlan:
        path = self._store.root / "plans" / f"{plan_id}.json"
        return ExecutablePlan.model_validate(self._store.read_json(path))

    def mark_status(self, plan_id: str, status: CaseStatus) -> Path:
        path = self._store.root / "cases" / f"{plan_id}.json"
        self._store.write_json(path, {"plan_id": plan_id, "status": status})
        return path

    def list_summaries(self) -> list[CaseSummary]:
        plans_dir = self._store.root / "plans"
        if not plans_dir.exists():
            return []
        summaries: list[CaseSummary] = []
        for path in sorted(plans_dir.glob("*.json")):
            plan = ExecutablePlan.model_validate(self._store.read_json(path))
            summaries.append(
                CaseSummary(
                    id=plan.id,
                    name=plan.name,
                    source=plan.source,
                    step_count=len(plan.steps),
                )
            )
        return summaries

