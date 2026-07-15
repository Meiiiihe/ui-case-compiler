from __future__ import annotations

import argparse
import asyncio
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from typing import Any, Literal, cast

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from playwright.async_api import async_playwright  # noqa: E402

from ui_case_compiler.compiler import (  # noqa: E402
    ContextAwarePromptBuilder,
    DeepSeekProvider,
    PageContext,
    SemanticContextCollector,
)
from ui_case_compiler.compiler.llm_provider import LLMProvider  # noqa: E402
from ui_case_compiler.compiler.prompt_builder import PromptBuilder  # noqa: E402
from ui_case_compiler.config import RuntimeConfig, load_config  # noqa: E402
from ui_case_compiler.errors import UiCaseCompilerError  # noqa: E402
from ui_case_compiler.runner.locator_resolver import LocatorResolver  # noqa: E402
from ui_case_compiler.runner.plan_runner import PlanRunner, RunOptions  # noqa: E402
from ui_case_compiler.schema.executable_plan import ExecutablePlan  # noqa: E402
from ui_case_compiler.schema.steps import StepTarget  # noqa: E402
from ui_case_compiler.schema.validation import validate_plan  # noqa: E402

Mode = Literal["baseline", "context-aware"]


@dataclass
class CaseMetric:
    case_id: str
    page_type: str
    mode: Mode
    dsl_valid: bool = False
    plan_fidelity_passed: bool = False
    e2e_passed: bool = False
    compile_seconds: float = 0.0
    locator_steps: int = 0
    primary_unique: int = 0
    resolved_unique: int = 0
    fidelity_error: str | None = None
    error: str | None = None

    def to_json(self) -> dict[str, Any]:
        data = self.__dict__.copy()
        data["compile_seconds"] = round(self.compile_seconds, 3)
        return data


@dataclass
class ModeSummary:
    total_cases: int = 0
    dsl_valid_cases: int = 0
    plan_fidelity_cases: int = 0
    e2e_passed_cases: int = 0
    locator_steps: int = 0
    primary_unique_steps: int = 0
    resolved_unique_steps: int = 0
    total_compile_seconds: float = 0.0

    def add(self, metric: CaseMetric) -> None:
        self.total_cases += 1
        self.dsl_valid_cases += int(metric.dsl_valid)
        self.plan_fidelity_cases += int(metric.plan_fidelity_passed)
        self.e2e_passed_cases += int(metric.e2e_passed)
        self.locator_steps += metric.locator_steps
        self.primary_unique_steps += metric.primary_unique
        self.resolved_unique_steps += metric.resolved_unique
        self.total_compile_seconds += metric.compile_seconds

    def to_json(self) -> dict[str, Any]:
        return {
            "total_cases": self.total_cases,
            "dsl_valid_rate": _rate(self.dsl_valid_cases, self.total_cases),
            "plan_fidelity_rate": _rate(self.plan_fidelity_cases, self.total_cases),
            "e2e_pass_rate": _rate(self.e2e_passed_cases, self.total_cases),
            "primary_locator_unique_rate": _rate(
                self.primary_unique_steps, self.locator_steps
            ),
            "resolved_locator_unique_rate": _rate(
                self.resolved_unique_steps, self.locator_steps
            ),
            "locator_steps": self.locator_steps,
            "avg_compile_seconds": round(
                self.total_compile_seconds / self.total_cases
                if self.total_cases
                else 0.0,
                3,
            ),
        }


class EchoProvider:
    """Provider for smoke tests: it turns expected_steps into a deterministic plan."""

    def __init__(self, case: dict[str, Any]) -> None:
        self._case = case

    async def generate_plan_json(self, prompt: str) -> str:
        _ = prompt
        plan = _expected_steps_to_plan(self._case)
        return json.dumps(plan, ensure_ascii=False)


