import base64
import json
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from ui_case_compiler.api.app import create_app
from ui_case_compiler.config import LLMConfig, RuntimeConfig
from ui_case_compiler.recorder.recorder_session import RecordedElement, RecordedEvent
from ui_case_compiler.reporter.run_result import RunResult, StepResult
from ui_case_compiler.storage.file_store import FileStore
from ui_case_compiler.storage.run_repository import RunRepository


def _client(tmp_path: Path, api_key: str | None = "sk-test") -> TestClient:
    config = RuntimeConfig(output_dir=tmp_path, llm=LLMConfig(api_key=api_key))
    return TestClient(create_app(config))


def _recording_body() -> dict:
    return {
        "events": [
            {"type": "navigation", "timestamp": 0, "url": "https://example.test/login"},
            {
                "type": "click",
                "timestamp": 1,
                "element": {"tag": "button", "role": "button", "text": "Login"},
            },
        ],
        "name": "Rec",
    }


def test_list_cases_empty(tmp_path: Path) -> None:
    client = _client(tmp_path)
    resp = client.get("/api/cases")
    assert resp.status_code == 200
    assert resp.json() == []


def test_compile_recording_then_get_and_list(tmp_path: Path) -> None:
    client = _client(tmp_path)

    resp = client.post("/api/cases/compile-recording", json=_recording_body())
    assert resp.status_code == 200
    plan_id = resp.json()["id"]

    listed = client.get("/api/cases")
    assert plan_id in {c["id"] for c in listed.json()}

    got = client.get(f"/api/cases/{plan_id}")
    assert got.status_code == 200
    assert got.json()["source"] == "recording"


def test_start_and_stop_recording_endpoint(tmp_path: Path) -> None:
    client = _client(tmp_path)

    async def fake_record(self: object, url: str):
        return [
            RecordedEvent(type="navigation", timestamp=0, url=url),
            RecordedEvent(
                type="click",
                timestamp=1,
                element=RecordedElement(tag="button", role="button", text="Login"),
            ),
        ]

    with patch("ui_case_compiler.recorder.live_recorder.LiveRecorder.record", fake_record):
        start = client.post(
            "/api/recordings/start",
            json={"url": "https://example.test/login", "name": "Live Rec"},
        )
        assert start.status_code == 200
        session_id = start.json()["session_id"]

        stop = client.post(f"/api/recordings/{session_id}/stop")

    assert stop.status_code == 200
    assert stop.json()["source"] == "recording"


def test_get_missing_case_returns_404(tmp_path: Path) -> None:
    client = _client(tmp_path)
    resp = client.get("/api/cases/nope")
    assert resp.status_code == 404
    assert "detail" in resp.json()


def test_validate_endpoint(tmp_path: Path) -> None:
    client = _client(tmp_path)
    plan_id = client.post("/api/cases/compile-recording", json=_recording_body()).json()["id"]

    resp = client.post(f"/api/cases/{plan_id}/validate")
    assert resp.status_code == 200
    assert resp.json()["valid"] is True


def test_compile_nl_missing_api_key_returns_400(tmp_path: Path) -> None:
    client = _client(tmp_path, api_key=None)
    resp = client.post(
        "/api/cases/compile-nl",
        json={"text": "go", "context": {"url": "https://example.test/login"}},
    )
    assert resp.status_code == 400
    assert "API key" in resp.json()["detail"]


def test_compile_nl_with_patched_provider(tmp_path: Path) -> None:
    client = _client(tmp_path)
    fake_json = (
        '{"id": "nl", "name": "NL", "source": "natural_language",'
        ' "steps": [{"id": "step-001", "type": "navigate", "url": "https://example.test"}]}'
    )

    async def fake_generate(self: object, prompt: str) -> str:
        return fake_json

    with patch(
        "ui_case_compiler.compiler.deepseek_provider.DeepSeekProvider.generate_plan_json",
        fake_generate,
    ):
        resp = client.post(
            "/api/cases/compile-nl",
            json={"text": "go", "context": {"url": "https://example.test/login"}},
        )
    assert resp.status_code == 200
    assert resp.json()["source"] == "natural_language"


