from __future__ import annotations

import json
from pathlib import Path


def load_manifest(manifest_path: Path) -> dict[str, object]:
    return json.loads(manifest_path.read_text())
