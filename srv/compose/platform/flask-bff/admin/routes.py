"""Admin UI and schema registry APIs."""
from __future__ import annotations

import base64
import binascii
import json
import uuid
from typing import Any, Dict

from flask import Blueprint, abort, current_app, jsonify, redirect, render_template, request
from psycopg2 import sql

import db
from core.mss_profile import current_msn_id
from core.policy import get_current_user, is_root_admin, require_root_admin
from core.domains.samras import validate_archetype_field_constraints
from routes.common import (
    json_body,
    load_tenant_or_abort,
    load_tenant_or_error,
    require_fields,
    require_realm_role,
    require_tenant_admin,
    unwrap_api_response,
)
from tenants.registry import (
    TenantExistsError,
    TenantIdError,
    TenantIndexError,
    TenantNotFoundError,
    TenantRegistryError,
    TenantValidationError,
    create_tenant,
    delete_tenant,
    list_tenants,
    load_tenant,
    tenant_public_view,
    update_tenant,
)
from utils.general_tables import general_table_name

from routes.user import admin_mss_profiles


admin_bp = Blueprint("admin", __name__)


def _log_admin_event(action: str, payload: Dict[str, Any]) -> None:
    data = {"event": action}
    data.update(payload)
    try:
        current_app.logger.info(json.dumps(data, separators=(",", ":")))
    except RuntimeError:
        pass


def _tenant_error_response(exc: TenantRegistryError):
    status = 500
    if isinstance(exc, TenantNotFoundError):
        status = 404
    elif isinstance(exc, (TenantValidationError, TenantIdError)):
        status = 400
    elif isinstance(exc, TenantExistsError):
        status = 409
    elif isinstance(exc, TenantIndexError):
        status = 500
    payload: Dict[str, Any] = {"error": exc.code, "message": exc.message}
    if exc.details:
        payload["details"] = exc.details
    return jsonify(payload), status


