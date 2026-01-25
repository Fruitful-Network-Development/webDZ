"""Postgres helpers for the platform BFF."""

from __future__ import annotations

import os
from typing import Any, Iterable, Optional

import psycopg2
import psycopg2.extras

_CONN = None
_DB_URL = os.getenv("PLATFORM_DB_URL")


def get_conn():
    """Return a shared database connection."""
    global _CONN
    if _CONN is None or _CONN.closed:
        if not _DB_URL:
            raise RuntimeError("Missing required environment variable: PLATFORM_DB_URL")
        _CONN = psycopg2.connect(_DB_URL)
    return _CONN


def execute(query: str, params: Optional[Iterable[Any]] = None) -> None:
    """Execute a write query and commit."""
    conn = get_conn()
    with conn.cursor() as cur:
        cur.execute(query, params)
    conn.commit()


def fetchall(query: str, params: Optional[Iterable[Any]] = None):
    """Execute a query and return rows as dicts."""
    conn = get_conn()
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(query, params)
        return cur.fetchall()


def fetchone(query: str, params: Optional[Iterable[Any]] = None):
    """Execute a query and return a single row as a dict."""
    conn = get_conn()
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(query, params)
        return cur.fetchone()


def close_conn() -> None:
    """Close the shared connection if it exists."""
    global _CONN
    if _CONN is not None and not _CONN.closed:
        _CONN.close()
    _CONN = None