async def main() -> None:
    args = _parse_args()
    dataset = json.loads(args.cases.read_text(encoding="utf-8"))
    cases = cast(list[dict[str, Any]], dataset["cases"])
    if args.limit is not None:
        cases = cases[: args.limit]

    config = load_config()
    result_root = args.output
    result_root.mkdir(parents=True, exist_ok=True)

    collector = SemanticContextCollector(timeout_ms=config.timeout_ms)
    metrics: list[CaseMetric] = []
    summaries: dict[Mode, ModeSummary] = {
        "baseline": ModeSummary(),
        "context-aware": ModeSummary(),
    }

    for index, case in enumerate(cases, start=1):
        case_id = str(case["case_id"])
        print(f"[{index}/{len(cases)}] {case_id}")
        semantic = await collector.collect(str(case["page_url"]))

        for mode in ("baseline", "context-aware"):
            provider: LLMProvider
            if args.provider == "echo":
                provider = EchoProvider(case)
            else:
                provider = DeepSeekProvider(config.llm)

            metric = await _evaluate_case(
                case=case,
                mode=mode,
                provider=provider,
                config=config,
                result_root=result_root,
                semantic=semantic,
            )
            metrics.append(metric)
            summaries[mode].add(metric)
            _write_json(
                result_root / mode / f"{case_id}.metric.json",
                metric.to_json(),
            )

    summary = {
        "benchmark": dataset["name"],
        "dataset_version": dataset.get("version"),
        "total_cases": len(cases),
        "targets": {
            "status": "unverified",
            "locator_unique_rate": "68% -> 87%",
            "e2e_pass_rate": "54% -> 76%",
            "note": "这些数字是待验证目标，不是实际运行结果。",
        },
        "run_config": {
            "provider": args.provider,
            "model": config.llm.model if args.provider == "deepseek" else None,
            "temperature": 0 if args.provider == "deepseek" else None,
        },
        "baseline": summaries["baseline"].to_json(),
        "context_aware": summaries["context-aware"].to_json(),
        "cases": [metric.to_json() for metric in metrics],
    }
    _write_json(result_root / "summary.json", summary)
    print(json.dumps(summary["baseline"], ensure_ascii=False, indent=2))
    print(json.dumps(summary["context_aware"], ensure_ascii=False, indent=2))
    print(f"summary: {result_root / 'summary.json'}")


async def _evaluate_case(
    *,
    case: dict[str, Any],
    mode: Mode,
    provider: LLMProvider,
    config: RuntimeConfig,
    result_root: Path,
    semantic: Any,
) -> CaseMetric:
    case_id = str(case["case_id"])
    metric = CaseMetric(case_id=case_id, page_type=str(case["page_type"]), mode=mode)
    mode_dir = result_root / mode
    mode_dir.mkdir(parents=True, exist_ok=True)

    context = _build_context(case, mode, semantic)
    builder = ContextAwarePromptBuilder() if mode == "context-aware" else PromptBuilder()
    prompt = builder.build(str(case["natural_language"]), context)
    _write_text(mode_dir / f"{case_id}.prompt.txt", prompt)

    start = perf_counter()
    try:
        raw_plan = await provider.generate_plan_json(prompt)
        metric.compile_seconds = perf_counter() - start
        _write_text(mode_dir / f"{case_id}.raw.json", raw_plan)
        plan = validate_plan(json.loads(raw_plan))
        metric.dsl_valid = True
        _write_json(mode_dir / f"{case_id}.plan.json", plan.model_dump(mode="json"))
        metric.plan_fidelity_passed, metric.fidelity_error = _assess_plan_fidelity(
            plan, case
        )
        locator_counts = await _measure_locator_uniqueness(plan)
        metric.locator_steps = locator_counts["locator_steps"]
        metric.primary_unique = locator_counts["primary_unique"]
        metric.resolved_unique = locator_counts["resolved_unique"]
        if metric.plan_fidelity_passed:
            metric.e2e_passed = await _run_e2e(plan, config, mode_dir)
    except Exception as exc:  # noqa: BLE001 - benchmark records any failure
        if metric.compile_seconds == 0.0:
            metric.compile_seconds = perf_counter() - start
        metric.error = f"{type(exc).__name__}: {exc}"

    return metric


def _build_context(case: dict[str, Any], mode: Mode, semantic: Any) -> PageContext:
    if mode == "baseline":
        return PageContext(
            url=str(case["page_url"]),
            title=str(semantic.title),
            dom_summary=semantic.to_baseline_dom_summary(),
        )
    return PageContext(
        url=str(case["page_url"]),
        title=str(semantic.title),
        dom_summary=semantic.to_prompt_json(),
    )


def _assess_plan_fidelity(
    plan: ExecutablePlan, case: dict[str, Any]
) -> tuple[bool, str | None]:
    expected_steps = [
        step for step in case.get("expected_steps", []) if step.get("type") != "wait"
    ]
    actual_steps = [step for step in plan.steps if step.type != "wait"]

    expected_types = [str(step.get("type")) for step in expected_steps]
    actual_types = [step.type for step in actual_steps]
    if actual_types != expected_types:
        return False, f"步骤类型不一致: expected={expected_types}, actual={actual_types}"

    for index, (expected_step, actual_step) in enumerate(
        zip(expected_steps, actual_steps, strict=True), start=1
    ):
        for field in ("url", "value", "key", "checked", "expected"):
            if field not in expected_step:
                continue
            expected_value = expected_step[field]
            actual_value = getattr(actual_step, field, None)
            if actual_value != expected_value:
                return (
                    False,
                    f"step {index} 的 {field} 不一致: "
                    f"expected={expected_value!r}, actual={actual_value!r}",
                )

    actual_assertions = [
        str(expected)
        for step in actual_steps
        if step.type.startswith("assert_")
        if (expected := getattr(step, "expected", None)) is not None
    ]
    for expected_assertion in case.get("expected_assertions", []):
        if not any(
            str(expected_assertion) in actual_assertion
            for actual_assertion in actual_assertions
        ):
            return False, f"缺少期望断言: {expected_assertion}"

    return True, None


