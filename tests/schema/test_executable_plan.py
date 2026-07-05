import pytest

from ui_case_compiler.errors import PlanValidationError
from ui_case_compiler.schema import ExecutablePlan, validate_plan


def _target() -> dict[str, object]:
    return {
        "primary": {"strategy": "role", "role": "button", "name": "登录"},
        "fallbacks": [{"strategy": "text", "value": "登录"}],
        "confidence": 0.95,
    }


def test_valid_manual_plan() -> None:
    plan = validate_plan(
        {
            "id": "plan-login",
            "name": "登录流程",
            "source": "manual",
            "parameters": {"username": "${username}"},
            "steps": [
                {"id": "s1", "type": "navigate", "url": "https://example.com"},
                {"id": "s2", "type": "click", "target": _target()},
                {"id": "s3", "type": "assert_text", "target": _target(), "expected": "欢迎回来"},
            ],
        }
    )

    assert isinstance(plan, ExecutablePlan)
    assert plan.steps[1].type == "click"


def test_unknown_step_type_fails() -> None:
    with pytest.raises(PlanValidationError):
        validate_plan(
            {
                "id": "plan-bad",
                "name": "bad",
                "source": "manual",
                "steps": [{"id": "s1", "type": "unknown"}],
            }
        )


def test_empty_plan_fails() -> None:
    with pytest.raises(PlanValidationError):
        validate_plan({"id": "plan-empty", "name": "empty", "source": "manual", "steps": []})