def _load_manifest_entry(tenant_id: str, table_local_id: str):
    return db.fetchone(
        """
        SELECT table_id, archetype_id
        FROM platform.manifest
        WHERE tenant_id = %s AND table_id = %s
        """,
        (tenant_id, table_local_id),
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


def _load_local_domain(table_local_id: str):
    return db.fetchone(
        "SELECT local_id, title FROM platform.local_domain WHERE local_id = %s",
        (table_local_id,),
    )


def _load_archetype(archetype_id: str):
    return db.fetchone(
        """
        SELECT id, tenant_id, name, version
        FROM platform.archetype
        WHERE id = %s
        """,
        (archetype_id,),
    )


def _load_general_table_entry(tenant_id: str, table_local_id: str):
    return db.fetchone(
        """
        SELECT tenant_id, table_local_id, mode, table_name, archetype_id, msn_id, enabled,
               created_at, updated_at
        FROM platform.general_table
        WHERE tenant_id = %s AND table_local_id = %s
        """,
        (tenant_id, table_local_id),
    )


def _ensure_general_table(table_name: str) -> None:
    query = sql.SQL(
        """
        CREATE TABLE IF NOT EXISTS {table} (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            created_at TIMESTAMPTZ DEFAULT now(),
            updated_at TIMESTAMPTZ DEFAULT now(),
            data JSONB NOT NULL
        )
        """
    ).format(table=sql.Identifier(table_name))
    db.execute(query)


@admin_bp.get("/admin")
@require_root_admin
def admin_index():
    user = get_current_user() or {}
    return render_template("admin/index.html", user=user), 200


@admin_bp.get("/admin/overview")
@require_root_admin
def admin_overview():
    return redirect("/admin")


@admin_bp.get("/_tenants")
@require_realm_role("root_admin")
def tenants_index():
    try:
        tenants = list_tenants()
    except TenantRegistryError as exc:
        return jsonify({"error": exc.code, "message": exc.message}), 500
    return jsonify({"tenants": tenants}), 200


@admin_bp.get("/api/admin/tenants")
@require_root_admin
def admin_tenants_api():
    try:
        tenants = list_tenants()
    except TenantRegistryError as exc:
        return jsonify({"error": exc.code, "message": exc.message}), 500
    return jsonify({"tenants": tenants}), 200


@admin_bp.post("/api/admin/tenants")
@require_root_admin
def admin_tenant_create():
    payload, error = json_body()
    if error:
        return error
    try:
        tenant_cfg = create_tenant(payload)
    except TenantRegistryError as exc:
        return _tenant_error_response(exc)
    return jsonify({"tenant": tenant_public_view(tenant_cfg)}), 201


@admin_bp.get("/api/admin/tenants/<tenant_id>")
@require_root_admin
def admin_tenant_get(tenant_id: str):
    try:
        tenant_cfg = load_tenant(tenant_id)
    except TenantRegistryError as exc:
        return _tenant_error_response(exc)
    return jsonify({"tenant": tenant_public_view(tenant_cfg)}), 200


@admin_bp.put("/api/admin/tenants/<tenant_id>")
@require_root_admin
def admin_tenant_update(tenant_id: str):
    payload, error = json_body()
    if error:
        return error
    try:
        tenant_cfg = update_tenant(tenant_id, payload)
    except TenantRegistryError as exc:
        return _tenant_error_response(exc)
    return jsonify({"tenant": tenant_public_view(tenant_cfg)}), 200


@admin_bp.delete("/api/admin/tenants/<tenant_id>")
@require_root_admin
def admin_tenant_delete(tenant_id: str):
    hard = request.args.get("hard") == "1"
    try:
        result = delete_tenant(tenant_id, hard=hard)
    except TenantRegistryError as exc:
        return _tenant_error_response(exc)
    if hard:
        return jsonify({"tenant": result}), 200
    return jsonify({"tenant": tenant_public_view(result)}), 200


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


@admin_bp.get("/admin/tenant/<tenant_id>")
@require_root_admin
def admin_tenant_detail_alias(tenant_id: str):
    return redirect(f"/admin/tenants/{tenant_id}")


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


@admin_bp.get("/admin/local-domain")
@require_root_admin
def admin_local_domains_page_alias():
    qs = request.query_string.decode("utf-8")
    suffix = f"?{qs}" if qs else ""
    return redirect(f"/admin/local-domains{suffix}")


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


@admin_bp.get("/admin/samras")
@require_root_admin
def admin_samras_layouts_page_alias():
    qs = request.query_string.decode("utf-8")
    suffix = f"?{qs}" if qs else ""
    return redirect(f"/admin/samras-layouts{suffix}")


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


@admin_bp.get("/admin/services")
@require_root_admin
def admin_services_page():
    return render_template("admin/services.html"), 200


@admin_bp.get("/admin/tables")
@require_root_admin
def admin_tables_page():
    tenant_id = request.args.get("tenant_id", "")
    payload, status = unwrap_api_response(admin_tables_list())
    if status != 200:
        abort(status)
    return render_template(
        "admin/tables.html",
        tables=payload.get("tables", []),
        tenant_id=tenant_id,
    ), 200


@admin_bp.get("/admin/tables/<table_local_id>/records")
@require_root_admin
def admin_table_records_page(table_local_id: str):
    tenant_id = request.args.get("tenant_id")
    if not tenant_id:
        abort(400, "missing tenant_id")

    manifest_entry = _load_manifest_entry(tenant_id, table_local_id)
    if not manifest_entry:
        abort(404, "manifest not found")
    archetype_id = str(manifest_entry["archetype_id"])
    archetype = _load_archetype(archetype_id)
    fields = _load_archetype_fields(archetype_id)
    table_entry = _load_general_table_entry(tenant_id, table_local_id)

    return render_template(
        "admin/table_records.html",
        tenant_id=tenant_id,
        table_local_id=table_local_id,
        archetype=archetype,
        archetype_fields=fields,
        table_entry=table_entry,
    ), 200


@admin_bp.get("/admin/lists")
@require_root_admin
def admin_lists_page():
    return render_template("admin/lists.html"), 200


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

    ids = [str(row["id"]) for row in archetypes]
    fields_by_archetype: Dict[str, list[Dict[str, Any]]] = {}
    if ids:
        field_rows = db.fetchall(
            """
            SELECT archetype_id, position, name, type, ref_domain, constraints
            FROM platform.archetype_field
            WHERE archetype_id = ANY(%s::uuid[])
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


@admin_bp.post("/api/admin/tables")
@require_root_admin
def admin_tables_create():
    payload, error = json_body()
    if error:
        return error
    error = require_fields(payload, ["tenant_id", "table_local_id", "mode"])
    if error:
        return error

    tenant_id = payload["tenant_id"]
    table_local_id = payload["table_local_id"]
    mode = payload["mode"]

    if not isinstance(tenant_id, str) or not tenant_id.strip():
        return jsonify({"error": "invalid_tenant_id"}), 400
    if not isinstance(table_local_id, str) or not table_local_id.strip():
        return jsonify({"error": "invalid_table_local_id"}), 400
    if not isinstance(mode, str) or not mode.strip():
        return jsonify({"error": "invalid_mode"}), 400
    if mode.strip() != "general":
        return jsonify({"error": "unsupported_table_mode"}), 400

    try:
        uuid.UUID(table_local_id)
    except ValueError:
        return jsonify({"error": "invalid_table_local_id"}), 400

    manifest_entry = _load_manifest_entry(tenant_id.strip(), table_local_id.strip())
    if not manifest_entry:
        return jsonify({
            "error": "manifest_not_found",
            "message": "Manifest binding is required before provisioning.",
        }), 409

    local_domain = _load_local_domain(table_local_id.strip())
    if not local_domain:
        return jsonify({
            "error": "local_domain_not_found",
            "message": "Local domain entry is required before provisioning.",
        }), 409

    archetype_id = str(manifest_entry["archetype_id"])
    archetype = _load_archetype(archetype_id)
    if not archetype:
        return jsonify({
            "error": "archetype_not_found",
            "message": "Archetype is missing for manifest binding.",
        }), 409

    fields = _load_archetype_fields(archetype_id)
    if not fields:
        return jsonify({
            "error": "archetype_fields_not_found",
            "message": "Archetype fields are required before provisioning.",
        }), 409

    msn_id = current_msn_id()
    if not msn_id:
        return jsonify({"error": "missing_msn_profile"}), 400

    existing = _load_general_table_entry(tenant_id.strip(), table_local_id.strip())
    if existing:
        _ensure_general_table(existing["table_name"])
        if not existing.get("enabled", True):
            db.execute(
                """
                UPDATE platform.general_table
                SET enabled = TRUE, updated_at = now()
                WHERE tenant_id = %s AND table_local_id = %s
                """,
                (tenant_id.strip(), table_local_id.strip()),
            )
        _log_admin_event("admin_table_provisioned", {
            "tenant_id": tenant_id.strip(),
            "table_local_id": table_local_id.strip(),
            "table_name": existing["table_name"],
            "mode": existing["mode"],
            "archetype_id": str(existing["archetype_id"]),
            "status": "existing",
        })
        return jsonify({
            "tenant_id": tenant_id.strip(),
            "table_local_id": table_local_id.strip(),
            "mode": existing["mode"],
            "table_name": existing["table_name"],
            "archetype_id": str(existing["archetype_id"]),
            "local_domain": local_domain,
            "archetype": archetype,
            "archetype_fields": fields,
            "status": "already_provisioned",
        }), 200

    table_name = general_table_name(msn_id, table_local_id.strip())
    _ensure_general_table(table_name)

    db.execute(
        """
        INSERT INTO platform.general_table
        (tenant_id, table_local_id, mode, table_name, archetype_id, msn_id, enabled)
        VALUES (%s, %s, %s, %s, %s, %s, TRUE)
        """,
        (
            tenant_id.strip(),
            table_local_id.strip(),
            mode.strip(),
            table_name,
            archetype_id,
            msn_id,
        ),
    )

    _log_admin_event("admin_table_provisioned", {
        "tenant_id": tenant_id.strip(),
        "table_local_id": table_local_id.strip(),
        "table_name": table_name,
        "mode": mode.strip(),
        "archetype_id": archetype_id,
        "status": "created",
    })

    return jsonify({
        "tenant_id": tenant_id.strip(),
        "table_local_id": table_local_id.strip(),
        "mode": mode.strip(),
        "table_name": table_name,
        "archetype_id": archetype_id,
        "local_domain": local_domain,
        "archetype": archetype,
        "archetype_fields": fields,
    }), 201


@admin_bp.get("/api/admin/tables")
@require_root_admin
def admin_tables_list():
    tenant_id = request.args.get("tenant_id")
    if tenant_id:
        rows = db.fetchall(
            """
            SELECT gt.tenant_id, gt.table_local_id, gt.mode, gt.table_name, gt.archetype_id,
                   gt.msn_id, gt.enabled, gt.created_at, gt.updated_at, ld.title,
                   a.name AS archetype_name, a.version AS archetype_version
            FROM platform.general_table gt
            LEFT JOIN platform.local_domain ld ON ld.local_id = gt.table_local_id
            LEFT JOIN platform.archetype a ON a.id = gt.archetype_id
            WHERE gt.tenant_id = %s
            ORDER BY gt.created_at DESC
            """,
            (tenant_id,),
        )
    else:
        rows = db.fetchall(
            """
            SELECT gt.tenant_id, gt.table_local_id, gt.mode, gt.table_name, gt.archetype_id,
                   gt.msn_id, gt.enabled, gt.created_at, gt.updated_at, ld.title,
                   a.name AS archetype_name, a.version AS archetype_version
            FROM platform.general_table gt
            LEFT JOIN platform.local_domain ld ON ld.local_id = gt.table_local_id
            LEFT JOIN platform.archetype a ON a.id = gt.archetype_id
            ORDER BY gt.created_at DESC
            """
        )
    return jsonify({"tables": rows}), 200


@admin_bp.delete("/api/admin/tables/<table_local_id>")
@require_root_admin
def admin_tables_delete(table_local_id: str):
    tenant_id = request.args.get("tenant_id")
    if not tenant_id or not isinstance(tenant_id, str):
        return jsonify({"error": "missing_tenant_id"}), 400
    try:
        uuid.UUID(table_local_id)
    except ValueError:
        return jsonify({"error": "invalid_table_local_id"}), 400

    row = db.fetchone(
        """
        UPDATE platform.general_table
        SET enabled = FALSE, updated_at = now()
        WHERE tenant_id = %s AND table_local_id = %s
        RETURNING table_name, enabled
        """,
        (tenant_id, table_local_id),
    )
    if not row:
        return jsonify({"error": "table_not_found"}), 404
    _log_admin_event("admin_table_disabled", {
        "tenant_id": tenant_id,
        "table_local_id": table_local_id,
        "table_name": row["table_name"],
    })
    return jsonify({
        "table_local_id": table_local_id,
        "tenant_id": tenant_id,
        "table_name": row["table_name"],
        "disabled": True,
    }), 200


@admin_bp.post("/api/admin/lists")
@require_root_admin
def admin_lists_create():
    payload, error = json_body()
    if error:
        return error
    error = require_fields(payload, ["tenant_id", "list_local_id", "members"])
    if error:
        return error

    tenant_id = payload["tenant_id"]
    list_local_id = payload["list_local_id"]
    members = payload["members"]
    name = payload.get("name")

    if not isinstance(tenant_id, str) or not tenant_id.strip():
        return jsonify({"error": "invalid_tenant_id"}), 400
    if not isinstance(list_local_id, str) or not list_local_id.strip():
        return jsonify({"error": "invalid_list_local_id"}), 400
    if not isinstance(members, list):
        return jsonify({"error": "invalid_members"}), 400
    if name is not None and not isinstance(name, str):
        return jsonify({"error": "invalid_name"}), 400

    try:
        uuid.UUID(list_local_id)
    except ValueError:
        return jsonify({"error": "invalid_list_local_id"}), 400

    cleaned_members = []
    for member in members:
        if not isinstance(member, str) or not member.strip():
            return jsonify({"error": "invalid_member"}), 400
        try:
            uuid.UUID(member)
        except ValueError:
            return jsonify({"error": "invalid_member"}), 400
        cleaned_members.append(member.strip())

    if db.fetchone(
        "SELECT 1 FROM platform.local_list WHERE list_local_id = %s",
        (list_local_id.strip(),),
    ):
        return jsonify({"error": "list_exists"}), 409

    existing = set()
    if cleaned_members:
        rows = db.fetchall(
            "SELECT local_id FROM platform.local_domain WHERE local_id = ANY(%s::uuid[])",
            (cleaned_members,),
        )
        existing = {str(row["local_id"]) for row in rows}
    missing = [member for member in cleaned_members if member not in existing]
    if missing:
        return jsonify({
            "error": "local_domain_not_found",
            "message": "All list members must exist in local_domain.",
            "missing": missing,
        }), 409

    conn = db.get_conn()
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO platform.local_list (list_local_id, tenant_id, name)
            VALUES (%s, %s, %s)
            """,
            (list_local_id.strip(), tenant_id.strip(), name.strip() if isinstance(name, str) else None),
        )
        for ordinal, local_id in enumerate(cleaned_members):
            cur.execute(
                """
                INSERT INTO platform.local_list_member (list_local_id, ordinal, local_id)
                VALUES (%s, %s, %s)
                """,
                (list_local_id.strip(), ordinal, local_id),
            )
    conn.commit()

    _log_admin_event("admin_list_created", {
        "tenant_id": tenant_id.strip(),
        "list_local_id": list_local_id.strip(),
        "member_count": len(cleaned_members),
    })

    return jsonify({
        "list_local_id": list_local_id.strip(),
        "tenant_id": tenant_id.strip(),
        "name": name.strip() if isinstance(name, str) else None,
        "members": cleaned_members,
    }), 201


@admin_bp.get("/api/admin/lists/<list_local_id>")
@require_root_admin
def admin_lists_get(list_local_id: str):
    try:
        uuid.UUID(list_local_id)
    except ValueError:
        return jsonify({"error": "invalid_list_local_id"}), 400

    list_row = db.fetchone(
        """
        SELECT list_local_id, tenant_id, name, created_at, updated_at
        FROM platform.local_list
        WHERE list_local_id = %s
        """,
        (list_local_id,),
    )
    if not list_row:
        return jsonify({"error": "list_not_found"}), 404

    members = db.fetchall(
        """
        SELECT m.ordinal, m.local_id, d.title
        FROM platform.local_list_member m
        JOIN platform.local_domain d ON d.local_id = m.local_id
        WHERE m.list_local_id = %s
        ORDER BY m.ordinal
        """,
        (list_local_id,),
    )

    list_row["members"] = members
    return jsonify({"list": list_row}), 200


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
