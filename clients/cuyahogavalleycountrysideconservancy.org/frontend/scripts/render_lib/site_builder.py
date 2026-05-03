from __future__ import annotations

import sys
from pathlib import Path

from .content_loader import load_manifest
from .shell import render_document

SUPPORTED_SCHEMAS = {"webdz.site_content.v2", "webdz.site_content.v3", "webdz.site_content.v4"}


def build_site(frontend_root: Path, manifest_relative_path: str = "assets/docs/manifest.json") -> None:
    manifest_path = frontend_root / manifest_relative_path
    manifest = load_manifest(manifest_path)
    schema = manifest.get("schema", "unknown")
    if schema not in SUPPORTED_SCHEMAS:
        print(f"Warning: manifest schema '{schema}' is not in supported list", file=sys.stderr)
    for page_key, page in manifest["pages"].items():
        output_path = frontend_root / page["file"]
        output_path.write_text(render_document(manifest, page_key, page, frontend_root))
        print(f"rendered {output_path.relative_to(frontend_root)}")
