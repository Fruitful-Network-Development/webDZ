from __future__ import annotations

import json
import re
from pathlib import Path

from .html_utils import escape, external_link_attrs, rel_asset, render_inline_markdown, slugify


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
    if value.startswith(("[", "{", '"')) and value.endswith(("]", "}", '"')):
        return json.loads(value)
    return value


def markdown_to_html(markdown: str) -> str:
    lines = markdown.strip().splitlines()
    blocks: list[str] = []
    index = 0

    while index < len(lines):
        raw_line = lines[index].rstrip()
        stripped = raw_line.strip()

        if not stripped:
            index += 1
            continue

        if re.fullmatch(r"-{3,}", stripped):
            blocks.append("<hr>")
            index += 1
            continue

        if stripped.startswith("### "):
            blocks.append(f"<h3>{render_inline_markdown(stripped[4:])}</h3>")
            index += 1
            continue

        if stripped.startswith("## "):
            blocks.append(f"<h2>{render_inline_markdown(stripped[3:])}</h2>")
            index += 1
            continue

        if stripped.startswith("# "):
            blocks.append(f"<h1>{render_inline_markdown(stripped[2:])}</h1>")
            index += 1
            continue

        if stripped.startswith("> "):
            quote_lines = []
            while index < len(lines) and lines[index].strip().startswith("> "):
                quote_lines.append(lines[index].strip()[2:].strip())
                index += 1
            quote_html = "".join(f"<p>{render_inline_markdown(line)}</p>" for line in quote_lines if line)
            blocks.append(f"<blockquote>{quote_html}</blockquote>")
            continue

        if re.match(r"^\d+\.\s+", stripped):
            items = []
            while index < len(lines) and re.match(r"^\d+\.\s+", lines[index].strip()):
                items.append(re.sub(r"^\d+\.\s+", "", lines[index].strip()))
                index += 1
            blocks.append(
                "<ol>"
                + "".join(f"<li>{render_inline_markdown(item)}</li>" for item in items)
                + "</ol>"
            )
            continue

        if stripped.startswith("- "):
            items = []
            while index < len(lines) and lines[index].strip().startswith("- "):
                items.append(lines[index].strip()[2:].strip())
                index += 1
            blocks.append(
                "<ul>"
                + "".join(f"<li>{render_inline_markdown(item)}</li>" for item in items)
                + "</ul>"
            )
            continue

        image_match = re.match(r"^!\[([^\]]*)\]\(([^)]+)\)$", stripped)
        if image_match:
            alt_text = image_match.group(1).strip()
            source = image_match.group(2).strip()
            resolved = rel_asset(source) if source.startswith("/") else source
            blocks.append(
                '<figure class="figure">'
                f'<img class="figure__img" src="{escape(resolved)}" alt="{escape(alt_text)}">'
                f'{f"<figcaption class=\"figure__cap\">{escape(alt_text)}</figcaption>" if alt_text else ""}'
                "</figure>"
            )
            index += 1
            continue

        paragraph_lines = [stripped]
        index += 1
        while index < len(lines):
            candidate = lines[index].strip()
            if not candidate:
                break
            if (
                candidate.startswith(("# ", "## ", "### ", "> ", "- "))
                or re.match(r"^\d+\.\s+", candidate)
                or re.fullmatch(r"-{3,}", candidate)
                or re.match(r"^!\[([^\]]*)\]\(([^)]+)\)$", candidate)
            ):
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
    document.setdefault("slug", slugify(path.stem))
    return document


def load_collection(manifest: dict[str, object], frontend_root: Path, collection_key: str) -> object:
    collection = manifest["collections"][collection_key]
    collection_type = collection.get("type")

    if collection_type == "markdown_directory":
        directory = frontend_root / collection["directory"]
        items = [load_markdown_document(frontend_root, str(path.relative_to(frontend_root))) for path in sorted(directory.glob(collection.get("pattern", "*.md")))]
        sort_key = collection.get("sort_by")
        if sort_key:
            items.sort(key=lambda item: str(item.get(sort_key, "")), reverse=collection.get("sort_order", "asc") == "desc")
        return items

    if collection_type == "markdown_documents":
        documents = []
        for item in collection["items"]:
            document = load_markdown_document(frontend_root, item["source"])
            for key, value in item.items():
                if key != "source":
                    document[key] = value
            documents.append(document)
        return documents

    if collection_type == "json_file":
        return json.loads((frontend_root / collection["source"]).read_text())

    raise ValueError(f"Unsupported collection type for {collection_key}: {collection_type}")


def load_fragment(frontend_root: Path, source_path: str) -> str:
    return (frontend_root / source_path).read_text().strip()

