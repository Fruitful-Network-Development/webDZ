#!/usr/bin/env python3
"""Remove demo JSON data from Postgres safely and idempotently.

Usage:
  python srv/compose/platform/flask-bff/scripts/beta_cleanup_demo_data.py \
    --data-dir srv/compose/platform/flask-bff/demo-data

Environment variables:
  DATABASE_URL or PGHOST/PGPORT/PGUSER/PGPASSWORD/PGDATABASE
  DEMO_DATA_TABLE (default: demo_contract_payloads)
  DEMO_DATA_CONTRACT_COLUMN (default: contract_name)
  DEMO_DATA_SOURCE_COLUMN (default: source_file)
  DEMO_DATA_DEFAULT_CONTRACT (optional override for unmapped files)
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import psycopg2

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from demo_data_common import iter_demo_files, resolve_contract  # noqa: E402


def _get_connection():
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        return psycopg2.connect(database_url)
    return psycopg2.connect(
        host=os.getenv("PGHOST"),
        port=os.getenv("PGPORT"),
        user=os.getenv("PGUSER"),
        password=os.getenv("PGPASSWORD"),
        dbname=os.getenv("PGDATABASE"),
    )


def _get_table_settings() -> dict[str, str]:
    return {
        "table": os.getenv("DEMO_DATA_TABLE", "demo_contract_payloads"),
        "contract_column": os.getenv("DEMO_DATA_CONTRACT_COLUMN", "contract_name"),
        "source_column": os.getenv("DEMO_DATA_SOURCE_COLUMN", "source_file"),
    }


def cleanup_demo_data(
    data_dir: Path,
    default_contract: str | None,
    dry_run: bool,
    glob_pattern: str,
) -> int:
    settings = _get_table_settings()
    table = settings["table"]
    contract_column = settings["contract_column"]
    source_column = settings["source_column"]

    files = list(iter_demo_files(data_dir, glob_pattern))

    if dry_run:
        for path in files:
            contract_name = resolve_contract(path.name, default_contract)
            print(f"[dry-run] Would delete {path.name} -> {contract_name}")
        return 0

    deleted_rows = 0
    with _get_connection() as connection:
        with connection.cursor() as cursor:
            for path in files:
                contract_name = resolve_contract(path.name, default_contract)
                cursor.execute(
                    f"DELETE FROM {table} WHERE {contract_column} = %s "
                    f"AND {source_column} = %s",
                    (contract_name, path.name),
                )
                deleted_rows += cursor.rowcount
        connection.commit()

    return deleted_rows


def main() -> int:
    parser = argparse.ArgumentParser(description="Remove demo JSON data from Postgres.")
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "demo-data",
        help="Path to the demo-data directory.",
    )
    parser.add_argument(
        "--glob",
        default="*.json",
        help="File glob to select demo data files.",
    )
    parser.add_argument(
        "--default-contract",
        default=os.getenv("DEMO_DATA_DEFAULT_CONTRACT"),
        help="Contract placeholder used when no mapping is found.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print actions without DB writes.")
    args = parser.parse_args()

    if not args.data_dir.exists():
        print(f"Demo data directory not found: {args.data_dir}", file=sys.stderr)
        return 1

    deleted_rows = cleanup_demo_data(
        data_dir=args.data_dir,
        default_contract=args.default_contract,
        dry_run=args.dry_run,
        glob_pattern=args.glob,
    )
    if not args.dry_run:
        print(f"Deleted {deleted_rows} rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
