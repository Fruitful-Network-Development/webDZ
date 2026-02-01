#!/usr/bin/env python3
"""Load demo JSON data into Postgres.

Usage:
  python srv/compose/platform/flask-bff/scripts/ingest_demo_data.py \
    --data-dir srv/compose/platform/flask-bff/demo-data

Environment variables:
  DATABASE_URL or PGHOST/PGPORT/PGUSER/PGPASSWORD/PGDATABASE
  DEMO_DATA_TABLE (default: platform.portal_contract_payloads)
  DEMO_DATA_CONTRACT_COLUMN (default: contract_name)
  DEMO_DATA_SOURCE_COLUMN (default: source_file)
  DEMO_DATA_PAYLOAD_COLUMN (default: payload)
  DEMO_DATA_INGEST_COLUMN (default: ingest_source)
  DEMO_DATA_INGEST_SOURCE (default: demo-data)
  DEMO_DATA_DEFAULT_CONTRACT (optional override for unmapped files)

Notes:
  - This script expects a generic table with contract/source/payload columns.
  - Update CONTRACT_MAPPINGS in demo_data_common.py to align demo files to
    specific contract implementations.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

import psycopg2
from psycopg2 import sql
from psycopg2.extras import Json

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from demo_data_common import DemoDataError, iter_demo_files, parse_demo_payload, resolve_contract  # noqa: E402


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
        "payload_column": os.getenv("DEMO_DATA_PAYLOAD_COLUMN", "payload"),
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


def _ensure_table(connection, settings: dict[str, str]) -> None:
    schema, table_name = _split_table_name(settings["table"])
    for key in ("contract_column", "source_column", "payload_column", "ingest_column"):
        _validate_identifier(settings[key])
    table_ref = sql.Identifier(table_name) if schema is None else sql.Identifier(schema, table_name)
    create_sql = sql.SQL(
        "CREATE TABLE IF NOT EXISTS {table} ("
        "id BIGSERIAL PRIMARY KEY, "
        "{contract} TEXT NOT NULL, "
        "{source} TEXT NOT NULL, "
        "{payload} JSONB NOT NULL, "
        "{ingest} TEXT NOT NULL, "
        "created_at TIMESTAMPTZ NOT NULL DEFAULT now(), "
        "updated_at TIMESTAMPTZ NOT NULL DEFAULT now()"
        ")"
    ).format(
        table=table_ref,
        contract=sql.Identifier(settings["contract_column"]),
        source=sql.Identifier(settings["source_column"]),
        payload=sql.Identifier(settings["payload_column"]),
        ingest=sql.Identifier(settings["ingest_column"]),
    )
    index_contract = sql.SQL(
        "CREATE INDEX IF NOT EXISTS {index_name} ON {table} ({contract})"
    ).format(
        index_name=sql.Identifier(f"{table_name}_contract_idx"),
        table=table_ref,
        contract=sql.Identifier(settings["contract_column"]),
    )
    index_source = sql.SQL(
        "CREATE INDEX IF NOT EXISTS {index_name} ON {table} ({source})"
    ).format(
        index_name=sql.Identifier(f"{table_name}_source_idx"),
        table=table_ref,
        source=sql.Identifier(settings["source_column"]),
    )
    with connection.cursor() as cursor:
        cursor.execute(create_sql)
        cursor.execute(index_contract)
        cursor.execute(index_source)


def _ensure_mss_tables(connection) -> None:
    expected_tables = (
        "mss.compendium",
        "mss.anthology_entry",
        "mss.taxonomy_local_map",
        "mss.msn_local_map",
        "mss.muniment",
    )
    with connection.cursor() as cursor:
        for table in expected_tables:
            cursor.execute("SELECT to_regclass(%s)", (table,))
            result = cursor.fetchone()
            if not result or result[0] is None:
                raise DemoDataError(
                    f"Missing MSS table: {table}. Apply migrations before ingesting MSS data."
                )


def _extract_field(payload: dict, keys: tuple[str, ...]) -> str | None:
    for key in keys:
        if key in payload:
            value = payload.get(key)
            if value is not None:
                return str(value)
    return None


def _validate_payload_items(payloads: list[dict], path: Path) -> None:
    if not payloads:
        raise DemoDataError(f"No payloads found in {path}")
    for item in payloads:
        if not isinstance(item, dict):
            raise DemoDataError(f"Non-object payload in {path}: {item}")
        for key in item.keys():
            if not isinstance(key, str):
                raise DemoDataError(f"Non-string key in {path}: {key}")


def ingest_demo_data(
    data_dir: Path,
    default_contract: str | None,
    dry_run: bool,
    limit: int | None,
    glob_pattern: str,
) -> int:
    settings = _get_table_settings()
    table = settings["table"]
    contract_column = settings["contract_column"]
    source_column = settings["source_column"]
    payload_column = settings["payload_column"]
    ingest_column = settings["ingest_column"]
    ingest_source = settings["ingest_source"]

    files = list(iter_demo_files(data_dir, glob_pattern))
    if limit:
        files = files[:limit]

    if dry_run:
        for path in files:
            contract_name = resolve_contract(path.name, default_contract)
            print(f"[dry-run] Would ingest {path.name} -> {contract_name}")
        return 0

    inserted_rows = 0
    created_entries: list[dict[str, str]] = []
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
    schema, table_name = _split_table_name(table)
    table_ref = sql.Identifier(table_name) if schema is None else sql.Identifier(schema, table_name)
    with _get_connection() as connection:
        _ensure_table(connection, settings)
        _ensure_mss_tables(connection)
        with connection.cursor() as cursor:
            for path in files:
                contract_name = resolve_contract(path.name, default_contract)
                payload_items = parse_demo_payload(path)
                _validate_payload_items(payload_items, path)

                compendium_match = compendium_re.match(path.name)
                anthology_match = anthology_re.match(path.name)
                muniment_match = muniment_re.match(path.name)
                txa_match = txa_re.match(path.name)
                msn_match = msn_re.match(path.name)

                if compendium_match:
                    msn_id = compendium_match.group("msn_id")
                    if msn_id not in deleted_mss["compendium"]:
                        cursor.execute(
                            "DELETE FROM mss.compendium WHERE msn_id = %s",
                            (msn_id,),
                        )
                        deleted_mss["compendium"].add(msn_id)
                    record = payload_items[0]
                    title = _extract_field(record, ("title", "#.nominal.txt.256.title"))
                    if not title:
                        raise DemoDataError(f"Missing title in compendium {path.name}")
                    cursor.execute(
                        """
                        INSERT INTO mss.compendium
                            (msn_id, title, anthology_ref, standardization_ref, entity_type, payload)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        """,
                        (
                            msn_id,
                            title,
                            record.get("anthology"),
                            record.get("standardization"),
                            record.get("entity_type"),
                            Json(record),
                        ),
                    )

                if anthology_match:
                    msn_id = anthology_match.group("msn_id")
                    if msn_id not in deleted_mss["anthology"]:
                        cursor.execute(
                            "DELETE FROM mss.anthology_entry WHERE msn_id = %s",
                            (msn_id,),
                        )
                        deleted_mss["anthology"].add(msn_id)
                    for item in payload_items:
                        local_id = _extract_field(item, ("@.lcl.txt.16.local_id", "@.lcl.txt.5.local_id"))
                        title = _extract_field(item, ("#.nominal.txt.256.title",))
                        if not local_id or not title:
                            raise DemoDataError(f"Missing local_id/title in {path.name}")
                        cursor.execute(
                            """
                            INSERT INTO mss.anthology_entry
                                (msn_id, local_id, title, payload)
                            VALUES (%s, %s, %s, %s)
                            """,
                            (msn_id, local_id, title, Json(item)),
                        )

                if muniment_match:
                    msn_id = muniment_match.group("msn_id")
                    if msn_id not in deleted_mss["muniment"]:
                        cursor.execute(
                            "DELETE FROM mss.muniment WHERE msn_id = %s",
                            (msn_id,),
                        )
                        deleted_mss["muniment"].add(msn_id)
                    for item in payload_items:
                        opus_local_id = _extract_field(item, ("@.lcl.txt.16.opus_local_id",))
                        title = _extract_field(item, ("@.nominal.txt.32.title", "#.nominal.txt.256.title"))
                        muniment = _extract_field(item, ("@.nominal.txt.32.muniment",))
                        if not opus_local_id or not muniment:
                            raise DemoDataError(f"Missing opus_local_id/muniment in {path.name}")
                        cursor.execute(
                            """
                            INSERT INTO mss.muniment
                                (msn_id, opus_local_id, title, muniment, payload)
                            VALUES (%s, %s, %s, %s, %s)
                            """,
                            (msn_id, opus_local_id, title, muniment, Json(item)),
                        )

                if txa_match:
                    source_msn_id = txa_match.group("msn_id")
                    if source_msn_id not in deleted_mss["taxonomy"]:
                        cursor.execute(
                            "DELETE FROM mss.taxonomy_local_map WHERE source_msn_id = %s",
                            (source_msn_id,),
                        )
                        deleted_mss["taxonomy"].add(source_msn_id)
                    for item in payload_items:
                        taxonomy_id = _extract_field(item, ("@.txa.txt.16.taxonomy_id",))
                        title = _extract_field(item, ("#.nominal.txt.256.title",))
                        if not taxonomy_id:
                            raise DemoDataError(f"Missing taxonomy_id in {path.name}")
                        cursor.execute(
                            """
                            INSERT INTO mss.taxonomy_local_map
                                (source_msn_id, taxonomy_id, title, payload)
                            VALUES (%s, %s, %s, %s)
                            """,
                            (source_msn_id, taxonomy_id, title, Json(item)),
                        )

                if msn_match:
                    source_msn_id = msn_match.group("msn_id")
                    if source_msn_id not in deleted_mss["msn"]:
                        cursor.execute(
                            "DELETE FROM mss.msn_local_map WHERE source_msn_id = %s",
                            (source_msn_id,),
                        )
                        deleted_mss["msn"].add(source_msn_id)
                    for item in payload_items:
                        mapped_msn_id = _extract_field(item, ("@.msn.txt.16.msn_id",))
                        title = _extract_field(item, ("#.nominal.txt.256.title",))
                        if not mapped_msn_id:
                            raise DemoDataError(f"Missing msn_id in {path.name}")
                        cursor.execute(
                            """
                            INSERT INTO mss.msn_local_map
                                (source_msn_id, msn_id, title, payload)
                            VALUES (%s, %s, %s, %s)
                            """,
                            (source_msn_id, mapped_msn_id, title, Json(item)),
                        )

                delete_sql = sql.SQL(
                    "DELETE FROM {table} WHERE {contract} = %s AND {source} = %s AND {ingest} = %s"
                ).format(
                    table=table_ref,
                    contract=sql.Identifier(contract_column),
                    source=sql.Identifier(source_column),
                    ingest=sql.Identifier(ingest_column),
                )
                cursor.execute(delete_sql, (contract_name, path.name, ingest_source))

                for item in payload_items:
                    insert_sql = sql.SQL(
                        "INSERT INTO {table} ({contract}, {source}, {payload}, {ingest}) "
                        "VALUES (%s, %s, %s, %s)"
                    ).format(
                        table=table_ref,
                        contract=sql.Identifier(contract_column),
                        source=sql.Identifier(source_column),
                        payload=sql.Identifier(payload_column),
                        ingest=sql.Identifier(ingest_column),
                    )
                    cursor.execute(
                        insert_sql,
                        (contract_name, path.name, Json(item), ingest_source),
                    )
                    inserted_rows += 1
                created_entries.append({"source_file": path.name, "contract": contract_name})

        connection.commit()

    for entry in created_entries:
        print(f"[ingested] {entry['source_file']} -> {entry['contract']}")

    return inserted_rows


def main() -> int:
    parser = argparse.ArgumentParser(description="Ingest demo JSON data into Postgres.")
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
    parser.add_argument("--limit", type=int, help="Limit the number of files ingested.")
    parser.add_argument("--dry-run", action="store_true", help="Print actions without DB writes.")
    args = parser.parse_args()

    if not args.data_dir.exists():
        print(f"Demo data directory not found: {args.data_dir}", file=sys.stderr)
        return 1

    try:
        rows = ingest_demo_data(
            data_dir=args.data_dir,
            default_contract=args.default_contract,
            dry_run=args.dry_run,
            limit=args.limit,
            glob_pattern=args.glob,
        )
    except (DemoDataError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    if not args.dry_run:
        print(json.dumps({"ingested_rows": rows}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