def test_run_endpoint_against_local_page(tmp_path: Path) -> None:
    client = _client(tmp_path)
    root = Path(__file__).resolve().parents[2]
    login_url = (root / "examples" / "pages" / "login.html").resolve().as_uri()
    plan_body = _login_plan_json(root)

    put = client.put(f"/api/cases/{plan_body['id']}", json=plan_body)
    assert put.status_code == 200

    resp = client.post(
        f"/api/cases/{plan_body['id']}/run",
        json={"params": {"loginPageUrl": login_url}},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "passed"
    assert resp.json()["report_path"]

    runs = client.get("/api/runs")
    assert resp.json()["run_id"] in {r["run_id"] for r in runs.json()}


def test_run_artifact_endpoints_return_files(tmp_path: Path) -> None:
    client = _client(tmp_path)
    run_dir = tmp_path / "artifacts" / "r1"
    run_dir.mkdir(parents=True)
    screenshot = run_dir / "010-step-010.png"
    trace = run_dir / "trace.zip"
    report = tmp_path / "reports" / "r1.html"
    screenshot.write_bytes(b"fake-png")
    trace.write_bytes(b"fake-trace")
    report.parent.mkdir(parents=True)
    report.write_text("<html>report</html>", encoding="utf-8")

    RunRepository(FileStore(tmp_path)).save_result(
        RunResult(
            run_id="r1",
            plan_id="p1",
            status="failed",
            started_at=datetime.now(UTC),
            ended_at=datetime.now(UTC),
            steps=[
                StepResult(
                    step_id="step-010",
                    step_type="click",
                    status="failed",
                    duration_ms=12,
                    error="not found",
                    screenshot=screenshot,
                )
            ],
            trace_path=trace,
            report_path=report,
        )
    )

    shot_resp = client.get("/api/runs/r1/steps/step-010/screenshot")
    trace_resp = client.get("/api/runs/r1/artifacts/trace")
    report_resp = client.get("/api/runs/r1/artifacts/report")

    assert shot_resp.status_code == 200
    assert shot_resp.content == b"fake-png"
    assert trace_resp.status_code == 200
    assert trace_resp.content == b"fake-trace"
    assert report_resp.status_code == 200
    assert "report" in report_resp.text


def test_preview_dataset_endpoint(tmp_path: Path) -> None:
    client = _client(tmp_path)
    content = base64.b64encode(b"username,password\nalice,secret\n").decode()

    resp = client.post(
        "/api/datasets/preview",
        json={"filename": "login.csv", "content_base64": content},
    )

    assert resp.status_code == 200
    assert resp.json()["columns"] == ["username", "password"]
    assert resp.json()["row_count"] == 1


def test_batch_run_endpoint_saves_batch_and_runs(tmp_path: Path) -> None:
    client = _client(tmp_path)
    plan_id = client.post("/api/cases/compile-recording", json=_recording_body()).json()["id"]

    async def fake_run(self: object, plan: object, options: object) -> RunResult:
        _ = self, plan, options
        return RunResult(
            run_id="run-row",
            plan_id=plan_id,
            status="passed",
            started_at=datetime.now(UTC),
            ended_at=datetime.now(UTC),
            steps=[],
        )

    with patch("ui_case_compiler.runner.plan_runner.PlanRunner.run", fake_run):
        resp = client.post(
            f"/api/cases/{plan_id}/batch-run",
            json={
                "rows": [
                    {"username": "alice", "password": "secret"},
                    {"username": "bob", "password": "wrong"},
                ],
                "concurrency": 2,
            },
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 2
    assert body["passed"] == 2
    assert body["concurrency"] == 2
    assert all(result["run_id"] for result in body["results"])

    listed = client.get("/api/batch-runs")
    assert body["batch_id"] in {item["batch_id"] for item in listed.json()}

    got = client.get(f"/api/batch-runs/{body['batch_id']}")
    assert got.status_code == 200
    assert got.json()["total"] == 2


def test_cors_header_present(tmp_path: Path) -> None:
    client = _client(tmp_path)
    resp = client.get("/api/cases", headers={"Origin": "http://localhost:5173"})
    assert resp.headers.get("access-control-allow-origin") == "http://localhost:5173"


def _login_plan_json(root: Path) -> dict:
    return json.loads((root / "examples" / "plans" / "login.json").read_text(encoding="utf-8"))
