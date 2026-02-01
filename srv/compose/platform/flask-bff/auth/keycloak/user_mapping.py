"""User mapping helpers for Keycloak -> platform profile."""
from __future__ import annotations

import os
from typing import Any

import psycopg2


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


def fetch_user_profile(user_id: str) -> dict[str, Any] | None:
    """Return platform.mss_profile data for a Keycloak user_id."""
    try:
        with _get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT msn_id, user_id, role, display_name
                    FROM platform.mss_profile
                    WHERE user_id = %s
                    """,
                    (user_id,),
                )
                row = cursor.fetchone()
    except Exception as exc:
        raise UserMappingError("Failed to query platform.mss_profile.") from exc

    if not row:
        return None
    return {
        "msn_id": row[0],
        "user_id": str(row[1]),
        "role": row[2],
        "display_name": row[3],
    }
