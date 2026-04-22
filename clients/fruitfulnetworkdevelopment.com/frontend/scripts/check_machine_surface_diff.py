#!/usr/bin/env python3
"""Machine-surface-only diff check.

Validates, in two independent buckets:
1) hidden in-page injections (`machine/inpage/*` + target pages)
2) machine page endpoints (`machine/pages/*`)
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

from render_lib.content_loader import load_manifest

ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parents[2]
SCRIPT_JSONLD_PATTERN = re.compile(r'<script\\b[^>]*type="application/ld\\+json"[^>]*>(.*?)</script>', re.DOTALL)


def changed_files() -> set[str]:
    cmd = ["git", "-C", str(REPO_ROOT), "diff", "--name-only", "--", str(ROOT.relative_to(REPO_ROOT))]
    proc = subprocess.run(cmd, check=True, capture_output=True, text=True)
    return {line.strip() for line in proc.stdout.splitlines() if line.strip()}


def normalize_json_payload(text: str) -> str:
    return json.dumps(json.loads(text), indent=2, sort_keys=True)


def validate_inpage_diff(manifest: dict[str, object], changed: set[str]) -> list[str]:
    failures: list[str] = []
    inpage_prefix = f"{ROOT.relative_to(REPO_ROOT)}/machine/inpage/"
    page_prefix = f"{ROOT.relative_to(REPO_ROOT)}/"
    changed_inpage = sorted(path for path in changed if path.startswith(inpage_prefix))

    if not changed_inpage:
        return failures

    machine = manifest.get("machine")
    if not isinstance(machine, dict):
        machine = manifest.get("machine_surfaces", {})
    if not isinstance(machine, dict):
        return failures
    inpage = machine.get("inpage", {})
    if not isinstance(inpage, dict):
        return failures
    blocks = inpage.get("blocks", [])
    if not isinstance(blocks, list):
        return failures

    for block in blocks:
        source_rel = f"{ROOT.relative_to(REPO_ROOT)}/machine/inpage/{block['source']}"
        if source_rel not in changed_inpage:
            continue

        page_rel = "index.html" if block["page"] == "/" else block["page"].lstrip("/")
        page_repo_rel = f"{page_prefix}{page_rel}"
        if page_repo_rel not in changed:
            failures.append(
                f"{source_rel} changed but target page {page_repo_rel} did not change in the same diff"
            )
            continue

        source_path = ROOT / "machine/inpage" / block["source"]
        page_path = ROOT / page_rel
        source_payload = normalize_json_payload(source_path.read_text(encoding="utf-8"))
        scripts = SCRIPT_JSONLD_PATTERN.findall(page_path.read_text(encoding="utf-8"))
        script_payloads = {normalize_json_payload(script) for script in scripts if script.strip().startswith("{")}
        if source_payload not in script_payloads:
            failures.append(f"{source_rel} payload not found in {page_repo_rel}")

    return failures


def validate_machine_page_diff(manifest: dict[str, object], changed: set[str]) -> list[str]:
    failures: list[str] = []
    pages_prefix = f"{ROOT.relative_to(REPO_ROOT)}/machine/pages/"
    changed_pages = sorted(path for path in changed if path.startswith(pages_prefix))

    if not changed_pages:
        return failures

    machine = manifest.get("machine")
    if not isinstance(machine, dict):
        machine = manifest.get("machine_surfaces", {})
    if not isinstance(machine, dict):
        return failures
    pages = machine.get("pages", {})
    if not isinstance(pages, dict):
        return failures
    endpoints = pages.get("endpoints", [])
    if not isinstance(endpoints, list):
        return failures
    declared = {endpoint.get("href") for endpoint in endpoints if isinstance(endpoint, dict) and endpoint.get("href")}

    for page_path in changed_pages:
        href = "/" + str(Path(page_path).relative_to(ROOT.relative_to(REPO_ROOT))).replace("\\", "/")
        if href not in declared:
            failures.append(f"{page_path} changed but is not declared in manifest.machine.pages.endpoints")

    return failures


def main() -> None:
    manifest = load_manifest(ROOT / "assets/docs/manifest.json")
    changed = changed_files()

    inpage_failures = validate_inpage_diff(manifest, changed)
    machine_page_failures = validate_machine_page_diff(manifest, changed)

    if inpage_failures or machine_page_failures:
        print("Machine surface diff check failed.")
        if inpage_failures:
            print("\n[hidden in-page injections]")
            print("\n".join(f"- {entry}" for entry in inpage_failures))
        if machine_page_failures:
            print("\n[machine pages]")
            print("\n".join(f"- {entry}" for entry in machine_page_failures))
        raise SystemExit(1)

    print("Machine surface diff check passed.")


if __name__ == "__main__":
    main()
