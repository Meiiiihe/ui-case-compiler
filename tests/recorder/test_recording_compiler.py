import pytest

from ui_case_compiler.errors import RecordingError
from ui_case_compiler.recorder import RecordedElement, RecordedEvent, RecordingCompiler


def test_compiles_login_event_stream_to_fill_and_click_steps() -> None:
    compiler = RecordingCompiler()
    events = [
        RecordedEvent(type="navigation", timestamp=1, url="https://example.test/login"),
        RecordedEvent(
            type="input",
            timestamp=2,
            value="alice",
            element=RecordedElement(tag="input", label="Username", css="#username"),
        ),
        RecordedEvent(
            type="input",
            timestamp=3,
            value="secret",
            element=RecordedElement(tag="input", label="Password", css="#password"),
        ),
        RecordedEvent(
            type="click",
            timestamp=4,
            element=RecordedElement(
                tag="button",
                role="button",
                text="Login",
                css="button[type=submit]",
            ),
        ),
    ]

    plan = compiler.compile(events, "Login Flow")

    assert plan.id == "recording-login-flow"
    assert plan.source == "recording"
    assert plan.base_url == "https://example.test/login"
    assert [step.type for step in plan.steps] == ["navigate", "fill", "fill", "click"]
    assert plan.steps[3].target.primary.strategy == "role"  # type: ignore[union-attr]
    assert plan.steps[3].target.primary.role == "button"  # type: ignore[union-attr]


def test_ignores_mousemove_and_merges_consecutive_input_events() -> None:
    compiler = RecordingCompiler()
    element = RecordedElement(tag="input", placeholder="Search", css="#search")
    events = [
        RecordedEvent(type="mousemove", timestamp=1, element=element),
        RecordedEvent(type="input", timestamp=2, value="t", element=element),
        RecordedEvent(type="input", timestamp=3, value="te", element=element),
        RecordedEvent(type="input", timestamp=4, value="test", element=element),
    ]

    plan = compiler.compile(events, "Search")

    assert len(plan.steps) == 1
    assert plan.steps[0].type == "fill"
    assert plan.steps[0].value == "test"  # type: ignore[union-attr]


def test_change_event_uses_select_for_select_element() -> None:
    compiler = RecordingCompiler()
    events = [
        RecordedEvent(
            type="change",
            timestamp=1,
            value="paid",
            element=RecordedElement(tag="select", label="Status", css="#status"),
        )
    ]

    plan = compiler.compile(events, "Filter")

    assert plan.steps[0].type == "select"


def test_event_without_locator_information_fails() -> None:
    compiler = RecordingCompiler()
    events = [RecordedEvent(type="click", timestamp=1, element=RecordedElement(tag="button"))]

    with pytest.raises(RecordingError):
        compiler.compile(events, "Broken")


def test_noise_only_stream_fails_instead_of_creating_empty_plan() -> None:
    compiler = RecordingCompiler()
    events = [RecordedEvent(type="mousemove", timestamp=1)]

    with pytest.raises(RecordingError):
        compiler.compile(events, "Noise")
