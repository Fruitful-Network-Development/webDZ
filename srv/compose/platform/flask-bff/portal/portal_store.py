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
        include_all_ingest: bool = False,
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

        if include_all_ingest:
            pass
        elif ingest_source:
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

    def fetch_correspondence_entries(self, msn_id: str | None = None) -> list[dict]:
        return self._fetch_rows(
            schema="platform",
            table="correspondence",
            columns=("id", "msn_id", "source_file", "entry_index", "payload"),
            where={"msn_id": msn_id} if msn_id else None,
            order_by=("msn_id", "entry_index"),
        )

    def create_correspondence_entry(self, *, msn_id: str, source_file: str, payload: dict) -> dict:
        _validate_identifier("platform")
        _validate_identifier("correspondence")
        with self._get_pool().getconn() as connection:
            try:
                with connection.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute(
                        """
                        INSERT INTO platform.correspondence (msn_id, source_file, entry_index, payload)
                        VALUES (%s, %s, 0, %s)
                        RETURNING id, msn_id, source_file, entry_index, payload
                        """,
                        (msn_id, source_file, payload),
                    )
                    row = cursor.fetchone()
                connection.commit()
            finally:
                self._get_pool().putconn(connection)
        return dict(row) if row else {}

    def update_correspondence_entry(self, *, entry_id: int, payload: dict) -> dict:
        with self._get_pool().getconn() as connection:
            try:
                with connection.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute(
                        """
                        UPDATE platform.correspondence
                        SET payload = %s, updated_at = now()
                        WHERE id = %s
                        RETURNING id, msn_id, source_file, entry_index, payload
                        """,
                        (payload, entry_id),
                    )
                    row = cursor.fetchone()
                connection.commit()
            finally:
                self._get_pool().putconn(connection)
        return dict(row) if row else {}

    def delete_correspondence_entry(self, *, entry_id: int) -> bool:
        with self._get_pool().getconn() as connection:
            try:
                with connection.cursor() as cursor:
                    cursor.execute(
                        "DELETE FROM platform.correspondence WHERE id = %s",
                        (entry_id,),
                    )
                    deleted = cursor.rowcount > 0
                connection.commit()
            finally:
                self._get_pool().putconn(connection)
        return deleted

    def fetch_compendium_entries(self, msn_id: str | None = None) -> list[dict]:
        return self._fetch_rows(
            schema="mss",
            table="compendium",
            columns=(
                "msn_id",
                "title",
                "anthology_ref",
                "standardization_ref",
                "entity_type",
                "payload",
            ),
            where={"msn_id": msn_id} if msn_id else None,
            order_by=("msn_id",),
        )

    def fetch_anthology_entries(self, msn_id: str) -> list[dict]:
        return self._fetch_rows(
            schema="mss",
            table="anthology_entry",
            columns=("msn_id", "local_id", "title", "payload"),
            where={"msn_id": msn_id},
            order_by=("local_id",),
        )

    def fetch_taxonomy_local_map(self, source_msn_id: str) -> list[dict]:
        return self._fetch_rows(
            schema="mss",
            table="taxonomy_local_map",
            columns=("source_msn_id", "taxonomy_id", "local_id", "title", "payload"),
            where={"source_msn_id": source_msn_id},
            order_by=("taxonomy_id",),
        )

    def fetch_msn_local_map(self, source_msn_id: str) -> list[dict]:
        return self._fetch_rows(
            schema="mss",
            table="msn_local_map",
            columns=("source_msn_id", "msn_id", "local_id", "title", "payload"),
            where={"source_msn_id": source_msn_id},
            order_by=("msn_id",),
        )

    def fetch_muniment_entries(self, msn_id: str) -> list[dict]:
        return self._fetch_rows(
            schema="mss",
            table="muniment",
            columns=("msn_id", "opus_local_id", "title", "muniment", "payload"),
            where={"msn_id": msn_id},
            order_by=("opus_local_id",),
        )

    def fetch_all_muniment_entries(self) -> list[dict]:
        return self._fetch_rows(
            schema="mss",
            table="muniment",
            columns=("msn_id", "opus_local_id", "title", "muniment", "payload"),
            order_by=("msn_id", "opus_local_id"),
        )

    def _fetch_rows(
        self,
        *,
        schema: str,
        table: str,
        columns: tuple[str, ...],
        where: dict[str, str] | None = None,
        order_by: tuple[str, ...] | None = None,
    ) -> list[dict]:
        _validate_identifier(schema)
        _validate_identifier(table)
        for column in columns:
            _validate_identifier(column)

        where = where or {}
        for column in where:
            _validate_identifier(column)

        order_by = order_by or ()
        for column in order_by:
            _validate_identifier(column)

        table_ref = sql.Identifier(schema, table)
        query = sql.SQL("SELECT {fields} FROM {table}").format(
            fields=sql.SQL(", ").join(sql.Identifier(column) for column in columns),
            table=table_ref,
        )

        values: list[str] = []
        if where:
            where_clauses = [
                sql.SQL("{} = %s").format(sql.Identifier(column)) for column in where
            ]
            values = [where[column] for column in where]
            query = query + sql.SQL(" WHERE ") + sql.SQL(" AND ").join(where_clauses)

        if order_by:
            query = query + sql.SQL(" ORDER BY ") + sql.SQL(", ").join(
                sql.Identifier(column) for column in order_by
            )

        with self._get_pool().getconn() as connection:
            try:
                with connection.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute(query, values)
                    rows = cursor.fetchall() or []
            finally:
                self._get_pool().putconn(connection)

        return [dict(row) for row in rows]

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