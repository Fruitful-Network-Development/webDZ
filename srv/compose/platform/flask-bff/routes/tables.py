"""Tenant table CRUD and SAMRAS lookup routes."""
from __future__ import annotations

import json
import uuid
from typing import Any, Dict, Optional

from flask import Blueprint, jsonify
from psycopg2 import sql
from psycopg2.extras import Json

import db
from config import DEMO_ARCHETYPE_ID, DEMO_LOCAL_DOMAIN_ID, DEMO_TABLE_ID, DEMO_TENANT_ID
from routes.common import json_body, require_login, require_tenant_access
from utils.mss import current_msn_id
from utils.samras import (
    is_samras_domain,
    parse_samras_address,
    samras_address_in_stream,
    samras_find_node,
    samras_layout_lookup,
    samras_node_key,
    validate_samras_reference,
)


tables_bp = Blueprint("tables", __name__)


# ----------------------------
# Dynamic table helpers
# ----------------------------

def seed_demo_data() -> None:
    if not db.fetchone(
        "SELECT 1 FROM platform.local_domain WHERE local_id = %s",
        (DEMO_LOCAL_DOMAIN_ID,),
    ):
        db.execute(
            "INSERT INTO platform.local_domain (local_id, title) VALUES (%s, %s)",
            (DEMO_LOCAL_DOMAIN_ID, "Companion Animals"),
        )

    if not db.fetchone(
        "SELECT 1 FROM platform.archetype WHERE id = %s",
        (DEMO_ARCHETYPE_ID,),
    ):
        db.execute(
            """
            INSERT INTO platform.archetype (id, tenant_id, name, version)
            VALUES (%s, %s, %s, %s)
            """,
            (DEMO_ARCHETYPE_ID, DEMO_TENANT_ID, "companion_animals", 1),
        )
        db.execute(
            """
            INSERT INTO platform.archetype_field
            (archetype_id, position, name, type, ref_domain, constraints)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (DEMO_ARCHETYPE_ID, 1, "name", "string", None, None),
        )
        db.execute(
            """
            INSERT INTO platform.archetype_field
            (archetype_id, position, name, type, ref_domain, constraints)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                DEMO_ARCHETYPE_ID,
                2,
                "taxa_ref",
                "string",
                "SAMRAS",
                json.dumps({"samras_mode": "exact"}),
            ),
        )

    if not db.fetchone(
        "SELECT 1 FROM platform.manifest WHERE table_id = %s",
        (DEMO_TABLE_ID,),
    ):
        db.execute(
            """
            INSERT INTO platform.manifest (table_id, tenant_id, archetype_id)
            VALUES (%s, %s, %s)
            """,
            (DEMO_TABLE_ID, DEMO_TENANT_ID, DEMO_ARCHETYPE_ID),
        )


def _load_manifest_entry(tenant_id: str, table_id: str):
    return db.fetchone(
        """
        SELECT table_id, archetype_id
        FROM platform.manifest
        WHERE tenant_id = %s AND table_id = %s
        """,
        (tenant_id, table_id),
    )


def _load_archetype_fields(archetype_id: str) -> list[Dict[str, Any]]:
    fields = db.fetchall(
        """
        SELECT position, name, type, ref_domain, constraints
        FROM platform.archetype_field
        WHERE archetype_id = %s
        ORDER BY position
        """,
        (archetype_id,),
    )
    for field in fields:
        constraints = field.get("constraints")
        if isinstance(constraints, str):
            field["constraints"] = json.loads(constraints)
    return fields


def _load_local_domain(local_id: str):
    return db.fetchone(
        "SELECT local_id, title FROM platform.local_domain WHERE local_id = %s",
        (local_id,),
    )


def _dynamic_table_identifier(msn_id: str, local_id: str) -> sql.Identifier:
    table_name = f"{msn_id}{local_id}"
    return sql.Identifier(table_name)


