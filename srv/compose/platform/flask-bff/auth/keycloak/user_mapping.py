"""User mapping helpers for Keycloak -> portal identity access payloads."""
from __future__ import annotations

import os
import re
from typing import Any

import psycopg2
from psycopg2 import sql


class UserMappingError(RuntimeError):
    """Raised when user mapping lookup fails."""


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


IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _validate_identifier(value: str) -> None:
    if not IDENTIFIER_RE.match(value):
        raise UserMappingError(f"Invalid identifier: {value}")


def _split_table_name(table_name: str) -> tuple[str | None, str]:
    parts = table_name.split(".")
    if len(parts) == 1:
        _validate_identifier(parts[0])
        return None, parts[0]
    if len(parts) == 2:
        _validate_identifier(parts[0])
        _validate_identifier(parts[1])
        return parts[0], parts[1]
    raise UserMappingError(f"Invalid table name: {table_name}")


def _get_contract_settings() -> dict[str, str]:
    return {
        "table": os.getenv("PORTAL_CONTRACT_TABLE", "platform.portal_contract_payloads"),
        "contract_column": os.getenv("PORTAL_CONTRACT_COLUMN", "contract_name"),
        "payload_column": os.getenv("PORTAL_PAYLOAD_COLUMN", "payload"),
    }


def fetch_identity_access(user_id: str) -> dict[str, Any] | None:
    """Return identity_access payload details for a Keycloak user_id."""
    settings = _get_contract_settings()
    schema, table = _split_table_name(settings["table"])
    _validate_identifier(settings["contract_column"])
    _validate_identifier(settings["payload_column"])

    table_ref = sql.Identifier(table) if schema is None else sql.Identifier(schema, table)
    contract_column = sql.Identifier(settings["contract_column"])
    payload_column = sql.Identifier(settings["payload_column"])
    keycloak_key = "#.nominal.txt.36.keycloak_user_id"
    msn_key = "@.msn.txt.9.msn_id"
    beneficiary_key = "@.lcl.txt.4.beneficiary_local_id"
    principal_key = "@.lcl.txt.4.principle_user_local_id"

    try:
        with _get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT {payload}
                    FROM {table}
                    WHERE {contract} = %s
                      AND {payload} ->> %s = %s
                    LIMIT 1
                    """.format(
                        payload=payload_column,
                        table=table_ref,
                        contract=contract_column,
                    ),
                    ("identity_access", keycloak_key, user_id),
                )
                row = cursor.fetchone()
    except Exception as exc:
        raise UserMappingError("Failed to query identity_access payloads.") from exc

    if not row:
        return None
    payload = row[0] or {}
    return {
        "msn_id": payload.get(msn_key),
        "user_id": user_id,
        "beneficiary_local_id": payload.get(beneficiary_key),
        "principle_user_local_id": payload.get(principal_key),
    }
