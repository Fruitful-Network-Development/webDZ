"""Admin UI and schema registry APIs."""
from __future__ import annotations

import base64
import binascii
import json
import uuid
from typing import Any, Dict

from flask import Blueprint, abort, jsonify, render_template, request

import db
from authz import get_current_user, is_root_admin, require_root_admin
from routes.common import (
    json_body,
    load_tenant_or_abort,
    load_tenant_or_error,
    require_fields,
    require_realm_role,
    require_tenant_admin,
    unwrap_api_response,
)
from tenant_registry import TenantRegistryError, list_tenants, tenant_public_view
from utils.samras import validate_archetype_field_constraints

from routes.user import admin_mss_profiles


admin_bp = Blueprint("admin", __name__)


@admin_bp.get("/admin")
@require_root_admin
def admin_index():
    user = get_current_user() or {}
    return render_template("admin/index.html", user=user), 200


@admin_bp.get("/_tenants")
@require_realm_role("root_admin")
def tenants_index():
    try:
        tenants = list_tenants()
    except TenantRegistryError as exc:
        return jsonify({"error": exc.code, "message": exc.message}), 500
    return jsonify({"tenants": tenants}), 200


@admin_bp.get("/_tenants/<tenant_id>")
@require_realm_role("root_admin")
def tenant_detail(tenant_id: str):
    tenant_cfg, error = load_tenant_or_error(tenant_id)
    if error:
        return error
    return jsonify({"tenant": tenant_public_view(tenant_cfg)}), 200


@admin_bp.get("/admin/tenants")
@require_root_admin
def admin_tenants():
    try:
        tenants = list_tenants()
    except TenantRegistryError as exc:
        abort(500, exc.message)
    return render_template("admin/tenants.html", tenants=tenants), 200


@admin_bp.get("/admin/tenants/<tenant_id>")
@require_root_admin
def admin_tenant_detail(tenant_id: str):
    tenant_cfg = load_tenant_or_abort(tenant_id)
    return render_template(
        "admin/tenant_detail.html",
        tenant=tenant_public_view(tenant_cfg),
    ), 200


@admin_bp.get("/admin/local-domains")
@require_root_admin
def admin_local_domains_page():
    payload, status = unwrap_api_response(admin_local_domains())
    if status != 200:
        abort(status)
    return render_template(
        "admin/local_domains.html",
        local_domains=payload.get("local_domains", []),
    ), 200


@admin_bp.get("/admin/archetypes")
@require_root_admin
def admin_archetypes_page():
    payload, status = unwrap_api_response(admin_archetypes())
    if status != 200:
        abort(status)
    return render_template(
        "admin/archetypes.html",
        archetypes=payload.get("archetypes", []),
        tenant_id=request.args.get("tenant_id", ""),
    ), 200


@admin_bp.get("/admin/manifest")
@require_root_admin
def admin_manifest_page():
    payload, status = unwrap_api_response(admin_manifest())
    if status != 200:
        abort(status)
    return render_template(
        "admin/manifest.html",
        manifest_rows=payload.get("manifest", []),
        tenant_id=request.args.get("tenant_id", ""),
    ), 200


@admin_bp.get("/admin/samras-layouts")
@require_root_admin
def admin_samras_layouts_page():
    payload, status = unwrap_api_response(admin_samras_layouts())
    if status != 200:
        abort(status)
    return render_template(
        "admin/samras_layouts.html",
        samras_layouts=payload.get("samras_layouts", []),
    ), 200


@admin_bp.get("/admin/users")
@require_root_admin
def admin_user_management_page():
    payload, status = unwrap_api_response(admin_mss_profiles())
    if status != 200:
        abort(status)
    return render_template(
        "admin/user_management.html",
        mss_profiles=payload.get("mss_profiles", []),
    ), 200


@admin_bp.get("/api/admin/local-domain")
@require_root_admin
def admin_local_domains():
    domains = db.fetchall(
        "SELECT local_id, title FROM platform.local_domain ORDER BY title"
    )
    return jsonify({"local_domains": domains}), 200


@admin_bp.post("/api/admin/local-domain")
@require_root_admin
def admin_local_domain_create():
    payload, error = json_body()
    if error:
        return error
    error = require_fields(payload, ["local_id", "title"])
    if error:
        return error

    local_id = payload["local_id"]
    title = payload["title"]
    if not isinstance(local_id, str) or not local_id.strip():
        return jsonify({"error": "invalid_local_id"}), 400
    if not isinstance(title, str) or not title.strip():
        return jsonify({"error": "invalid_title"}), 400
    try:
        uuid.UUID(local_id)
    except ValueError:
        return jsonify({"error": "invalid_local_id"}), 400

    db.execute(
        "INSERT INTO platform.local_domain (local_id, title) VALUES (%s, %s)",
        (local_id, title.strip()),
    )
    return jsonify({"local_id": local_id, "title": title.strip()}), 201


