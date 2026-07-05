from __future__ import annotations

import re
import secrets
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

from ui_case_compiler.errors import PlanValidationError
from ui_case_compiler.schema.steps import Step

VARIABLE_PATTERN = re.compile(r"\$\{(?P<name>[A-Za-z_][A-Za-z0-9_]*)\}")


class ParameterContext(BaseModel):
    """Parameters available for one plan execution."""

    model_config = ConfigDict(extra="forbid")

    runtime: dict[str, Any] = Field(default_factory=dict)
    case: dict[str, Any] = Field(default_factory=dict)
    environment: dict[str, Any] = Field(default_factory=dict)
    global_params: dict[str, Any] = Field(default_factory=dict)


class ParameterResolver:
    """Resolve variable placeholders in step data."""

    def __init__(self) -> None:
        self._dynamic_values: dict[str, str] = {}
        self._step_adapter: TypeAdapter[Step] = TypeAdapter(Step)

    def resolve_value(
        self,
        value: Any,
        context: ParameterContext,
        *,
        step_id: str | None = None,
    ) -> Any:
        if isinstance(value, str):
            return self._resolve_string(value, context, step_id=step_id)
        if isinstance(value, list):
            return [self.resolve_value(item, context, step_id=step_id) for item in value]
        if isinstance(value, dict):
            return {
                key: self.resolve_value(item, context, step_id=step_id)
                for key, item in value.items()
            }
        return value

    def resolve_step(self, step: Step, context: ParameterContext) -> Step:
        step_id = step.id
        data = step.model_dump()
        resolved = self.resolve_value(data, context, step_id=step_id)
        return self._step_adapter.validate_python(resolved)

    def _resolve_string(
        self,
        value: str,
        context: ParameterContext,
        *,
        step_id: str | None,
    ) -> str:
        def replace(match: re.Match[str]) -> str:
            name = match.group("name")
            resolved = self._resolve_name(name, context, step_id=step_id)
            return str(resolved)

        return VARIABLE_PATTERN.sub(replace, value)

    def _resolve_name(
        self,
        name: str,
        context: ParameterContext,
        *,
        step_id: str | None,
    ) -> Any:
        if name in {"timestamp", "randomString"}:
            return self._resolve_dynamic(name)

        for source in (context.runtime, context.case, context.environment, context.global_params):
            if name in source:
                return source[name]

        location = f" in step '{step_id}'" if step_id else ""
        msg = f"Missing parameter '{name}'{location}"
        raise PlanValidationError(msg)

    def _resolve_dynamic(self, name: str) -> str:
        if name not in self._dynamic_values:
            if name == "timestamp":
                self._dynamic_values[name] = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
            else:
                self._dynamic_values[name] = secrets.token_hex(4)
        return self._dynamic_values[name]
