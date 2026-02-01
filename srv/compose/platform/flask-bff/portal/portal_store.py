"""Portal data-access helpers backed by Postgres."""
from __future__ import annotations

from dataclasses import dataclass
import os
import re
from typing import Iterable

from psycopg2 import pool, sql
from psycopg2.extras import RealDictCursor


class PortalStoreError(RuntimeError):
    """Raised when portal data access fails."""


IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _validate_identifier(value: str) -> None:
    if not IDENTIFIER_RE.match(value):
        raise PortalStoreError(f"Invalid identifier: {value}")


def _split_table_name(table_name: str) -> tuple[str | None, str]:
    parts = table_name.split(".")
    if len(parts) == 1:
        _validate_identifier(parts[0])
        return None, parts[0]
    if len(parts) == 2:
        _validate_identifier(parts[0])
        _validate_identifier(parts[1])
        return parts[0], parts[1]
    raise PortalStoreError(f"Invalid table name: {table_name}")


def _build_dsn() -> str:
    database_url = os.getenv("DATABASE_URL") or os.getenv("PLATFORM_DB_URL")
    if database_url:
        return database_url
    host = os.getenv("PGHOST")
    port = os.getenv("PGPORT")
    user = os.getenv("PGUSER")
    password = os.getenv("PGPASSWORD")
    dbname = os.getenv("PGDATABASE")
    if not (host and port and user and dbname):
        raise PortalStoreError(
            "Missing database connection configuration. "
            "Set DATABASE_URL or PGHOST/PGPORT/PGUSER/PGDATABASE."
        )
    password_part = f" password={password}" if password else ""
    return f"host={host} port={port} dbname={dbname} user={user}{password_part}"


@dataclass(frozen=True)
class ContractPayload:
    contract_name: str
    source_file: str
    payload: dict
    ingest_source: str


class PortalStore:
    """Access contract payloads stored in Postgres."""

    def __init__(self) -> None:
        self._pool: pool.SimpleConnectionPool | None = None
        self._table = os.getenv("PORTAL_CONTRACT_TABLE", "platform.portal_contract_payloads")
        self._contract_column = os.getenv("PORTAL_CONTRACT_COLUMN", "contract_name")
        self._source_column = os.getenv("PORTAL_SOURCE_COLUMN", "source_file")
        self._payload_column = os.getenv("PORTAL_PAYLOAD_COLUMN", "payload")
        self._ingest_column = os.getenv("PORTAL_INGEST_COLUMN", "ingest_source")
        self._default_ingest_source = os.getenv("PORTAL_INGEST_SOURCE", "demo-data")
        self._table_checked = False

    def _get_pool(self) -> pool.SimpleConnectionPool:
        if self._pool is None:
            minconn = int(os.getenv("PORTAL_DB_POOL_MIN", "1"))
            maxconn = int(os.getenv("PORTAL_DB_POOL_MAX", "5"))
            self._pool = pool.SimpleConnectionPool(minconn, maxconn, _build_dsn())
        return self._pool

    def _ensure_table_available(self) -> None:
        if self._table_checked:
            return
        schema, table = _split_table_name(self._table)
        with self._get_pool().getconn() as connection:
            try:
                with connection.cursor() as cursor:
                    if schema:
                        cursor.execute(
                            "SELECT to_regclass(%s)",
                            (f"{schema}.{table}",),
                        )
                    else:
                        cursor.execute("SELECT to_regclass(%s)", (table,))
                    result = cursor.fetchone()
                    if not result or result[0] is None:
                        raise PortalStoreError(
                            f"Portal contract table not found: {self._table}. "
                            "Run scripts/ingest_demo_data.py to create it."
                        )
            finally:
                self._get_pool().putconn(connection)
        self._table_checked = True

    def fetch_contract_payloads(
        self,
        contract_name: str,
        *,
        source_file: str | None = None,
        ingest_source: str | None = None,
    ) -> list[ContractPayload]:
        self._ensure_table_available()
        schema, table = _split_table_name(self._table)
        _validate_identifier(self._contract_column)
        _validate_identifier(self._source_column)
        _validate_identifier(self._payload_column)
        _validate_identifier(self._ingest_column)

        where_clauses = [
            sql.SQL("{} = %s").format(sql.Identifier(self._contract_column))
        ]
        values: list[str] = [contract_name]

        if source_file:
            where_clauses.append(sql.SQL("{} = %s").format(sql.Identifier(self._source_column)))
            values.append(source_file)

        if ingest_source:
            where_clauses.append(sql.SQL("{} = %s").format(sql.Identifier(self._ingest_column)))
            values.append(ingest_source)
        else:
            where_clauses.append(sql.SQL("{} = %s").format(sql.Identifier(self._ingest_column)))
            values.append(self._default_ingest_source)

        table_ref = sql.Identifier(table) if schema is None else sql.Identifier(schema, table)
        query = sql.SQL(
            "SELECT {contract}, {source}, {payload}, {ingest} "
            "FROM {table} WHERE {where} ORDER BY {source} ASC"
        ).format(
            contract=sql.Identifier(self._contract_column),
            source=sql.Identifier(self._source_column),
            payload=sql.Identifier(self._payload_column),
            ingest=sql.Identifier(self._ingest_column),
            table=table_ref,
            where=sql.SQL(" AND ").join(where_clauses),
        )

        with self._get_pool().getconn() as connection:
            try:
                with connection.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute(query, values)
                    rows = cursor.fetchall() or []
            finally:
                self._get_pool().putconn(connection)

        return [
            ContractPayload(
                contract_name=row[self._contract_column],
                source_file=row[self._source_column],
                payload=row[self._payload_column],
                ingest_source=row[self._ingest_column],
            )
            for row in rows
        ]

    @staticmethod
    def match_payloads_by_value(payloads: Iterable[ContractPayload], value: str) -> list[ContractPayload]:
        matched: list[ContractPayload] = []
        for payload in payloads:
            if _payload_contains_value(payload.payload, value):
                matched.append(payload)
        return matched


def _payload_contains_value(payload: dict, target: str) -> bool:
    if not isinstance(payload, dict):
        return False
    for value in payload.values():
        if isinstance(value, str) and value == target:
            return True
        if isinstance(value, list) and target in value:
            return True
    return False
