#!/usr/bin/env python3
"""Remove demo JSON data from Postgres safely and idempotently.

Usage:
  python srv/compose/platform/flask-bff/scripts/beta_cleanup_demo_data.py \
    --data-dir srv/compose/platform/flask-bff/demo-data

Environment variables:
  DATABASE_URL or PGHOST/PGPORT/PGUSER/PGPASSWORD/PGDATABASE
  DEMO_DATA_TABLE (default: platform.portal_contract_payloads)
  DEMO_DATA_CONTRACT_COLUMN (default: contract_name)
  DEMO_DATA_SOURCE_COLUMN (default: source_file)
  DEMO_DATA_INGEST_COLUMN (default: ingest_source)
  DEMO_DATA_INGEST_SOURCE (default: demo-data)
  DEMO_DATA_DEFAULT_CONTRACT (optional override for unmapped files)
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

import psycopg2
from psycopg2 import sql

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from demo_data_common import DemoDataError, iter_demo_files, resolve_contract  # noqa: E402


def _get_connection():
    database_url = os.getenv("DATABASE_URL") or os.getenv("PLATFORM_DB_URL")
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
        "table": os.getenv("DEMO_DATA_TABLE", "platform.portal_contract_payloads"),
        "contract_column": os.getenv("DEMO_DATA_CONTRACT_COLUMN", "contract_name"),
        "source_column": os.getenv("DEMO_DATA_SOURCE_COLUMN", "source_file"),
        "ingest_column": os.getenv("DEMO_DATA_INGEST_COLUMN", "ingest_source"),
        "ingest_source": os.getenv("DEMO_DATA_INGEST_SOURCE", "demo-data"),
    }


def _validate_identifier(value: str) -> None:
    if not value or not value.replace("_", "").isalnum() or value[0].isdigit():
        raise ValueError(f"Invalid identifier: {value}")


def _split_table_name(table_name: str) -> tuple[str | None, str]:
    parts = table_name.split(".")
    if len(parts) == 1:
        _validate_identifier(parts[0])
        return None, parts[0]
    if len(parts) == 2:
        _validate_identifier(parts[0])
        _validate_identifier(parts[1])
        return parts[0], parts[1]
    raise ValueError(f"Invalid table name: {table_name}")


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
    ingest_column = settings["ingest_column"]
    ingest_source = settings["ingest_source"]
    for column in (contract_column, source_column, ingest_column):
        _validate_identifier(column)

    files = list(iter_demo_files(data_dir, glob_pattern))

    if dry_run:
        for path in files:
            contract_name = resolve_contract(path.name, default_contract)
            print(f"[dry-run] Would delete {path.name} -> {contract_name}")
        return 0

    deleted_rows = 0
    deleted_entries: list[dict[str, str]] = []
    deleted_mss: dict[str, set[str]] = {
        "compendium": set(),
        "anthology": set(),
        "muniment": set(),
        "taxonomy": set(),
        "msn": set(),
    }

    compendium_re = re.compile(r"^mss\\.compendium\\.(?P<msn_id>.+)\\.json$")
    anthology_re = re.compile(r"^mss\\.anthology\\.(?P<msn_id>.+)\\.json$")
    muniment_re = re.compile(r"^mss\\.muniment\\.(?P<msn_id>.+)\\.json$")
    txa_re = re.compile(r"^(?P<msn_id>.+)\\.txa\\..+\\.json$")
    msn_re = re.compile(r"^(?P<msn_id>.+)\\.msn\\..+\\.json$")
    correspondence_re = re.compile(r"^platform\\.correspondence\\.(?P<msn_id>.+)\\.json$")
    schema, table_name = _split_table_name(table)
    table_ref = sql.Identifier(table_name) if schema is None else sql.Identifier(schema, table_name)
    with _get_connection() as connection:
        with connection.cursor() as cursor:
            for path in files:
                compendium_match = compendium_re.match(path.name)
                anthology_match = anthology_re.match(path.name)
                muniment_match = muniment_re.match(path.name)
                txa_match = txa_re.match(path.name)
                msn_match = msn_re.match(path.name)
                correspondence_match = correspondence_re.match(path.name)

                if compendium_match:
                    msn_id = compendium_match.group("msn_id")
                    if msn_id not in deleted_mss["compendium"]:
                        cursor.execute(
                            "DELETE FROM mss.compendium WHERE msn_id = %s",
                            (msn_id,),
                        )
                        deleted_mss["compendium"].add(msn_id)

                if anthology_match:
                    msn_id = anthology_match.group("msn_id")
                    if msn_id not in deleted_mss["anthology"]:
                        cursor.execute(
                            "DELETE FROM mss.anthology_entry WHERE msn_id = %s",
                            (msn_id,),
                        )
                        deleted_mss["anthology"].add(msn_id)

                if muniment_match:
                    msn_id = muniment_match.group("msn_id")
                    if msn_id not in deleted_mss["muniment"]:
                        cursor.execute(
                            "DELETE FROM mss.muniment WHERE msn_id = %s",
                            (msn_id,),
                        )
                        deleted_mss["muniment"].add(msn_id)

                if txa_match:
                    source_msn_id = txa_match.group("msn_id")
                    if source_msn_id not in deleted_mss["taxonomy"]:
                        cursor.execute(
                            "DELETE FROM mss.taxonomy_local_map WHERE source_msn_id = %s",
                            (source_msn_id,),
                        )
                        deleted_mss["taxonomy"].add(source_msn_id)

                if msn_match:
                    source_msn_id = msn_match.group("msn_id")
                    if source_msn_id not in deleted_mss["msn"]:
                        cursor.execute(
                            "DELETE FROM mss.msn_local_map WHERE source_msn_id = %s",
                            (source_msn_id,),
                        )
                        deleted_mss["msn"].add(source_msn_id)

                if correspondence_match:
                    msn_id = correspondence_match.group("msn_id")
                    cursor.execute(
                        "DELETE FROM platform.correspondence WHERE msn_id = %s AND source_file = %s",
                        (msn_id, path.name),
                    )

                contract_name = resolve_contract(path.name, default_contract)
                delete_sql = sql.SQL(
                    "DELETE FROM {table} WHERE {contract} = %s AND {source} = %s AND {ingest} = %s"
                ).format(
                    table=table_ref,
                    contract=sql.Identifier(contract_column),
                    source=sql.Identifier(source_column),
                    ingest=sql.Identifier(ingest_column),
                )
                cursor.execute(delete_sql, (contract_name, path.name, ingest_source))
                deleted_rows += cursor.rowcount
                deleted_entries.append({"source_file": path.name, "contract": contract_name})
        connection.commit()

    for entry in deleted_entries:
        print(f"[deleted] {entry['source_file']} -> {entry['contract']}")

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

    try:
        deleted_rows = cleanup_demo_data(
            data_dir=args.data_dir,
            default_contract=args.default_contract,
            dry_run=args.dry_run,
            glob_pattern=args.glob,
        )
    except (DemoDataError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    if not args.dry_run:
        print(f"Deleted {deleted_rows} rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
