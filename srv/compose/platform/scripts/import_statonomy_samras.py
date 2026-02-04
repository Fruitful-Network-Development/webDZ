#!/usr/bin/env python3
"""Import the statonomy SAMRAS domain into platform_db."""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

APP_DIR = Path(__file__).resolve().parents[1] / "flask-bff"
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from utils.statonomy_importer import (  # type: ignore  # noqa: E402
    DEFAULT_INPUT_PATH,
    import_statonomy_samras,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Import statonomy SAMRAS domain.")
    parser.add_argument(
        "--input",
        default=DEFAULT_INPUT_PATH,
        help=f"Path to statonomy JSON (default: {DEFAULT_INPUT_PATH})",
    )
    args = parser.parse_args()

    db_url = os.getenv("PLATFORM_DB_URL")
    if not db_url:
        raise RuntimeError("Missing PLATFORM_DB_URL for statonomy import")

    result = import_statonomy_samras(db_url=db_url, input_path=args.input)
    print(f"Imported statonomy nodes: {result['node_count']}")
    print(f"Statonomy table: {result['table_name']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
