#!/usr/bin/env python3
"""Lint machine-oriented LLM docs for required sections and metadata."""

from __future__ import annotations

import argparse
import pathlib
import re
import sys

REQUIRED_HEADINGS = [
    "## Document Metadata",
    "## Core Claims",
    "## Company Facts",
    "## Milestones And Future Roadmap",
    "## Accolades And Proof Points",
    "## Citations And External References",
]

REQUIRED_METADATA_FIELDS = ["version:", "last_updated:"]


def lint_file(path: pathlib.Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    errors: list[str] = []

    for field in REQUIRED_METADATA_FIELDS:
        if field not in text:
            errors.append(f"missing metadata field '{field}'")

    for heading in REQUIRED_HEADINGS:
        if heading not in text:
            errors.append(f"missing required heading '{heading}'")

    references = re.findall(r"^\d+\.\s+https?://\S+", text, flags=re.MULTILINE)
    if not references:
        errors.append("missing numbered external references under 'Citations And External References'")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Lint LLM optimization docs.")
    parser.add_argument(
        "files",
        nargs="+",
        help="One or more markdown source docs to lint.",
    )
    args = parser.parse_args()

    has_errors = False
    for file_name in args.files:
        path = pathlib.Path(file_name)
        if not path.exists():
            print(f"ERROR: file not found: {path}")
            has_errors = True
            continue
        errors = lint_file(path)
        if errors:
            has_errors = True
            print(f"FAIL: {path}")
            for err in errors:
                print(f"  - {err}")
        else:
            print(f"PASS: {path}")

    return 1 if has_errors else 0


if __name__ == "__main__":
    sys.exit(main())
