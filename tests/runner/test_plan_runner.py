from pathlib import Path

import pytest

from ui_case_compiler.config import RuntimeConfig
from ui_case_compiler.runner.plan_runner import PlanRunner, RunOptions
from ui_case_compiler.schema import ExecutablePlan


def _login_page(path: Path) -> None:
    path.write_text(
        """
        <!doctype html>
        <html lang="zh-CN">
          <body>
            <label>用户名 <input aria-label="用户名" id="username"></label>
            <label>密码 <input aria-label="密码" id="password" type="password"></label>
            <button onclick="document.querySelector('#message').textContent='欢迎回来'">
              登录
            </button>
            <div id="message"></div>
          </body>
        </html>
        """,
        encoding="utf-8",
    )


def _target(strategy: str, value: str) -> dict[str, object]:
    return {"primary": {"strategy": strategy, "value": value}}


def _plan(page: Path, expected: str = "欢迎回来") -> ExecutablePlan:
    return ExecutablePlan.model_validate(
        {
            "id": "plan-login",
            "name": "登录流程",
            "source": "manual",
            "parameters": {"username": "alice", "password": "secret"},
            "steps": [
                {"id": "s1", "type": "navigate", "url": page.as_uri()},
                {
                    "id": "s2",
                    "type": "fill",
                    "target": _target("label", "用户名"),
                    "value": "${username}",
                },
                {
                    "id": "s3",
                    "type": "fill",
                    "target": _target("label", "密码"),
                    "value": "${password}",
                },
                {
                    "id": "s4",
                    "type": "click",
                    "target": {"primary": {"strategy": "role", "role": "button", "name": "登录"}},
                },
                {
                    "id": "s5",
                    "type": "assert_text",
                    "target": _target("css", "#message"),
                    "expected": expected,
                },
            ],
        }
    )


@pytest.mark.asyncio
async def test_plan_runner_executes_successful_plan(tmp_path: Path) -> None:
    page = tmp_path / "login.html"
    _login_page(page)

    result = await PlanRunner(RuntimeConfig(output_dir=tmp_path / "out")).run(
        _plan(page),
        RunOptions(),
    )

    assert result.status == "passed"
    assert [step.status for step in result.steps] == ["passed"] * 5


@pytest.mark.asyncio
async def test_plan_runner_records_failed_step_and_screenshot(tmp_path: Path) -> None:
    page = tmp_path / "login.html"
    _login_page(page)

    result = await PlanRunner(RuntimeConfig(output_dir=tmp_path / "out")).run(
        _plan(page, expected="不会出现"),
        RunOptions(),
    )

    assert result.status == "failed"
    failed_step = next(step for step in result.steps if step.status == "failed")
    assert failed_step.step_id == "s5"
    assert failed_step.error
    assert failed_step.screenshot is not None
    assert failed_step.screenshot.exists()