def _field_sql_type(field: Dict[str, Any]) -> sql.SQL:
    if field.get("ref_domain"):
        return sql.SQL("JSONB")
    field_type = (field.get("type") or "").lower()
    if field_type == "string":
        return sql.SQL("TEXT")
    if field_type in {"int", "integer"}:
        return sql.SQL("INTEGER")
    if field_type in {"float", "number", "decimal"}:
        return sql.SQL("DOUBLE PRECISION")
    if field_type in {"bool", "boolean"}:
        return sql.SQL("BOOLEAN")
    if field_type in {"json", "object"}:
        return sql.SQL("JSONB")
    return sql.SQL("TEXT")


def _ensure_dynamic_table(table_identifier: sql.Identifier, fields: list[Dict[str, Any]]) -> None:
    base_query = sql.SQL(
        """
        CREATE TABLE IF NOT EXISTS {table} (
            record_id UUID PRIMARY KEY,
            created_at TIMESTAMPTZ DEFAULT now(),
            updated_at TIMESTAMPTZ DEFAULT now()
        )
        """
    ).format(table=table_identifier)
    db.execute(base_query)

    for field in fields:
        alter_query = sql.SQL(
            "ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {column} {col_type}"
        ).format(
            table=table_identifier,
            column=sql.Identifier(field["name"]),
            col_type=_field_sql_type(field),
        )
        db.execute(alter_query)


def _validate_field_value(field: Dict[str, Any], value: Any) -> Optional[str]:
    if field.get("ref_domain"):
        if not isinstance(value, dict):
            return "invalid_reference"
        has_system_id = "system_id" in value
        has_system_value = "system_value" in value
        if has_system_id and has_system_value:
            return "ambiguous_reference"
        if not has_system_id and not has_system_value:
            return "missing_reference"
        ref_domain = field.get("ref_domain")
        if is_samras_domain(ref_domain):
            return validate_samras_reference(field, value, has_system_id, has_system_value)
        constraints = field.get("constraints") or {}
        if constraints.get("mode") == "exact" and not has_system_id:
            return "missing_system_id"
        if constraints.get("mode") == "exact" and has_system_value:
            return "system_value_not_allowed"
        if has_system_id and not isinstance(value.get("system_id"), str):
            return "invalid_system_id"
        if has_system_value and not isinstance(value.get("system_value"), str):
            return "invalid_system_value"
        return None

    field_type = (field.get("type") or "").lower()
    if field_type == "string":
        if not isinstance(value, str):
            return "invalid_string"
        return None
    if field_type in {"int", "integer"}:
        if not isinstance(value, int) or isinstance(value, bool):
            return "invalid_integer"
        return None
    if field_type in {"float", "number", "decimal"}:
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            return "invalid_number"
        return None
    if field_type in {"bool", "boolean"}:
        if not isinstance(value, bool):
            return "invalid_boolean"
        return None
    if field_type in {"json", "object"}:
        if not isinstance(value, dict):
            return "invalid_object"
        return None
    return None


def _validate_record_payload(
    payload: Dict[str, Any],
    fields: list[Dict[str, Any]],
) -> tuple[Optional[Dict[str, Any]], Optional[tuple[Any, int]]]:
    expected = [field["name"] for field in fields]
    missing = [name for name in expected if name not in payload]
    if missing:
        return None, (jsonify({"error": "missing_fields", "fields": missing}), 400)
    extra = [key for key in payload.keys() if key not in expected]
    if extra:
        return None, (jsonify({"error": "unexpected_fields", "fields": extra}), 400)

    cleaned = {}
    for field in fields:
        value = payload.get(field["name"])
        error = _validate_field_value(field, value)
        if error:
            return None, (
                jsonify({"error": "invalid_field", "field": field["name"], "reason": error}),
                400,
            )
        cleaned[field["name"]] = value
    return cleaned, None


def _serialize_field_value(field: Dict[str, Any], value: Any) -> Any:
    if field.get("ref_domain"):
        return Json(value)
    field_type = (field.get("type") or "").lower()
    if field_type in {"json", "object"} and isinstance(value, dict):
        return Json(value)
    return value


