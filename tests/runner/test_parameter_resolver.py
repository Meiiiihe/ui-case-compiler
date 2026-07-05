import pytest

from ui_case_compiler.errors import PlanValidationError
from ui_case_compiler.runner.parameter_resolver import ParameterContext, ParameterResolver
from ui_case_compiler.schema.steps import FillStep, Locator, StepTarget


def _fill_step(value: str) -> FillStep:
    return FillStep(
        id="fill-username",
        target=StepTarget(primary=Locator(strategy="label", value="用户名")),
        value=value,
    )


def test_runtime_parameter_has_highest_priority() -> None:
    resolver = ParameterResolver()
    context = ParameterContext(
        runtime={"username": "runtime_user"},
        case={"username": "case_user"},
        environment={"username": "env_user"},
        global_params={"username": "global_user"},
    )

    assert resolver.resolve_value("${username}", context) == "runtime_user"


def test_missing_parameter_reports_name_and_step() -> None:
    resolver = ParameterResolver()

    with pytest.raises(PlanValidationError, match="orderId.*fill-username"):
        resolver.resolve_step(_fill_step("${orderId}"), ParameterContext())


def test_dynamic_variables_are_stable_within_resolver() -> None:
    resolver = ParameterResolver()
    context = ParameterContext()

    first = resolver.resolve_value("${randomString}", context)
    second = resolver.resolve_value("${randomString}", context)

    assert first == second


def test_resolve_step_revalidates_step_model() -> None:
    resolver = ParameterResolver()
    step = resolver.resolve_step(
        _fill_step("user-${timestamp}"),
        ParameterContext(),
    )

    assert isinstance(step, FillStep)
    assert step.value.startswith("user-")

