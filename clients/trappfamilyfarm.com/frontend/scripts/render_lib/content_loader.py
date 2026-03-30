from __future__ import annotations

import json
import re
from pathlib import Path

from .html_utils import render_inline_markdown


def load_manifest(manifest_path: Path) -> dict[str, object]:
    return json.loads(manifest_path.read_text())


def parse_front_matter(source_text: str) -> tuple[dict[str, object], str]:
    if not source_text.startswith("---\n"):
        return {}, source_text

    lines = source_text.splitlines()
    front_matter_lines: list[str] = []
    body_start = None

    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            body_start = index + 1
            break
        front_matter_lines.append(line)

    if body_start is None:
        return {}, source_text

    metadata: dict[str, object] = {}
    for line in front_matter_lines:
        if not line.strip() or ":" not in line:
            continue
        key, value = line.split(":", 1)
        metadata[key.strip()] = parse_front_matter_value(value.strip())

    return metadata, "\n".join(lines[body_start:]).strip()


def parse_front_matter_value(value: str) -> object:
    if value in {"true", "false"}:
        return value == "true"
    if value.startswith("[") or value.startswith("{"):
        return json.loads(value)
    if value.startswith('"') and value.endswith('"'):
        return json.loads(value)
    return value


def markdown_to_html(markdown: str) -> str:
    lines = markdown.strip().splitlines()
    blocks: list[str] = []
    index = 0

    while index < len(lines):
        line = lines[index].rstrip()
        stripped = line.strip()

        if not stripped:
            index += 1
            continue

        if re.fullmatch(r"-{3,}", stripped):
            blocks.append("<hr>")
            index += 1
            continue

        if stripped.startswith("## "):
            blocks.append(f"<h2>{render_inline_markdown(stripped[3:])}</h2>")
            index += 1
            continue

        if stripped.startswith("### "):
            blocks.append(f"<h3>{render_inline_markdown(stripped[4:])}</h3>")
            index += 1
            continue

        if stripped.startswith("- "):
            items = []
            while index < len(lines) and lines[index].strip().startswith("- "):
                items.append(lines[index].strip()[2:].rstrip())
                index += 1
            blocks.append(
                "<ul>"
                + "".join(f"<li>{render_inline_markdown(item)}</li>" for item in items)
                + "</ul>"
            )
            continue

        paragraph_lines = [stripped]
        index += 1
        while index < len(lines):
            candidate = lines[index].strip()
            if not candidate:
                break
            if candidate.startswith(("## ", "### ", "- ")) or re.fullmatch(r"-{3,}", candidate):
                break
            paragraph_lines.append(candidate)
            index += 1
        blocks.append(f"<p>{render_inline_markdown(' '.join(paragraph_lines))}</p>")

    return "".join(blocks)


def load_markdown_document(frontend_root: Path, source_path: str) -> dict[str, object]:
    path = frontend_root / source_path
    metadata, body_markdown = parse_front_matter(path.read_text())
    document = dict(metadata)
    document["source"] = source_path
    document["body_markdown"] = body_markdown
    document["body_html"] = markdown_to_html(body_markdown)
    return document


def load_collection(manifest: dict[str, object], frontend_root: Path, collection_key: str) -> list[dict[str, object]]:
    collection = manifest["collections"][collection_key]
    if collection.get("type") != "markdown_documents":
        raise ValueError(f"Unsupported collection type for {collection_key}: {collection.get('type')}")
    items = []
    for item in collection["items"]:
        document = load_markdown_document(frontend_root, item["source"])
        for key, value in item.items():
            if key != "source":
                document[key] = value
        items.append(document)
    return items
