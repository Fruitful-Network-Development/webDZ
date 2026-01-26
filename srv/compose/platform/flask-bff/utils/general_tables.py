"""Helpers for MSS general tables."""
from __future__ import annotations

from psycopg2 import sql


def general_table_name(msn_id: str, table_local_id: str) -> str:
    return f"{msn_id}__{table_local_id}"


def general_table_identifier(msn_id: str, table_local_id: str) -> sql.Identifier:
    return sql.Identifier(general_table_name(msn_id, table_local_id))
