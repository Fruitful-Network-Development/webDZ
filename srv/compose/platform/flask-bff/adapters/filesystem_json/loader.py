"""Filesystem loader for JSON data environment."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

from core.data_env.errors import DataEnvFileError


def load_resources(root_path: Path, *, ignore_files: Optional[Iterable[str]] = None) -> Dict[str, Any]:
    if not root_path.exists() or not root_path.is_dir():
        raise DataEnvFileError(str(root_path), "data env root not found or not a directory")

    ignore = {name for name in (ignore_files or [])}
    resources: Dict[str, Any] = {}
    for entry in sorted(root_path.iterdir()):
        if not entry.is_file():
            continue
        if entry.suffix.lower() != ".json":
            continue
        if entry.name in ignore:
            continue
        try:
            raw = json.loads(entry.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise DataEnvFileError(str(entry), f"invalid JSON: {exc.msg}") from exc
        if not isinstance(raw, dict):
            raise DataEnvFileError(str(entry), "top-level JSON must be an object")
        for resource_id, payload in raw.items():
            if resource_id in resources:
                raise DataEnvFileError(
                    str(entry),
                    f"duplicate resource_id '{resource_id}'",
                )
            resources[resource_id] = payload
    return resources

