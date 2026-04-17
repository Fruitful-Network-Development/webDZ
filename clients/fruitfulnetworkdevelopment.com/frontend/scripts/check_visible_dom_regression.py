#!/usr/bin/env python3
"""Static regression check for user-visible DOM regions.

Compares checked-in pages against freshly rendered output from the manifest and
fails if key visible slices change unexpectedly.
"""

from __future__ import annotations

import difflib
import json
import re
from html import unescape
from pathlib import Path

from render_lib.content_loader import load_manifest
from render_lib.shell import render_document

ROOT = Path(__file__).resolve().parents[1]
MAIN_REGION_PATTERN = re.compile(r"<main\\b[^>]*>(.*?)</main>", re.DOTALL | re.IGNORECASE)
FOOTER_REGION_PATTERN = re.compile(r"<footer\\b[^>]*>(.*?)</footer>", re.DOTALL | re.IGNORECASE)
NAV_REGION_PATTERN = re.compile(r"<nav\\b[^>]*class=\"[^\"]*topbar__nav[^\"]*\"[^>]*>(.*?)</nav>", re.DOTALL | re.IGNORECASE)
ANCHOR_TEXT_PATTERN = re.compile(r"<a\\b[^>]*>(.*?)</a>", re.DOTALL | re.IGNORECASE)
HEADING_PATTERN = re.compile(r"<h([1-3])\\b[^>]*>(.*?)</h\\1>", re.DOTALL | re.IGNORECASE)
CTA_PATTERN = re.compile(
    r"<(a|button)\\b(?=[^>]*(?:class=\"[^\"]*(?:cta|button)[^\"]*\"|data-cta=))[\\s\\S]*?>(.*?)</\\1>",
    re.DOTALL | re.IGNORECASE,
)
FOOTER_BLOCK_PATTERN = re.compile(r"<section\\b[^>]*>(.*?)</section>", re.DOTALL | re.IGNORECASE)
PARAGRAPH_PATTERN = re.compile(r"<p\\b[^>]*>(.*?)</p>", re.DOTALL | re.IGNORECASE)
TAG_PATTERN = re.compile(r"<[^>]+>")
SPACE_PATTERN = re.compile(r"\\s+")


def normalize_text(value: str) -> str:
    without_tags = TAG_PATTERN.sub(" ", value)
    collapsed = SPACE_PATTERN.sub(" ", unescape(without_tags)).strip()
    return collapsed


def extract_region(pattern: re.Pattern[str], html: str) -> str:
    match = pattern.search(html)
    return match.group(1) if match else ""


def extract_signature(html: str) -> dict[str, object]:
    nav_html = extract_region(NAV_REGION_PATTERN, html)
    main_html = extract_region(MAIN_REGION_PATTERN, html)
    footer_html = extract_region(FOOTER_REGION_PATTERN, html)

    nav_labels = [normalize_text(label) for label in ANCHOR_TEXT_PATTERN.findall(nav_html)]
    section_headings = [normalize_text(text) for _, text in HEADING_PATTERN.findall(main_html)]
    cta_text = [normalize_text(text) for _, text in CTA_PATTERN.findall(main_html)]

    footer_blocks = []
    for block in FOOTER_BLOCK_PATTERN.findall(footer_html):
        heading_match = re.search(r"<h2\\b[^>]*>(.*?)</h2>", block, re.DOTALL | re.IGNORECASE)
        heading = normalize_text(heading_match.group(1)) if heading_match else ""
        lines = [normalize_text(line) for line in PARAGRAPH_PATTERN.findall(block)]
        footer_blocks.append({"heading": heading, "lines": lines})

    return {
        "header_nav_labels": nav_labels,
        "section_headings": section_headings,
        "cta_text": cta_text,
        "footer_blocks": footer_blocks,
    }


def check_page(manifest: dict[str, object], page_key: str, page: dict[str, object]) -> list[str]:
    output_path = ROOT / page["file"]
    if not output_path.exists():
        return [f"{page['file']}: missing target file on disk"]

    pre_html = output_path.read_text(encoding="utf-8")
    post_html = render_document(manifest, page_key, page, ROOT)

    pre_signature = extract_signature(pre_html)
    post_signature = extract_signature(post_html)

    if pre_signature == post_signature:
        return []

    before = json.dumps(pre_signature, indent=2, sort_keys=True).splitlines()
    after = json.dumps(post_signature, indent=2, sort_keys=True).splitlines()
    diff = "\n".join(
        difflib.unified_diff(before, after, fromfile=f"pre:{page['file']}", tofile=f"post:{page['file']}", lineterm="")
    )
    return [f"{page['file']}: visible DOM signature changed\n{diff}"]


def main() -> None:
    manifest = load_manifest(ROOT / "assets/docs/manifest.json")
    failures: list[str] = []

    for page_key, page in manifest["pages"].items():
        if page["template"] in {"verbatim_fragment", "verbatim_document"}:
            continue
        failures.extend(check_page(manifest, page_key, page))

    if failures:
        print("Visible DOM regression check failed:\n")
        print("\n\n".join(failures))
        raise SystemExit(1)

    print("Visible DOM regression check passed.")


if __name__ == "__main__":
    main()
