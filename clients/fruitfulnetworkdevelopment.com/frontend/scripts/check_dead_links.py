#!/usr/bin/env python3
"""Validate outbound references in assets/docs/citations/references.json."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

TIMEOUT_SECONDS = 12


def check_url(url: str) -> tuple[bool, int | None, str]:
    for method in ("HEAD", "GET"):
        req = Request(url, method=method, headers={"User-Agent": "FND-Link-Validator/1.0"})
        try:
            with urlopen(req, timeout=TIMEOUT_SECONDS) as res:
                return True, res.status, method
        except HTTPError as err:
            if method == "HEAD" and err.code in {403, 405, 429}:
                continue
            return False, err.code, method
        except URLError as err:
            if method == "HEAD":
                continue
            return False, None, f"{method}:{err.reason}"
    return False, None, "unknown"


def main() -> int:
    base = Path(__file__).resolve().parents[1]
    refs_path = base / "assets" / "docs" / "citations" / "references.json"

    payload = json.loads(refs_path.read_text())
    failures: list[str] = []

    for source in payload.get("sources", []):
        ok, status, method = check_url(source["url"])
        if ok:
            print(f"OK   [{status}] ({method}) {source['id']} -> {source['url']}")
        else:
            failures.append(f"FAIL [{status}] ({method}) {source['id']} -> {source['url']}")

    for failure in failures:
        print(failure, file=sys.stderr)

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