async def _measure_locator_uniqueness(plan: ExecutablePlan) -> dict[str, int]:
    resolver = LocatorResolver(wait_timeout_ms=500, poll_interval_ms=50)
    stats = {"locator_steps": 0, "primary_unique": 0, "resolved_unique": 0}

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        page = await browser.new_page()
        try:
            for step in plan.steps:
                if step.type == "navigate" and hasattr(step, "url"):
                    await page.goto(step.url)
                    continue

                target = getattr(step, "target", None)
                if not isinstance(target, StepTarget):
                    continue

                stats["locator_steps"] += 1
                primary_count = await _safe_count(
                    resolver.to_playwright_locator(page, target.primary)
                )
                if primary_count == 1:
                    stats["primary_unique"] += 1

                candidate_counts = [
                    primary_count,
                    *[
                        await _safe_count(resolver.to_playwright_locator(page, candidate))
                        for candidate in target.fallbacks
                    ],
                ]
                if any(count == 1 for count in candidate_counts):
                    stats["resolved_unique"] += 1
        finally:
            await browser.close()

    return stats


async def _safe_count(locator: Any) -> int:
    try:
        return int(await locator.count())
    except Exception:
        return 0


async def _run_e2e(plan: ExecutablePlan, config: RuntimeConfig, mode_dir: Path) -> bool:
    run_config = config.model_copy(
        update={
            "headless": True,
            "output_dir": mode_dir / "runs",
            "trace_enabled": False,
            "screenshot_on_failure": False,
        }
    )
    try:
        result = await PlanRunner(run_config).run(
            plan,
            RunOptions(headless=True, output_dir=run_config.output_dir),
        )
        return result.status == "passed"
    except UiCaseCompilerError:
        return False


def _expected_steps_to_plan(case: dict[str, Any]) -> dict[str, Any]:
    steps: list[dict[str, Any]] = [
        {"id": "step-001", "type": "navigate", "url": case["page_url"]}
    ]
    for index, expected_step in enumerate(case.get("expected_steps", [])[1:], start=2):
        step_type = str(expected_step["type"])
        step: dict[str, Any] = {"id": f"step-{index:03d}", "type": step_type}
        target_hint = str(expected_step.get("target_hint") or expected_step.get("expected") or "")
        if step_type in {
            "click",
            "fill",
            "select",
            "check",
            "hover",
            "assert_text",
            "assert_visible",
            "assert_value",
        }:
            step["target"] = _target_from_hint(step_type, target_hint)
        if "value" in expected_step:
            step["value"] = expected_step["value"]
        if step_type == "check":
            step["checked"] = True
        if "expected" in expected_step:
            step["expected"] = expected_step["expected"]
        steps.append(step)
    return {
        "id": str(case["case_id"]),
        "name": str(case["case_id"]),
        "source": "natural_language",
        "base_url": case["page_url"],
        "steps": steps,
    }


def _target_from_hint(step_type: str, target_hint: str) -> dict[str, Any]:
    role_name = (
        target_hint.replace("按钮", "")
        .replace("链接", "")
        .replace("输入框", "")
        .strip()
    )
    if step_type in {"fill", "select", "check", "assert_value"}:
        primary = {"strategy": "label", "value": role_name or target_hint}
        fallbacks: list[dict[str, Any]] = [
            {"strategy": "placeholder", "value": role_name or target_hint},
            {"strategy": "text", "value": role_name or target_hint},
        ]
    elif step_type == "click":
        primary = {"strategy": "role", "role": "button", "name": role_name or target_hint}
        fallbacks = [
            {"strategy": "text", "value": role_name or target_hint},
            {"strategy": "label", "value": role_name or target_hint},
        ]
    else:
        primary = {"strategy": "text", "value": role_name or target_hint}
        fallbacks = [
            {"strategy": "css", "value": "[role='status']"},
            {"strategy": "css", "value": ".msg"},
            {"strategy": "css", "value": ".toast"},
        ]

    return {
        "primary": primary,
        "fallbacks": fallbacks,
        "confidence": 0.5,
    }


def _rate(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 4) if denominator else 0.0


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run context-aware UI compiler benchmark.")
    parser.add_argument(
        "--cases",
        type=Path,
        default=ROOT / "benchmarks" / "context-aware" / "cases.json",
        help="Path to benchmark cases.json.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "benchmarks" / "context-aware" / "results",
        help="Directory for benchmark results.",
    )
    parser.add_argument(
        "--provider",
        choices=["deepseek", "echo"],
        default="deepseek",
        help="deepseek runs real LLM evaluation; echo is a local smoke-test provider.",
    )
    parser.add_argument("--limit", type=int, default=None, help="Limit number of cases.")
    return parser.parse_args()


if __name__ == "__main__":
    asyncio.run(main())
