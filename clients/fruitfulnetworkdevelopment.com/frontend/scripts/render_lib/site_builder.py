from __future__ import annotations

from pathlib import Path

from .article_machine_records import generate_machine_records
from .content_loader import load_manifest
from .shell import render_document


def build_site(frontend_root: Path, manifest_relative_path: str = "assets/docs/manifest.json") -> None:
    manifest_path = frontend_root / manifest_relative_path
    manifest = load_manifest(manifest_path)
    for page_key, page in manifest["pages"].items():
        output_path = frontend_root / page["file"]
        output_path.write_text(render_document(manifest, page_key, page, frontend_root))
        print(f"rendered {output_path.relative_to(frontend_root)}")

    generate_machine_records(frontend_root, manifest)
    print("rendered machine article and citation records")
