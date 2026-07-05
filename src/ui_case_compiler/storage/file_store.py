from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ui_case_compiler.errors import StorageError


class FileStore:
    """Small JSON file store used by the MVP."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def read_json(self, path: Path) -> dict[str, Any]:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            msg = f"Failed to read JSON file: {path}"
            raise StorageError(msg) from exc
        if not isinstance(data, dict):
            msg = f"JSON file must contain an object: {path}"
            raise StorageError(msg)
        return data

    def write_json(self, path: Path, data: dict[str, Any]) -> None:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                json.dumps(data, ensure_ascii=False, indent=2, default=str),
                encoding="utf-8",
            )
        except OSError as exc:
            msg = f"Failed to write JSON file: {path}"
            raise StorageError(msg) from exc
