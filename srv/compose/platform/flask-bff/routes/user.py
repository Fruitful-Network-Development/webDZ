"""User hierarchy and MSS profile admin routes."""
from __future__ import annotations

import uuid
from typing import Any, Dict

from flask import Blueprint, jsonify, request
from psycopg2 import sql

import db
from authz import require_root_admin
from routes.common import json_body, require_fields


user_bp = Blueprint("user", __name__)


@user_bp.get("/api/admin/mss-profiles")
@require_root_admin
def admin_mss_profiles():
    profiles = db.fetchall(
        """
        SELECT msn_id, user_id, parent_msn_id, display_name, role, created_at, updated_at
        FROM platform.mss_profile
        ORDER BY created_at DESC
        """
    )
    return jsonify({"mss_profiles": profiles}), 200


@user_bp.post("/api/admin/mss-profiles")
@require_root_admin
def admin_mss_profiles_create():
    payload, error = json_body()
    if error:
        return error
    error = require_fields(payload, ["user_id", "display_name", "role"])
    if error:
        return error

    user_id = payload["user_id"]
    display_name = payload["display_name"]
    role = payload["role"]
    parent_msn_id = payload.get("parent_msn_id")
    msn_id = payload.get("msn_id")

    if not isinstance(user_id, str) or not user_id.strip():
        return jsonify({"error": "invalid_user_id"}), 400
    if not isinstance(display_name, str) or not display_name.strip():
        return jsonify({"error": "invalid_display_name"}), 400
    if not isinstance(role, str) or not role.strip():
        return jsonify({"error": "invalid_role"}), 400
    if parent_msn_id is not None and not isinstance(parent_msn_id, str):
        return jsonify({"error": "invalid_parent_msn_id"}), 400
    if msn_id is not None and (not isinstance(msn_id, str) or not msn_id.strip()):
        return jsonify({"error": "invalid_msn_id"}), 400

    try:
        uuid.UUID(user_id)
    except ValueError:
        return jsonify({"error": "invalid_user_id"}), 400

    parent_id = None
    if parent_msn_id:
        parent_id = parent_msn_id.strip()

    if msn_id is None:
        msn_id = f"msn-{uuid.uuid4()}"
    else:
        msn_id = msn_id.strip()
    db.execute(
        """
        INSERT INTO platform.mss_profile
        (msn_id, user_id, parent_msn_id, display_name, role)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (msn_id, user_id.strip(), parent_id, display_name.strip(), role.strip()),
    )

    return jsonify({
        "msn_id": msn_id,
        "user_id": user_id.strip(),
        "parent_msn_id": parent_id,
        "display_name": display_name.strip(),
        "role": role.strip(),
    }), 201


@user_bp.get("/api/admin/user-hierarchy")
@require_root_admin
def admin_user_hierarchy():
    user_id = request.args.get("user_id")
    msn_id = request.args.get("msn_id")

    if user_id:
        try:
            uuid.UUID(user_id)
        except ValueError:
            return jsonify({"error": "invalid_user_id"}), 400
        row = db.fetchone(
            """
            SELECT msn_id, user_id, parent_msn_id, display_name, role, created_at, updated_at
            FROM platform.mss_profile
            WHERE user_id = %s
            """,
            (user_id,),
        )
        if not row:
            return jsonify({"error": "profile_not_found"}), 404
        return jsonify({"profile": row}), 200

    if msn_id:
        if not isinstance(msn_id, str) or not msn_id.strip():
            return jsonify({"error": "invalid_msn_id"}), 400
        row = db.fetchone(
            """
            SELECT msn_id, user_id, parent_msn_id, display_name, role, created_at, updated_at
            FROM platform.mss_profile
            WHERE msn_id = %s
            """,
            (msn_id,),
        )
        if not row:
            return jsonify({"error": "profile_not_found"}), 404
        return jsonify({"profile": row}), 200

    profiles = db.fetchall(
        """
        SELECT msn_id, user_id, parent_msn_id, display_name, role, created_at, updated_at
        FROM platform.mss_profile
        ORDER BY created_at DESC
        """
    )
    return jsonify({"profiles": profiles}), 200


@user_bp.post("/api/admin/user-hierarchy")
@require_root_admin
def admin_user_hierarchy_create():
    payload, error = json_body()
    if error:
        return error
    error = require_fields(payload, ["user_id", "display_name", "role"])
    if error:
        return error

    user_id = payload["user_id"]
    display_name = payload["display_name"]
    role = payload["role"]
    parent_msn_id = payload.get("parent_msn_id")
    msn_id = payload.get("msn_id")

    if not isinstance(user_id, str) or not user_id.strip():
        return jsonify({"error": "invalid_user_id"}), 400
    if not isinstance(display_name, str) or not display_name.strip():
        return jsonify({"error": "invalid_display_name"}), 400
    if not isinstance(role, str) or not role.strip():
        return jsonify({"error": "invalid_role"}), 400
    if parent_msn_id is not None and not isinstance(parent_msn_id, str):
        return jsonify({"error": "invalid_parent_msn_id"}), 400
    if msn_id is not None and (not isinstance(msn_id, str) or not msn_id.strip()):
        return jsonify({"error": "invalid_msn_id"}), 400

    try:
        uuid.UUID(user_id)
    except ValueError:
        return jsonify({"error": "invalid_user_id"}), 400

    parent_id = None
    if parent_msn_id:
        parent_id = parent_msn_id.strip()

    if msn_id is None:
        msn_id = f"msn-{uuid.uuid4()}"
    else:
        msn_id = msn_id.strip()
    row = db.fetchone(
        """
        INSERT INTO platform.mss_profile
        (msn_id, user_id, parent_msn_id, display_name, role)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING msn_id, user_id, parent_msn_id, display_name, role, created_at, updated_at
        """,
        (msn_id, user_id.strip(), parent_id, display_name.strip(), role.strip()),
    )
    return jsonify({"profile": row}), 201


@user_bp.put("/api/admin/user-hierarchy")
@require_root_admin
def admin_user_hierarchy_update():
    payload, error = json_body()
    if error:
        return error
    error = require_fields(payload, ["msn_id"])
    if error:
        return error

    msn_id = payload["msn_id"]
    if not isinstance(msn_id, str) or not msn_id.strip():
        return jsonify({"error": "invalid_msn_id"}), 400

    updates: Dict[str, Any] = {}
    if "user_id" in payload:
        user_id = payload["user_id"]
        if not isinstance(user_id, str) or not user_id.strip():
            return jsonify({"error": "invalid_user_id"}), 400
        try:
            uuid.UUID(user_id)
        except ValueError:
            return jsonify({"error": "invalid_user_id"}), 400
        updates["user_id"] = user_id.strip()
    if "display_name" in payload:
        display_name = payload["display_name"]
        if not isinstance(display_name, str) or not display_name.strip():
            return jsonify({"error": "invalid_display_name"}), 400
        updates["display_name"] = display_name.strip()
    if "role" in payload:
        role = payload["role"]
        if not isinstance(role, str) or not role.strip():
            return jsonify({"error": "invalid_role"}), 400
        updates["role"] = role.strip()
    if "parent_msn_id" in payload:
        parent_msn_id = payload["parent_msn_id"]
        if parent_msn_id in (None, ""):
            updates["parent_msn_id"] = None
        elif not isinstance(parent_msn_id, str):
            return jsonify({"error": "invalid_parent_msn_id"}), 400
        else:
            updates["parent_msn_id"] = parent_msn_id.strip()

    if not updates:
        return jsonify({"error": "missing_fields"}), 400

    update_clause = sql.SQL(", ").join(
        sql.SQL("{field} = %s").format(field=sql.Identifier(field))
        for field in updates.keys()
    )
    values = list(updates.values()) + [msn_id]
    row = db.fetchone(
        sql.SQL(
            """
            UPDATE platform.mss_profile
            SET {updates}, updated_at = now()
            WHERE msn_id = %s
            RETURNING msn_id, user_id, parent_msn_id, display_name, role, created_at, updated_at
            """
        ).format(updates=update_clause),
        values,
    )
    if not row:
        return jsonify({"error": "profile_not_found"}), 404
    return jsonify({"profile": row}), 200


@user_bp.delete("/api/admin/user-hierarchy")
@require_root_admin
def admin_user_hierarchy_delete():
    payload, error = json_body()
    if error:
        return error
    error = require_fields(payload, ["msn_id"])
    if error:
        return error

    msn_id = payload["msn_id"]
    if not isinstance(msn_id, str) or not msn_id.strip():
        return jsonify({"error": "invalid_msn_id"}), 400

    row = db.fetchone(
        "DELETE FROM platform.mss_profile WHERE msn_id = %s RETURNING msn_id",
        (msn_id,),
    )
    if not row:
        return jsonify({"error": "profile_not_found"}), 404
    return jsonify({"deleted": True, "msn_id": row["msn_id"]}), 200
