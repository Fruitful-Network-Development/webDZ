#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
SHARED_CORE = ROOT / "clients" / "_shared" / "site-core" / "css" / "core.css"

TARGETS = [
    ROOT / "clients" / "fruitfulnetworkdevelopment.com" / "frontend" / "css" / "shared-core.css",
    ROOT / "clients" / "trappfamilyfarm.com" / "frontend" / "css" / "shared-core.css",
    ROOT / "clients" / "cuyahogavalleycountrysideconservancy.org" / "frontend" / "CSS" / "shared-core.css",
]

HEADER = "/* synced from clients/_shared/site-core/css/core.css */\n"


def main() -> int:
    payload = SHARED_CORE.read_text(encoding="utf-8")
    for target in TARGETS:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(HEADER + payload, encoding="utf-8")
        print(f"synced {target.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
