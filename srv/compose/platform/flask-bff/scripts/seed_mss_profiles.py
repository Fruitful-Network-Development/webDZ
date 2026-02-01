#!/usr/bin/env python3
"""Seed platform.mss_profile from platform.beneficiary demo data."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import psycopg2

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from demo_data_common import DemoDataError, iter_demo_files, parse_demo_payload  # noqa: E402


KEYCLOAK_KEY = "#.nominal.txt.36.keycloak_user_id"
MSN_ID_KEY = "@.msn.txt.9.msn_id"
BENEFICIARY_LOCAL_ID_KEY = "@.lcl.txt.4.beneficiary_local_id"
PRINCIPAL_LOCAL_ID_KEY = "@.lcl.txt.4.principle_user_local_id"


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


def _iter_beneficiary_payloads(data_dir: Path):
    for path in iter_demo_files(data_dir):
        if path.name.startswith("platform.beneficiary"):
            yield path, parse_demo_payload(path)


def seed_mss_profiles(data_dir: Path, role: str, dry_run: bool) -> int:
    updates = 0
    with _get_connection() as connection:
        with connection.cursor() as cursor:
            for path, payloads in _iter_beneficiary_payloads(data_dir):
                for entry in payloads:
                    keycloak_user_id = entry.get(KEYCLOAK_KEY) or ""
                    msn_id = entry.get(MSN_ID_KEY)
                    if not keycloak_user_id or not msn_id:
                        continue
                    display_name = entry.get(BENEFICIARY_LOCAL_ID_KEY) or entry.get(PRINCIPAL_LOCAL_ID_KEY)
                    if dry_run:
                        print(f"[dry-run] Would seed {msn_id} -> {keycloak_user_id} ({path.name})")
                        updates += 1
                        continue
                    cursor.execute(
                        "DELETE FROM platform.mss_profile WHERE user_id = %s AND msn_id <> %s",
                        (keycloak_user_id, msn_id),
                    )
                    cursor.execute(
                        """
                        INSERT INTO platform.mss_profile (msn_id, user_id, display_name, role)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (msn_id)
                        DO UPDATE SET
                          user_id = EXCLUDED.user_id,
                          display_name = EXCLUDED.display_name,
                          role = EXCLUDED.role,
                          updated_at = now()
                        """,
                        (msn_id, keycloak_user_id, display_name, role),
                    )
                    updates += 1
                    print(f"[seeded] {msn_id} -> {keycloak_user_id} ({path.name})")
    return updates


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed platform.mss_profile from beneficiary demo data.")
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "demo-data",
        help="Directory containing demo JSON files.",
    )
    parser.add_argument("--role", default="principal_user", help="Role to assign for seeded users.")
    parser.add_argument("--dry-run", action="store_true", help="Print actions without writing to the DB.")
    args = parser.parse_args()

    try:
        updates = seed_mss_profiles(args.data_dir, args.role, args.dry_run)
    except DemoDataError as exc:
        raise SystemExit(f"Invalid demo data: {exc}") from exc

    print({"seeded_rows": updates, "dry_run": args.dry_run})


if __name__ == "__main__":
    main()
