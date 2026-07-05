from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from ui_case_compiler.errors import RecordingError
from ui_case_compiler.recorder.recorder_session import RecordedEvent


class EventCollector:
    """Validate raw recorded event payloads from JSON-compatible data."""

    def collect(self, raw_events: Sequence[Mapping[str, object]]) -> list[RecordedEvent]:
        try:
            return [RecordedEvent.model_validate(event) for event in raw_events]
        except ValueError as exc:
            msg = "Recorded event payload is invalid"
            raise RecordingError(msg) from exc

    def load_json(self, path: Path) -> list[RecordedEvent]:
        try:
            data: Any = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            msg = f"Failed to load recorded events: {path}"
            raise RecordingError(msg) from exc

        if not isinstance(data, list):
            msg = "Recorded events JSON must be a list"
            raise RecordingError(msg)

        if not all(isinstance(item, dict) for item in data):
            msg = "Each recorded event must be a JSON object"
            raise RecordingError(msg)

        return self.collect(data)