def _resolve_table_context(
    tenant_id: str,
    table_id: str,
) -> tuple[Optional[Dict[str, Any]], Optional[tuple[Any, int]]]:
    try:
        uuid.UUID(table_id)
    except ValueError:
        return None, (jsonify({"error": "invalid_table_id"}), 400)

    manifest_entry = _load_manifest_entry(tenant_id, table_id)
    if not manifest_entry:
        return None, (jsonify({"error": "manifest_not_found"}), 404)

    local_domain = _load_local_domain(table_id)
    if not local_domain:
        return None, (jsonify({"error": "local_domain_not_found"}), 404)

    archetype_id = str(manifest_entry["archetype_id"])
    fields = _load_archetype_fields(archetype_id)
    if not fields:
        return None, (jsonify({"error": "archetype_fields_not_found"}), 404)

    msn_id = current_msn_id()
    if not msn_id:
        return None, (jsonify({"error": "missing_msn_profile"}), 400)

    return {
        "archetype_id": archetype_id,
        "fields": fields,
        "local_domain": local_domain,
        "msn_id": msn_id,
        "table_identifier": _dynamic_table_identifier(msn_id, table_id),
    }, None


# ----------------------------
# Routes
# ----------------------------

@tables_bp.get("/api/t/<tenant_id>/tables/<table_id>")
@require_login
def tenant_table_list(tenant_id: str, table_id: str):
    guard = require_tenant_access(tenant_id)
    if guard:
        return guard

    context, error = _resolve_table_context(tenant_id, table_id)
    if error:
        return error

    table_identifier = context["table_identifier"]
    fields = context["fields"]
    _ensure_dynamic_table(table_identifier, fields)

    column_names = [
        sql.Identifier("record_id"),
        sql.Identifier("created_at"),
        sql.Identifier("updated_at"),
    ] + [sql.Identifier(field["name"]) for field in fields]
    query = sql.SQL("SELECT {columns} FROM {table} ORDER BY created_at DESC").format(
        columns=sql.SQL(", ").join(column_names),
        table=table_identifier,
    )
    rows = db.fetchall(query)
    return jsonify({
        "table_id": table_id,
        "records": rows,
    }), 200


@tables_bp.post("/api/t/<tenant_id>/tables/<table_id>")
@require_login
def tenant_table_create_record(tenant_id: str, table_id: str):
    guard = require_tenant_access(tenant_id)
    if guard:
        return guard

    payload, error = json_body()
    if error:
        return error

    context, error = _resolve_table_context(tenant_id, table_id)
    if error:
        return error

    fields = context["fields"]
    cleaned, error = _validate_record_payload(payload, fields)
    if error:
        return error

    table_identifier = context["table_identifier"]
    _ensure_dynamic_table(table_identifier, fields)

    record_id = str(uuid.uuid4())
    column_names = [sql.Identifier("record_id")] + [
        sql.Identifier(field["name"]) for field in fields
    ]
    values = [record_id] + [
        _serialize_field_value(field, cleaned[field["name"]]) for field in fields
    ]
    placeholders = sql.SQL(", ").join(sql.Placeholder() for _ in values)
    query = sql.SQL(
        "INSERT INTO {table} ({columns}) VALUES ({placeholders}) RETURNING {columns}"
    ).format(
        table=table_identifier,
        columns=sql.SQL(", ").join(column_names),
        placeholders=placeholders,
    )
    row = db.fetchone(query, values)
    return jsonify({"record": row}), 201


