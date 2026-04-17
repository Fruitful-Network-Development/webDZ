from __future__ import annotations

import json
from datetime import UTC, date, datetime
from pathlib import Path

from .article_machine_records import generate_machine_records
from .content_loader import load_manifest
from .shell import render_document


def _page_path_from_file(file_path: str) -> str:
    normalized = file_path.strip("/")
    return "/" if normalized == "index.html" else f"/{normalized}"


def _build_machine_page_manifest(manifest: dict[str, object]) -> dict[str, object]:
    pages = manifest.get("pages", {})
    machine = manifest.get("machine") or manifest.get("machine_surfaces") or {}
    if not isinstance(pages, dict) or not isinstance(machine, dict):
        return {}

    inpage = machine.get("inpage", {})
    machine_pages = machine.get("pages", {})
    endpoint_maps = machine.get("endpoint_maps", {})
    blocks = inpage.get("blocks", []) if isinstance(inpage, dict) else []
    endpoints = machine_pages.get("endpoints", []) if isinstance(machine_pages, dict) else []
    inpage_root = inpage.get("root") if isinstance(inpage, dict) else None
    pages_root = machine_pages.get("root") if isinstance(machine_pages, dict) else None

    page_entries = []
    for page_key, page in pages.items():
        if not isinstance(page, dict):
            continue
        page_file = page.get("file")
        if not isinstance(page_file, str):
            continue
        page_path = _page_path_from_file(page_file)
        matched_blocks = []
        for block in blocks if isinstance(blocks, list) else []:
            if not isinstance(block, dict):
                continue
            if block.get("page_key") not in {None, page_key}:
                continue
            if block.get("page_key") is None and block.get("page") not in {None, page_path}:
                continue
            matched_blocks.append(
                {
                    "id": block.get("id"),
                    "source": block.get("source"),
                    "source_artifact": (
                        f"{inpage_root}/{block.get('source')}" if isinstance(inpage_root, str) else block.get("source")
                    ),
                    "injection_pattern": block.get("injection_pattern"),
                }
            )

        endpoint_entries = []
        for endpoint in endpoints if isinstance(endpoints, list) else []:
            if not isinstance(endpoint, dict):
                continue
            endpoint_entries.append(
                {
                    "rel": endpoint.get("rel"),
                    "href": endpoint.get("href"),
                    "format": endpoint.get("format"),
                    "source_artifact": endpoint.get("source_artifact"),
                    "root": pages_root,
                }
            )

        page_entries.append(
            {
                "page_key": page_key,
                "page": page_path,
                "title": page.get("title", ""),
                "machine_inpage_blocks": matched_blocks,
                "machine_page_links": endpoint_entries,
            }
        )

    return {
        "schema_identifier": "webdz.machine_pages_manifest.v1",
        "generated_from": "assets/docs/manifest.json",
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "pages": page_entries,
        "endpoint_maps": endpoint_maps if isinstance(endpoint_maps, dict) else {},
    }


def _write_machine_derivatives(frontend_root: Path, manifest: dict[str, object]) -> None:
    machine_manifest = _build_machine_page_manifest(manifest)
    if not machine_manifest:
        return

    machine = manifest.get("machine") or manifest.get("machine_surfaces") or {}
    if not isinstance(machine, dict):
        return
    endpoint_maps = machine.get("endpoint_maps", {})
    if not isinstance(endpoint_maps, dict):
        return

    page_manifest_href = endpoint_maps.get("page_manifest")
    machine_index_href = endpoint_maps.get("machine_index")
    if isinstance(page_manifest_href, str):
        page_manifest_path = frontend_root / page_manifest_href.lstrip("/")
        page_manifest_path.write_text(json.dumps(machine_manifest, indent=2) + "\n")
        print(f"rendered {page_manifest_path.relative_to(frontend_root)}")

    if isinstance(machine_index_href, str):
        machine_pages = machine.get("pages", {})
        endpoints = machine_pages.get("endpoints", []) if isinstance(machine_pages, dict) else []
        machine_index = {
            "version": "1.0",
            "updated_at": date.today().isoformat(),
            "site": "https://fruitfulnetworkdevelopment.com",
            "pages": endpoints if isinstance(endpoints, list) else [],
        }
        machine_index_path = frontend_root / machine_index_href.lstrip("/")
        machine_index_path.write_text(json.dumps(machine_index, indent=2) + "\n")
        print(f"rendered {machine_index_path.relative_to(frontend_root)}")


def build_site(frontend_root: Path, manifest_relative_path: str = "assets/docs/manifest.json") -> None:
    manifest_path = frontend_root / manifest_relative_path
    manifest = load_manifest(manifest_path)
    for page_key, page in manifest["pages"].items():
        output_path = frontend_root / page["file"]
        output_path.write_text(render_document(manifest, page_key, page, frontend_root))
        print(f"rendered {output_path.relative_to(frontend_root)}")

    generate_machine_records(frontend_root, manifest)
    print("rendered machine article and citation records")
    _write_machine_derivatives(frontend_root, manifest)
