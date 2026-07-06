import pytest

from ui_case_compiler.errors import RecordingError
from ui_case_compiler.recorder import RecordedElement, RecordedEvent, RecordingCompiler
from ui_case_compiler.schema.steps import NavigateStep


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


def test_merges_input_events_with_same_css_even_when_xpath_changes() -> None:
    compiler = RecordingCompiler()
    events = [
        RecordedEvent(
            type="input",
            timestamp=1,
            value="w",
            element=RecordedElement(tag="textarea", role="textbox", css="#chat-textarea"),
        ),
        RecordedEvent(
            type="input",
            timestamp=2,
            value="wang",
            element=RecordedElement(
                tag="textarea",
                role="textbox",
                css="#chat-textarea",
                xpath="/html/body/div[1]/textarea[1]",
            ),
        ),
        RecordedEvent(
            type="input",
            timestamp=3,
            value="wang",
            element=RecordedElement(
                tag="textarea",
                role="textbox",
                css="#chat-textarea",
                xpath="/html/body/div[2]/textarea[1]",
            ),
        ),
    ]

    plan = compiler.compile(events, "Search")

    assert len(plan.steps) == 1
    assert plan.steps[0].type == "fill"
    assert plan.steps[0].value == "wang"  # type: ignore[union-attr]


def test_merges_text_input_and_change_events_with_same_value() -> None:
    compiler = RecordingCompiler()
    element = RecordedElement(tag="textarea", role="textbox", css="#chat-textarea")
    events = [
        RecordedEvent(type="input", timestamp=1, value="王俊凯", element=element),
        RecordedEvent(type="change", timestamp=2, value="王俊凯", element=element),
    ]

    plan = compiler.compile(events, "Search")

    assert len(plan.steps) == 1
    assert plan.steps[0].type == "fill"
    assert plan.steps[0].value == "王俊凯"  # type: ignore[union-attr]


def test_keypress_event_compiles_to_press_step() -> None:
    compiler = RecordingCompiler()
    element = RecordedElement(tag="textarea", role="textbox", css="#chat-textarea")
    events = [
        RecordedEvent(type="input", timestamp=1, value="王俊凯", element=element),
        RecordedEvent(type="keypress", timestamp=2, value="Enter", element=element),
        RecordedEvent(type="navigation", timestamp=3, url="https://www.baidu.com/s?wd=wang"),
    ]

    plan = compiler.compile(events, "Search")

    assert [step.type for step in plan.steps] == ["fill", "press", "navigate"]
    assert plan.steps[0].value == "王俊凯"  # type: ignore[union-attr]
    assert plan.steps[1].key == "Enter"  # type: ignore[union-attr]


def test_filters_captcha_navigation_and_interactions_from_recording() -> None:
    compiler = RecordingCompiler()
    input_element = RecordedElement(tag="textarea", role="textbox", css="#chat-textarea")
    captcha_element = RecordedElement(
        tag="div",
        css="#spin-0 > div:nth-of-type(2)",
        xpath="/html/body/div[3]/div[2]",
    )
    events = [
        RecordedEvent(type="navigation", timestamp=1, url="https://www.baidu.com/"),
        RecordedEvent(type="input", timestamp=2, value="wang", element=input_element),
        RecordedEvent(
            type="navigation",
            timestamp=3,
            url="https://www.baidu.com/s?wd=wang",
        ),
        RecordedEvent(
            type="navigation",
            timestamp=4,
            url="https://wappass.baidu.com/static/captcha/tuxing_v2.html?backurl=...",
        ),
        RecordedEvent(type="click", timestamp=5, element=captcha_element),
        RecordedEvent(type="click", timestamp=6, element=captcha_element),
        RecordedEvent(
            type="navigation",
            timestamp=7,
            url="https://www.baidu.com/s?wd=wang&rsv_jmp=fail&p_tk=dynamic",
        ),
    ]

    plan = compiler.compile(events, "Baidu Search")

    assert [step.type for step in plan.steps] == ["navigate", "fill", "navigate"]
    navigation_urls = [step.url for step in plan.steps if isinstance(step, NavigateStep)]
    assert all("wappass.baidu.com" not in url for url in navigation_urls)
    assert all("rsv_jmp=fail" not in url for url in navigation_urls)


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