@admin_bp.get("/api/admin/archetypes")
def admin_archetypes():
    user = get_current_user()
    if not user:
        return jsonify({"error": "not_authenticated"}), 401

    tenant_id = request.args.get("tenant_id")
    if tenant_id:
        guard = require_tenant_admin(tenant_id)
        if guard:
            return guard
        archetypes = db.fetchall(
            """
            SELECT id, tenant_id, name, version, created_at
            FROM platform.archetype
            WHERE tenant_id = %s
            ORDER BY created_at DESC
            """,
            (tenant_id,),
        )
    else:
        if not is_root_admin(user):
            return jsonify({"error": "missing_tenant"}), 400
        archetypes = db.fetchall(
            """
            SELECT id, tenant_id, name, version, created_at
            FROM platform.archetype
            ORDER BY created_at DESC
            """
        )

    ids = [row["id"] for row in archetypes]
    fields_by_archetype: Dict[str, list[Dict[str, Any]]] = {}
    if ids:
        field_rows = db.fetchall(
            """
            SELECT archetype_id, position, name, type, ref_domain, constraints
            FROM platform.archetype_field
            WHERE archetype_id = ANY(%s)
            ORDER BY archetype_id, position
            """,
            (ids,),
        )
        for row in field_rows:
            fields_by_archetype.setdefault(str(row["archetype_id"]), []).append({
                "position": row["position"],
                "name": row["name"],
                "type": row["type"],
                "ref_domain": row["ref_domain"],
                "constraints": row["constraints"],
            })

    response = []
    for archetype in archetypes:
        archetype_id = str(archetype["id"])
        response.append({
            "id": archetype_id,
            "tenant_id": archetype["tenant_id"],
            "name": archetype["name"],
            "version": archetype["version"],
            "created_at": archetype["created_at"],
            "fields": fields_by_archetype.get(archetype_id, []),
        })
    return jsonify({"archetypes": response}), 200


