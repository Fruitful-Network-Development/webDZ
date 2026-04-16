#!/usr/bin/env python3
"""Render per-page JSON-LD blocks and canonical tags from manifest."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "assets/seo/structured-data.manifest.json"


def absolute_url(base: str, path: str) -> str:
    if path.startswith("http://") or path.startswith("https://"):
        return path
    return f"{base.rstrip('/')}{path}"


def build_breadcrumb(base_url: str, items: list[dict]) -> dict:
    return {
        "@type": "BreadcrumbList",
        "itemListElement": [
            {
                "@type": "ListItem",
                "position": index + 1,
                "name": item["name"],
                "item": absolute_url(base_url, item["path"]),
            }
            for index, item in enumerate(items)
        ],
    }


def render_page(html_path: Path, manifest: dict, page_path: str, cfg: dict) -> None:
    text = html_path.read_text(encoding="utf-8")

    canonical_path = "/" if page_path == "/index.html" else page_path
    canonical_url = absolute_url(manifest["baseUrl"], canonical_path)
    canonical_line = f'  <link rel="canonical" href="{canonical_url}" />\n'

    if 'rel="canonical"' in text:
        import re

        text = re.sub(r"\s*<link rel=\"canonical\" href=\"[^\"]*\"\s*/>\n", canonical_line, text, count=1)
    else:
        text = text.replace("</head>\n", canonical_line + "</head>\n", 1)

    graph = [manifest["organization"], manifest["website"], build_breadcrumb(manifest["baseUrl"], cfg.get("breadcrumb", []))]
    if cfg.get("includeServices"):
        graph.extend(manifest.get("services", []))
    if cfg.get("includePerson"):
        graph.append(manifest["person"])
    if cfg.get("includeDocs"):
        graph.append(manifest["docs"]["dataset"])
        graph.extend(manifest["docs"].get("articles", []))
        graph.extend(manifest["docs"].get("reports", []))
    if cfg.get("includeReport"):
        graph.extend(manifest["docs"].get("reports", []))

    payload = {
        "@context": "https://schema.org",
        "@graph": graph,
    }
    jsonld = json.dumps(payload, indent=2)
    block = (
        "  <script type=\"application/ld+json\" data-structured-data=\"page\">\n"
        f"{jsonld}\n"
        "  </script>\n"
    )

    start_marker = "  <script type=\"application/ld+json\" data-structured-data=\"page\">"
    if start_marker in text:
        before = text.split(start_marker, 1)[0]
        after = text.split("  </script>\n", 1)[1]
        text = before + block + after
    else:
        text = text.replace("</head>\n", block + "</head>\n", 1)

    text = text.replace('  <script src="./js/structured-data.js" defer></script>\n', "")
    text = text.replace('  <script src="../js/structured-data.js" defer></script>\n', "")

    html_path.write_text(text, encoding="utf-8")


def main() -> None:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    for page_path, cfg in manifest["pages"].items():
        file_path = ROOT / page_path.lstrip("/")
        if file_path.is_file():
            render_page(file_path, manifest, page_path, cfg)


if __name__ == "__main__":
    main()
