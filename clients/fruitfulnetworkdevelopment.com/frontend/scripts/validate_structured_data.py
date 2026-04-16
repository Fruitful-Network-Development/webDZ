#!/usr/bin/env python3
"""Pre-release structured data checks for FND frontend pages."""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "assets/seo/structured-data.manifest.json"

SCRIPT_PATTERN = re.compile(
    r'<script type="application/ld\+json" data-structured-data="page">\s*(\{.*?\})\s*</script>',
    re.DOTALL,
)
CANONICAL_PATTERN = re.compile(r'<link rel="canonical" href="(https://[^\"]+)"\s*/?>')

REQUIRED_MANIFEST_SECTIONS = ["organization", "person", "services", "docs", "pages"]
REQUIRED_DOC_SECTIONS = ["articles", "reports", "dataset"]
REQUIRED_GRAPH_TYPES = {"Organization", "WebSite", "BreadcrumbList"}


def load_manifest() -> dict:
    payload = json.loads(MANIFEST.read_text(encoding="utf-8"))
    for section in REQUIRED_MANIFEST_SECTIONS:
        if section not in payload:
            raise SystemExit(f"Missing required manifest section: {section}")
    for section in REQUIRED_DOC_SECTIONS:
        if section not in payload["docs"]:
            raise SystemExit(f"Missing docs subsection: docs.{section}")
    return payload


def read_page(path: Path) -> tuple[str, dict]:
    html = path.read_text(encoding="utf-8")
    json_match = SCRIPT_PATTERN.search(html)
    if not json_match:
        raise SystemExit(f"Missing page JSON-LD block: {path}")
    payload = json.loads(json_match.group(1))
    canonical_match = CANONICAL_PATTERN.search(html)
    if not canonical_match:
        raise SystemExit(f"Missing absolute canonical URL: {path}")
    if not canonical_match.group(1).startswith("https://fruitfulnetworkdevelopment.com"):
        raise SystemExit(f"Canonical URL is not on primary domain: {path}")
    return html, payload


def validate_page(path: Path, page_cfg: dict) -> None:
    _, payload = read_page(path)
    graph = payload.get("@graph", [])
    graph_types = {item.get("@type") for item in graph if isinstance(item, dict)}
    missing = REQUIRED_GRAPH_TYPES - graph_types
    if missing:
        raise SystemExit(f"{path} is missing required graph types: {sorted(missing)}")

    if page_cfg.get("includeServices") and "Service" not in graph_types:
        raise SystemExit(f"{path} should include Service entities")
    if page_cfg.get("includePerson") and "Person" not in graph_types:
        raise SystemExit(f"{path} should include Person entity")
    if page_cfg.get("includeDocs"):
        needed = {"Dataset", "Article", "ScholarlyArticle", "Report"}
        if not needed.issubset(graph_types):
            raise SystemExit(f"{path} missing docs-backed entities: {sorted(needed - graph_types)}")
    if page_cfg.get("includeReport") and "Report" not in graph_types:
        raise SystemExit(f"{path} should include Report entity")


def main() -> None:
    manifest = load_manifest()
    for page_path, cfg in manifest["pages"].items():
        page_file = ROOT / page_path.lstrip("/")
        if page_file.is_file():
            validate_page(page_file, cfg)
    print("Structured-data validation passed.")


if __name__ == "__main__":
    main()
