from ui_case_compiler.api.models import (
    CompileNlRequest,
    CompileRecordingRequest,
    RunRequest,
    ValidateResponse,
)
from ui_case_compiler.compiler.page_context_collector import PageContext


def test_compile_nl_request_parses() -> None:
    req = CompileNlRequest(
        text="Click Login",
        context=PageContext(url="https://example.test/login"),
    )
    assert req.text == "Click Login"
    assert req.context.url == "https://example.test/login"
    assert req.name is None


def test_compile_recording_request_defaults_name() -> None:
    req = CompileRecordingRequest(events=[{"type": "navigation", "timestamp": 0}])
    assert req.name == "Recorded Flow"


def test_run_request_defaults() -> None:
    req = RunRequest()
    assert req.params == {}
    assert req.headed is False


def test_validate_response_shape() -> None:
    resp = ValidateResponse(valid=True, plan_id="p1", step_count=3)
    assert resp.valid is True
    assert resp.step_count == 3
