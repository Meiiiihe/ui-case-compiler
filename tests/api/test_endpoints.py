import json
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from ui_case_compiler.api.app import create_app
from ui_case_compiler.config import LLMConfig, RuntimeConfig


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

    runs = client.get("/api/runs")
    assert resp.json()["run_id"] in {r["run_id"] for r in runs.json()}


def test_cors_header_present(tmp_path: Path) -> None:
    client = _client(tmp_path)
    resp = client.get("/api/cases", headers={"Origin": "http://localhost:5173"})
    assert resp.headers.get("access-control-allow-origin") == "http://localhost:5173"


def _login_plan_json(root: Path) -> dict:
    return json.loads((root / "examples" / "plans" / "login.json").read_text(encoding="utf-8"))
