from __future__ import annotations

import importlib.util
import json
import sys
from collections.abc import Callable
from pathlib import Path
from types import ModuleType
from typing import Any, cast

from ui_case_compiler.schema.executable_plan import ExecutablePlan
from ui_case_compiler.schema.validation import validate_plan

ROOT = Path(__file__).resolve().parents[2]


def _load_benchmark_module() -> ModuleType:
    path = ROOT / "benchmarks" / "context-aware" / "run_benchmark.py"
    spec = importlib.util.spec_from_file_location("context_aware_benchmark", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"无法加载 benchmark 模块: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


BENCHMARK = _load_benchmark_module()
ASSESS_FIDELITY = cast(
    Callable[[ExecutablePlan, dict[str, Any]], tuple[bool, str | None]],
    BENCHMARK._assess_plan_fidelity,
)
EXPECTED_TO_PLAN = cast(
    Callable[[dict[str, Any]], dict[str, Any]],
    BENCHMARK._expected_steps_to_plan,
)


def _case(case_id: str = "login-001") -> dict[str, Any]:
    dataset = json.loads(
        (ROOT / "benchmarks" / "context-aware" / "cases.json").read_text(
            encoding="utf-8"
        )
    )
    return next(case for case in dataset["cases"] if case["case_id"] == case_id)


def _expected_plan(case: dict[str, Any]) -> ExecutablePlan:
    return validate_plan(EXPECTED_TO_PLAN(case))


def test_expected_plan_passes_fidelity_check() -> None:
    case = _case("filter-002")

    passed, error = ASSESS_FIDELITY(_expected_plan(case), case)

    assert passed is True
    assert error is None


def test_missing_step_fails_fidelity_check() -> None:
    case = _case()
    data = EXPECTED_TO_PLAN(case)
    data["steps"].pop()
    plan = validate_plan(data)

    passed, error = ASSESS_FIDELITY(plan, case)

    assert passed is False
    assert error is not None
    assert "步骤类型不一致" in error


def test_wrong_input_value_fails_fidelity_check() -> None:
    case = _case()
    data = EXPECTED_TO_PLAN(case)
    data["steps"][1]["value"] = "wrong-user"
    plan = validate_plan(data)

    passed, error = ASSESS_FIDELITY(plan, case)

    assert passed is False
    assert error is not None
    assert "value 不一致" in error
