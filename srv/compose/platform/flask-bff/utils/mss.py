"""MSS profile helpers."""
from __future__ import annotations

from typing import Any, Dict, Optional

from flask import session

import db


def current_msn_id() -> Optional[str]:
    user = session.get("user") or {}
    user_id = user.get("user_id")
    if not user_id:
        return None
    row = db.fetchone(
        "SELECT msn_id FROM platform.mss_profile WHERE user_id = %s",
        (user_id,),
    )
    if not row:
        return None
    return str(row["msn_id"])


def load_user_hierarchy(user_id: str) -> Optional[Dict[str, Any]]:
    row = db.fetchone(
        """
        SELECT msn_id, parent_msn_id, role
        FROM platform.mss_profile
        WHERE user_id = %s
        """,
        (user_id,),
    )
    if not row:
        return None
    return {
        "msn_id": str(row["msn_id"]),
        "parent_msn_id": str(row["parent_msn_id"]) if row["parent_msn_id"] else None,
        "role": row["role"],
    }
