from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from ui_case_compiler.errors import PlanValidationError
from ui_case_compiler.schema.executable_plan import ExecutablePlan


def validate_plan(data: Mapping[str, Any]) -> ExecutablePlan:
    """Validate raw plan data and return an executable plan."""

    try:
        return ExecutablePlan.model_validate(data)
    except ValidationError as exc:
        msg = "Executable plan validation failed"
        raise PlanValidationError(msg) from exc


def load_plan(path: Path) -> ExecutablePlan:
    """Load and validate an executable plan from JSON."""

    try:
        return ExecutablePlan.model_validate_json(path.read_text(encoding="utf-8"))
    except ValidationError as exc:
        msg = f"Executable plan validation failed: {path}"
        raise PlanValidationError(msg) from exc


def dump_plan(plan: ExecutablePlan, path: Path) -> None:
    """Persist an executable plan as formatted JSON."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(plan.model_dump_json(indent=2), encoding="utf-8")
