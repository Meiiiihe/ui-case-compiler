import pytest
from pydantic import ValidationError

from ui_case_compiler.schema.steps import ClickStep, Locator, NavigateStep, PressStep, WaitStep


def test_role_locator_requires_role() -> None:
    with pytest.raises(ValidationError):
        Locator(strategy="role", name="登录")


def test_text_locator_requires_value() -> None:
    with pytest.raises(ValidationError):
        Locator(strategy="text")


def test_click_step_requires_target() -> None:
    with pytest.raises(ValidationError):
        ClickStep.model_validate({"id": "step-1", "type": "click"})


def test_navigate_step_requires_url() -> None:
    with pytest.raises(ValidationError):
        NavigateStep.model_validate({"id": "step-1", "type": "navigate"})


def test_wait_step_has_upper_bound() -> None:
    with pytest.raises(ValidationError):
        WaitStep(id="step-1", duration_ms=60_001)


def test_press_step_requires_key() -> None:
    with pytest.raises(ValidationError):
        PressStep.model_validate(
            {
                "id": "step-1",
                "type": "press",
                "target": {"primary": {"strategy": "css", "value": "#search"}},
            }
        )