@admin_bp.post("/api/admin/archetypes")
def admin_archetypes_create():
    payload, error = json_body()
    if error:
        return error
    error = require_fields(payload, ["tenant_id", "name", "fields"])
    if error:
        return error

    tenant_id = payload["tenant_id"]
    name = payload["name"]
    fields = payload["fields"]
    if not isinstance(tenant_id, str) or not tenant_id.strip():
        return jsonify({"error": "invalid_tenant_id"}), 400
    if not isinstance(name, str) or not name.strip():
        return jsonify({"error": "invalid_name"}), 400
    if not isinstance(fields, list) or not fields:
        return jsonify({"error": "invalid_fields"}), 400

    guard = require_tenant_admin(tenant_id)
    if guard:
        return guard

    archetype_id = str(uuid.uuid4())
    version = 1
    db.execute(
        """
        INSERT INTO platform.archetype (id, tenant_id, name, version)
        VALUES (%s, %s, %s, %s)
        """,
        (archetype_id, tenant_id.strip(), name.strip(), version),
    )

    field_rows = []
    for field in fields:
        if not isinstance(field, dict):
            return jsonify({"error": "invalid_field"}), 400
        error = require_fields(field, ["position", "name", "type"])
        if error:
            return error
        position = field["position"]
        field_name = field["name"]
        field_type = field["type"]
        ref_domain = field.get("ref_domain")
        constraints = field.get("constraints")

        if not isinstance(position, int):
            return jsonify({"error": "invalid_position"}), 400
        if not isinstance(field_name, str) or not field_name.strip():
            return jsonify({"error": "invalid_field_name"}), 400
        if not isinstance(field_type, str) or not field_type.strip():
            return jsonify({"error": "invalid_field_type"}), 400
        if ref_domain is not None and not isinstance(ref_domain, str):
            return jsonify({"error": "invalid_ref_domain"}), 400
        if constraints is not None and not isinstance(constraints, dict):
            return jsonify({"error": "invalid_constraints"}), 400
        constraint_error = validate_archetype_field_constraints(ref_domain, constraints)
        if constraint_error:
            return jsonify({"error": constraint_error}), 400

        db.execute(
            """
            INSERT INTO platform.archetype_field
            (archetype_id, position, name, type, ref_domain, constraints)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                archetype_id,
                position,
                field_name.strip(),
                field_type.strip(),
                ref_domain,
                json.dumps(constraints) if constraints is not None else None,
            ),
        )
        field_rows.append({
            "position": position,
            "name": field_name.strip(),
            "type": field_type.strip(),
            "ref_domain": ref_domain,
            "constraints": constraints,
        })

    return jsonify({
        "id": archetype_id,
        "tenant_id": tenant_id.strip(),
        "name": name.strip(),
        "version": version,
        "fields": field_rows,
    }), 201


@admin_bp.get("/api/admin/manifest")
def admin_manifest():
    user = get_current_user()
    if not user:
        return jsonify({"error": "not_authenticated"}), 401

    tenant_id = request.args.get("tenant_id")
    if tenant_id:
        guard = require_tenant_admin(tenant_id)
        if guard:
            return guard
        rows = db.fetchall(
            """
            SELECT table_id, tenant_id, archetype_id
            FROM platform.manifest
            WHERE tenant_id = %s
            ORDER BY table_id
            """,
            (tenant_id,),
        )
    else:
        if not is_root_admin(user):
            return jsonify({"error": "missing_tenant"}), 400
        rows = db.fetchall(
            """
            SELECT table_id, tenant_id, archetype_id
            FROM platform.manifest
            ORDER BY tenant_id, table_id
            """
        )

    return jsonify({"manifest": rows}), 200


@admin_bp.post("/api/admin/manifest")
def admin_manifest_create():
    payload, error = json_body()
    if error:
        return error
    error = require_fields(payload, ["tenant_id", "table_id", "archetype_id"])
    if error:
        return error

    tenant_id = payload["tenant_id"]
    table_id = payload["table_id"]
    archetype_id = payload["archetype_id"]
    if not isinstance(tenant_id, str) or not tenant_id.strip():
        return jsonify({"error": "invalid_tenant_id"}), 400
    if not isinstance(table_id, str) or not table_id.strip():
        return jsonify({"error": "invalid_table_id"}), 400
    if not isinstance(archetype_id, str) or not archetype_id.strip():
        return jsonify({"error": "invalid_archetype_id"}), 400

    guard = require_tenant_admin(tenant_id)
    if guard:
        return guard

    db.execute(
        """
        INSERT INTO platform.manifest (table_id, tenant_id, archetype_id)
        VALUES (%s, %s, %s)
        """,
        (table_id.strip(), tenant_id.strip(), archetype_id.strip()),
    )
    return jsonify({
        "table_id": table_id.strip(),
        "tenant_id": tenant_id.strip(),
        "archetype_id": archetype_id.strip(),
    }), 201


@admin_bp.get("/api/admin/samras-layouts")
@require_root_admin
def admin_samras_layouts():
    layouts = db.fetchall(
        """
        SELECT domain, version, count_stream, traversal_spec
        FROM platform.samras_layout
        ORDER BY domain, version
        """
    )
    response = []
    for row in layouts:
        count_stream = row["count_stream"]
        if count_stream is not None:
            count_stream = base64.b64encode(bytes(count_stream)).decode("utf-8")
        response.append({
            "domain": row["domain"],
            "version": row["version"],
            "count_stream": count_stream,
            "traversal_spec": row["traversal_spec"],
        })
    return jsonify({"samras_layouts": response}), 200


@admin_bp.post("/api/admin/samras-layouts")
@require_root_admin
def admin_samras_layouts_create():
    payload, error = json_body()
    if error:
        return error
    error = require_fields(payload, ["domain", "version", "count_stream", "traversal_spec"])
    if error:
        return error

    domain = payload["domain"]
    version = payload["version"]
    count_stream = payload["count_stream"]
    traversal_spec = payload["traversal_spec"]

    if not isinstance(domain, str) or not domain.strip():
        return jsonify({"error": "invalid_domain"}), 400
    if not isinstance(version, int):
        return jsonify({"error": "invalid_version"}), 400
    if not isinstance(count_stream, str):
        return jsonify({"error": "invalid_count_stream"}), 400
    if not isinstance(traversal_spec, dict):
        return jsonify({"error": "invalid_traversal_spec"}), 400

    try:
        count_bytes = base64.b64decode(count_stream.encode("utf-8"), validate=True)
    except (ValueError, binascii.Error):
        return jsonify({"error": "invalid_count_stream"}), 400

    db.execute(
        """
        INSERT INTO platform.samras_layout (domain, version, count_stream, traversal_spec)
        VALUES (%s, %s, %s, %s)
        """,
        (domain.strip(), version, count_bytes, json.dumps(traversal_spec)),
    )
    return jsonify({
        "domain": domain.strip(),
        "version": version,
        "count_stream": count_stream,
        "traversal_spec": traversal_spec,
    }), 201
