from datetime import UTC, datetime
from pathlib import Path

import pytest

from ui_case_compiler.errors import StorageError
from ui_case_compiler.reporter import RunResult
from ui_case_compiler.schema import ExecutablePlan
from ui_case_compiler.storage import CaseRepository, FileStore, RunRepository


def _plan() -> ExecutablePlan:
    return ExecutablePlan.model_validate(
        {
            "id": "plan-1",
            "name": "计划",
            "source": "manual",
            "steps": [{"id": "s1", "type": "navigate", "url": "https://example.com"}],
        }
    )


def test_case_repository_saves_and_loads_plan(tmp_path: Path) -> None:
    repository = CaseRepository(FileStore(tmp_path))

    path = repository.save_plan(_plan())
    loaded = repository.load_plan("plan-1")

    assert path.exists()
    assert loaded.id == "plan-1"


def test_run_repository_saves_and_loads_result(tmp_path: Path) -> None:
    repository = RunRepository(FileStore(tmp_path))
    result = RunResult(
        run_id="run-1",
        plan_id="plan-1",
        status="passed",
        started_at=datetime.now(UTC),
        ended_at=datetime.now(UTC),
        steps=[],
    )

    path = repository.save_result(result)
    loaded = repository.load_result("run-1")

    assert path.exists()
    assert loaded.run_id == "run-1"


def test_file_store_reports_invalid_json(tmp_path: Path) -> None:
    bad_json = tmp_path / "bad.json"
    bad_json.write_text("{", encoding="utf-8")

    with pytest.raises(StorageError):
        FileStore(tmp_path).read_json(bad_json)


def test_case_repository_list_summaries(tmp_path: Path) -> None:
    repo = CaseRepository(FileStore(tmp_path))
    repo.save_plan(
        ExecutablePlan.model_validate(
            {
                "id": "p1",
                "name": "Plan One",
                "source": "manual",
                "steps": [{"id": "s1", "type": "navigate", "url": "https://example.test"}],
            }
        )
    )
    repo.save_plan(
        ExecutablePlan.model_validate(
            {
                "id": "p2",
                "name": "Plan Two",
                "source": "recording",
                "steps": [{"id": "s1", "type": "navigate", "url": "https://example.test"}],
            }
        )
    )

    summaries = repo.list_summaries()

    assert {s.id for s in summaries} == {"p1", "p2"}
    one = next(s for s in summaries if s.id == "p1")
    assert one.name == "Plan One"
    assert one.source == "manual"
    assert one.step_count == 1


def test_case_repository_list_summaries_empty(tmp_path: Path) -> None:
    repo = CaseRepository(FileStore(tmp_path))
    assert repo.list_summaries() == []


def test_run_repository_list_summaries(tmp_path: Path) -> None:
    repo = RunRepository(FileStore(tmp_path))
    repo.save_result(
        RunResult(
            run_id="r1",
            plan_id="p1",
            status="passed",
            started_at=datetime(2026, 7, 5, tzinfo=UTC),
            ended_at=datetime(2026, 7, 5, tzinfo=UTC),
            steps=[],
        )
    )

    summaries = repo.list_summaries()

    assert len(summaries) == 1
    assert summaries[0].run_id == "r1"
    assert summaries[0].plan_id == "p1"
    assert summaries[0].status == "passed"