@tables_bp.get("/api/t/<tenant_id>/tables/<table_id>/<record_id>")
@require_login
def tenant_table_get_record(tenant_id: str, table_id: str, record_id: str):
    guard = require_tenant_access(tenant_id)
    if guard:
        return guard

    try:
        uuid.UUID(record_id)
    except ValueError:
        return jsonify({"error": "invalid_record_id"}), 400

    context, error = _resolve_table_context(tenant_id, table_id)
    if error:
        return error

    fields = context["fields"]
    table_identifier = context["table_identifier"]
    _ensure_dynamic_table(table_identifier, fields)

    column_names = [
        sql.Identifier("record_id"),
        sql.Identifier("created_at"),
        sql.Identifier("updated_at"),
    ] + [sql.Identifier(field["name"]) for field in fields]
    query = sql.SQL(
        "SELECT {columns} FROM {table} WHERE record_id = %s"
    ).format(
        columns=sql.SQL(", ").join(column_names),
        table=table_identifier,
    )
    row = db.fetchone(query, (record_id,))
    if not row:
        return jsonify({"error": "record_not_found"}), 404
    return jsonify({"record": row}), 200


@tables_bp.put("/api/t/<tenant_id>/tables/<table_id>/<record_id>")
@require_login
def tenant_table_update_record(tenant_id: str, table_id: str, record_id: str):
    guard = require_tenant_access(tenant_id)
    if guard:
        return guard

    try:
        uuid.UUID(record_id)
    except ValueError:
        return jsonify({"error": "invalid_record_id"}), 400

    payload, error = json_body()
    if error:
        return error

    context, error = _resolve_table_context(tenant_id, table_id)
    if error:
        return error

    fields = context["fields"]
    cleaned, error = _validate_record_payload(payload, fields)
    if error:
        return error

    table_identifier = context["table_identifier"]
    _ensure_dynamic_table(table_identifier, fields)

    assignments = sql.SQL(", ").join(
        sql.SQL("{column} = %s").format(column=sql.Identifier(field["name"]))
        for field in fields
    )
    values = [
        _serialize_field_value(field, cleaned[field["name"]]) for field in fields
    ]
    values.append(record_id)
    query = sql.SQL(
        """
        UPDATE {table}
        SET {assignments}, updated_at = now()
        WHERE record_id = %s
        RETURNING {columns}
        """
    ).format(
        table=table_identifier,
        assignments=assignments,
        columns=sql.SQL(", ").join(
            [sql.Identifier("record_id"), sql.Identifier("created_at"), sql.Identifier("updated_at")]
            + [sql.Identifier(field["name"]) for field in fields]
        ),
    )
    row = db.fetchone(query, values)
    if not row:
        return jsonify({"error": "record_not_found"}), 404
    return jsonify({"record": row}), 200


@tables_bp.delete("/api/t/<tenant_id>/tables/<table_id>/<record_id>")
@require_login
def tenant_table_delete_record(tenant_id: str, table_id: str, record_id: str):
    guard = require_tenant_access(tenant_id)
    if guard:
        return guard

    try:
        uuid.UUID(record_id)
    except ValueError:
        return jsonify({"error": "invalid_record_id"}), 400

    context, error = _resolve_table_context(tenant_id, table_id)
    if error:
        return error

    table_identifier = context["table_identifier"]
    _ensure_dynamic_table(table_identifier, context["fields"])

    query = sql.SQL(
        "DELETE FROM {table} WHERE record_id = %s RETURNING record_id"
    ).format(table=table_identifier)
    row = db.fetchone(query, (record_id,))
    if not row:
        return jsonify({"error": "record_not_found"}), 404
    return jsonify({"deleted": True, "record_id": record_id}), 200


@tables_bp.get("/api/samras/<domain>/<int:version>/node/<address>")
def samras_node(domain: str, version: int, address: str):
    layout = samras_layout_lookup(domain, version)
    if not layout:
        return jsonify({"error": "samras_layout_not_found"}), 404

    address_parts = parse_samras_address(address)
    if not address_parts:
        return jsonify({"error": "invalid_address"}), 400
    if not samras_address_in_stream(address_parts, layout["count_stream"]):
        return jsonify({"error": "address_not_found"}), 404

    node = samras_find_node(layout.get("traversal_spec"), address_parts)
    return jsonify({
        "domain": domain,
        "version": version,
        "address": samras_node_key(address_parts),
        "node": node,
    }), 200
