"""Flask BFF (Keycloak-only, DB-free)

This version reflects the **current consolidated platform state**:

- Keycloak is the sole stateful dependency (no platform Postgres / no separate DB).
- OIDC Authorization Code flow against Keycloak.
- Server-side token exchange.
- Session cookie handled by the BFF (no tokens stored in browser storage).
- Designed for Phase 3 (internal-only via SSH tunnel) and Phase 4 (public HTTPS) via env toggles.

Required env:
- OIDC_ISSUER                e.g. https://auth.fruitfulnetworkdevelopment.com/realms/fruitful
- OIDC_CLIENT_ID             e.g. flask-bff
- OIDC_CLIENT_SECRET         (Keycloak client secret)
- SESSION_SECRET             (Flask session secret)

Optional env:
- PUBLIC_BASE_URL            e.g. https://api.fruitfulnetworkdevelopment.com
                             If not set, computed from X-Forwarded-* headers.
- COOKIE_SECURE              true|false (default: false)
                             Set true when served over HTTPS (Phase 4).
"""

from __future__ import annotations

import base64
import binascii
import json
import os
import re
import time
import uuid
from functools import wraps
from typing import Any, Dict, Optional
from urllib.parse import urlencode

import requests
from psycopg2 import sql
from psycopg2.extras import Json
from flask import Flask, abort, jsonify, redirect, render_template, request, session, url_for
from jinja2 import TemplateNotFound

import db
from authz import get_current_user, is_root_admin, is_tenant_admin, require_root_admin
from tenant_registry import (
    TenantNotFoundError,
    TenantRegistryError,
    TenantValidationError,
    list_tenants,
    load_tenant,
    tenant_public_view,
    validate_return_to,
)


# ----------------------------
# Configuration
# ----------------------------

def _require_env(name: str) -> str:
    val = os.getenv(name)
    if not val:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return val


OIDC_ISSUER = _require_env("OIDC_ISSUER").rstrip("/")
OIDC_CLIENT_ID = _require_env("OIDC_CLIENT_ID")
OIDC_CLIENT_SECRET = _require_env("OIDC_CLIENT_SECRET")
SESSION_SECRET = _require_env("SESSION_SECRET")

PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "").rstrip("/")
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() == "true"

DEMO_TENANT_ID = "cuyahogaterravita"
DEMO_LOCAL_DOMAIN_ID = "6c3152b3-2d2c-4f10-8fcf-3fca0d2c7af1"
DEMO_ARCHETYPE_ID = "e9fa1d2b-2a25-478a-91ef-1b31f5111c92"
DEMO_TABLE_ID = DEMO_LOCAL_DOMAIN_ID


# ----------------------------
# Flask app
# ----------------------------

app = Flask(__name__)
app.secret_key = SESSION_SECRET

# Session cookie policy:
# - Phase 3 (SSH tunnel via http://localhost:8001): COOKIE_SECURE=false
# - Phase 4 (public HTTPS): COOKIE_SECURE=true
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=COOKIE_SECURE,
)


@app.before_serving
def _init_db() -> None:
    db.get_conn()
    _seed_demo_data()


@app.after_serving
def _close_db() -> None:
    db.close_conn()


# ----------------------------
# OIDC discovery (cached)
# ----------------------------

_discovery_cache: Dict[str, Any] = {}
_discovery_cache_at: float = 0.0
_DISCOVERY_TTL_SECONDS = 300


def _get_discovery() -> Dict[str, Any]:
    global _discovery_cache, _discovery_cache_at
    now = time.time()
    if _discovery_cache and (now - _discovery_cache_at) < _DISCOVERY_TTL_SECONDS:
        return _discovery_cache

    url = f"{OIDC_ISSUER}/.well-known/openid-configuration"
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    _discovery_cache = resp.json()
    _discovery_cache_at = now
    return _discovery_cache


def _public_base_url() -> str:
    """Compute external base URL for redirects when behind NGINX."""
    if PUBLIC_BASE_URL:
        return PUBLIC_BASE_URL

    scheme = request.headers.get("X-Forwarded-Proto", request.scheme)
    host = request.headers.get("X-Forwarded-Host", request.host)
    return f"{scheme}://{host}"


def _callback_url() -> str:
    return f"{_public_base_url()}{url_for('callback')}"

# ----------------------------
# JWT helpers (no signature verification)
# ----------------------------

def _b64url_decode(s: str) -> bytes:
    s += "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode(s.encode("utf-8"))


def jwt_payload(jwt_token: str) -> Dict[str, Any]:
    """Parse JWT payload without verifying signature (sufficient for role scaffolding)."""
    parts = jwt_token.split(".")
    if len(parts) != 3:
        return {}
    try:
        return json.loads(_b64url_decode(parts[1]))
    except Exception:
        return {}


# ----------------------------
# Session / auth helpers
# ----------------------------

def _current_user() -> Optional[Dict[str, Any]]:
    return get_current_user()


def _load_tenant_or_error(tenant_id: str):
    try:
        return load_tenant(tenant_id), None
    except TenantNotFoundError as exc:
        return None, (jsonify({"error": exc.code, "message": exc.message}), 404)
    except (TenantValidationError, TenantRegistryError) as exc:
        return None, (jsonify({"error": exc.code, "message": exc.message}), 400)


def _load_tenant_or_abort(tenant_id: str):
    try:
        return load_tenant(tenant_id)
    except TenantNotFoundError as exc:
        abort(404, exc.message)
    except (TenantValidationError, TenantRegistryError) as exc:
        abort(400, exc.message)


def require_login(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not _current_user():
            return jsonify({"error": "not_authenticated"}), 401
        return fn(*args, **kwargs)
    return wrapper


def require_tenant_context(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("tenant_id"):
            return jsonify({"error": "missing_tenant"}), 400
        return fn(*args, **kwargs)
    return wrapper


def _json_body() -> tuple[Optional[Dict[str, Any]], Optional[tuple[Any, int]]]:
    data = request.get_json(silent=True)
    if data is None:
        return None, (jsonify({"error": "invalid_json"}), 400)
    if not isinstance(data, dict):
        return None, (jsonify({"error": "invalid_json"}), 400)
    return data, None


def _require_fields(payload: Dict[str, Any], fields: list[str]) -> Optional[tuple[Any, int]]:
    missing = [field for field in fields if field not in payload]
    if missing:
        return jsonify({"error": "missing_fields", "fields": missing}), 400
    return None


def _require_tenant_admin(tenant_id: str) -> Optional[tuple[Any, int]]:
    user = get_current_user()
    if not user:
        return jsonify({"error": "not_authenticated"}), 401
    if is_root_admin(user) or is_tenant_admin(user, tenant_id):
        return None
    return jsonify({"error": "forbidden"}), 403


# ----------------------------
# Dynamic table helpers
# ----------------------------

def _seed_demo_data() -> None:
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


SAMRAS_MODES = {"exact", "group", "existential"}


def _is_samras_domain(ref_domain: Optional[str]) -> bool:
    if not ref_domain:
        return False
    return ref_domain.strip().upper().startswith("SAMRAS")


def _parse_samras_ref_domain(ref_domain: str) -> tuple[Optional[str], Optional[int]]:
    ref_domain = ref_domain.strip()
    if not _is_samras_domain(ref_domain):
        return None, None
    suffix = ref_domain[len("SAMRAS"):]
    if not suffix:
        return None, None
    suffix = suffix.lstrip(":/")
    if not suffix:
        return None, None
    parts = [part for part in re.split(r"[:/]", suffix) if part]
    if len(parts) < 2:
        return None, None
    domain = parts[0].strip()
    if not domain:
        return None, None
    try:
        version = int(parts[1])
    except ValueError:
        return None, None
    return domain, version


def _samras_layout_lookup(domain: str, version: int) -> Optional[Dict[str, Any]]:
    row = db.fetchone(
        """
        SELECT domain, version, count_stream, traversal_spec
        FROM platform.samras_layout
        WHERE domain = %s AND version = %s
        """,
        (domain, version),
    )
    if not row:
        return None
    count_stream = row.get("count_stream")
    if count_stream is None:
        count_bytes = b""
    else:
        count_bytes = bytes(count_stream)
    row["count_stream"] = [byte for byte in count_bytes]
    return row


def _parse_samras_address(address: str) -> Optional[list[int]]:
    if not isinstance(address, str):
        return None
    address = address.strip()
    if not address:
        return None
    parts = re.split(r"[./-]", address)
    parsed = []
    for part in parts:
        if not part.isdigit():
            return None
        parsed.append(int(part))
    return parsed if parsed else None


def _samras_address_in_stream(address: list[int], count_stream: list[int]) -> bool:
    if not address:
        return False
    if len(address) > len(count_stream):
        return False
    for idx, count in zip(address, count_stream):
        if idx < 0 or idx >= count:
            return False
    return True


def _samras_node_key(address: list[int]) -> str:
    return ".".join(str(part) for part in address)


def _samras_find_node(traversal_spec: Any, address: list[int]) -> Optional[Any]:
    if traversal_spec is None:
        return None
    if isinstance(traversal_spec, dict):
        nodes = traversal_spec.get("nodes")
        if isinstance(nodes, dict):
            return nodes.get(_samras_node_key(address))
    current = traversal_spec
    for idx in address:
        if isinstance(current, dict):
            children = current.get("children")
        elif isinstance(current, list):
            children = current
        else:
            return None
        if not isinstance(children, list) or idx >= len(children):
            return None
        current = children[idx]
    return current


def _resolve_samras_context(field: Dict[str, Any]) -> tuple[Optional[dict], Optional[str]]:
    constraints = field.get("constraints") or {}
    ref_domain = field.get("ref_domain")
    domain, version = _parse_samras_ref_domain(ref_domain or "")
    if not domain:
        domain = constraints.get("samras_domain") or constraints.get("domain")
    if version is None:
        version_value = constraints.get("samras_version", constraints.get("version"))
        if isinstance(version_value, int):
            version = version_value
        elif isinstance(version_value, str) and version_value.isdigit():
            version = int(version_value)
    if not domain or version is None:
        return None, "missing_samras_layout"
    layout = _samras_layout_lookup(domain, version)
    if not layout:
        return None, "missing_samras_layout"
    return layout, None


def _resolve_samras_mode(constraints: Dict[str, Any]) -> tuple[Optional[str], Optional[str]]:
    mode = constraints.get("samras_mode") or constraints.get("mode")
    if mode is None:
        return "exact", None
    if not isinstance(mode, str):
        return None, "invalid_samras_mode"
    mode = mode.strip().lower()
    if mode not in SAMRAS_MODES:
        return None, "invalid_samras_mode"
    return mode, None


def _validate_samras_reference(
    field: Dict[str, Any],
    value: Dict[str, Any],
    has_system_id: bool,
    has_system_value: bool,
) -> Optional[str]:
    constraints = field.get("constraints") or {}
    mode, error = _resolve_samras_mode(constraints)
    if error:
        return error
    if mode == "exact":
        if not has_system_id:
            return "missing_system_id"
        if has_system_value:
            return "system_value_not_allowed"
    address_value = value.get("system_id") if has_system_id else value.get("system_value")
    if not isinstance(address_value, str):
        return "invalid_samras_address"
    address = _parse_samras_address(address_value)
    if not address:
        return "invalid_samras_address"
    layout, error = _resolve_samras_context(field)
    if error:
        return error
    if not _samras_address_in_stream(address, layout["count_stream"]):
        return "invalid_samras_address"
    return None


def _validate_archetype_field_constraints(
    ref_domain: Optional[str],
    constraints: Optional[Dict[str, Any]],
) -> Optional[str]:
    if constraints is None:
        return None
    if not isinstance(constraints, dict):
        return "invalid_constraints"
    if _is_samras_domain(ref_domain):
        mode, error = _resolve_samras_mode(constraints)
        if error:
            return error
        if mode:
            constraints["samras_mode"] = mode
        return None
    if "samras_mode" in constraints:
        return "samras_mode_not_allowed"
    return None


def _load_local_domain(local_id: str):
    return db.fetchone(
        "SELECT local_id, title FROM platform.local_domain WHERE local_id = %s",
        (local_id,),
    )


def _current_msn_id() -> Optional[str]:
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


def _load_user_hierarchy(user_id: str) -> Optional[Dict[str, Any]]:
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
        if _is_samras_domain(ref_domain):
            return _validate_samras_reference(field, value, has_system_id, has_system_value)
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

    msn_id = _current_msn_id()
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
# Authorization helpers
# ----------------------------

def require_realm_role(role: str):
    """Require a Keycloak realm role captured during /callback."""
    def deco(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            u = session.get("user")
            if not u:
                return jsonify({"error": "not_authenticated"}), 401
            roles = u.get("realm_roles") or []
            if role not in roles:
                return jsonify({"error": "forbidden", "missing_role": role}), 403
            return fn(*args, **kwargs)
        return wrapper
    return deco


def require_tenant_access(tenant_id: str):
    u = get_current_user()
    if not u:
        return jsonify({"error": "not_authenticated"}), 401
    if is_root_admin(u):
        return None
    if is_tenant_admin(u, tenant_id):
        return None
    return jsonify({"error": "forbidden"}), 403


def _unwrap_api_response(result: Any) -> tuple[dict[str, Any], int]:
    if isinstance(result, tuple):
        response, status = result
    else:
        response = result
        status = response.status_code
    payload = response.get_json() if hasattr(response, "get_json") else {}
    return payload or {}, status


def _enabled_console_modules(tenant_cfg: dict[str, Any]) -> list[str]:
    modules = tenant_cfg.get("console_modules") or {}
    if isinstance(modules, dict):
        return [name for name, enabled in modules.items() if enabled]
    return list(modules)


def _require_tenant_console_access(tenant_id: str) -> tuple[dict[str, Any], Optional[Any]]:
    tenant_cfg = _load_tenant_or_abort(tenant_id)
    user = get_current_user()
    if not user:
        next_path = request.full_path
        if next_path.endswith("?"):
            next_path = next_path[:-1]
        login_url = f"/login?{urlencode({'tenant': tenant_id, 'next': next_path})}"
        return tenant_cfg, redirect(login_url)
    if not (is_root_admin(user) or is_tenant_admin(user, tenant_id)):
        abort(403)
    return tenant_cfg, None


# ----------------------------
# Routes
# ----------------------------

@app.context_processor
def inject_template_context():
    user = get_current_user()
    return {
        "current_user": user,
        "is_root_admin": is_root_admin(user) if user else False,
    }


@app.get("/health")
def health():
    return jsonify({"status": "ok"}), 200


@app.get("/admin")
@require_root_admin
def admin_index():
    user = get_current_user() or {}
    return render_template("admin/index.html", user=user), 200


@app.get("/_tenants")
@require_realm_role("root_admin")
def tenants_index():
    try:
        tenants = list_tenants()
    except TenantRegistryError as exc:
        return jsonify({"error": exc.code, "message": exc.message}), 500
    return jsonify({"tenants": tenants}), 200


@app.get("/_tenants/<tenant_id>")
@require_realm_role("root_admin")
def tenant_detail(tenant_id: str):
    tenant_cfg, error = _load_tenant_or_error(tenant_id)
    if error:
        return error
    return jsonify({"tenant": tenant_public_view(tenant_cfg)}), 200


@app.get("/admin/tenants")
@require_root_admin
def admin_tenants():
    try:
        tenants = list_tenants()
    except TenantRegistryError as exc:
        abort(500, exc.message)
    return render_template("admin/tenants.html", tenants=tenants), 200


@app.get("/admin/tenants/<tenant_id>")
@require_root_admin
def admin_tenant_detail(tenant_id: str):
    tenant_cfg = _load_tenant_or_abort(tenant_id)
    return render_template(
        "admin/tenant_detail.html",
        tenant=tenant_public_view(tenant_cfg),
    ), 200


@app.get("/admin/local-domains")
@require_root_admin
def admin_local_domains_page():
    payload, status = _unwrap_api_response(admin_local_domains())
    if status != 200:
        abort(status)
    return render_template(
        "admin/local_domains.html",
        local_domains=payload.get("local_domains", []),
    ), 200


@app.get("/admin/archetypes")
@require_root_admin
def admin_archetypes_page():
    payload, status = _unwrap_api_response(admin_archetypes())
    if status != 200:
        abort(status)
    return render_template(
        "admin/archetypes.html",
        archetypes=payload.get("archetypes", []),
        tenant_id=request.args.get("tenant_id", ""),
    ), 200


@app.get("/admin/manifest")
@require_root_admin
def admin_manifest_page():
    payload, status = _unwrap_api_response(admin_manifest())
    if status != 200:
        abort(status)
    return render_template(
        "admin/manifest.html",
        manifest_rows=payload.get("manifest", []),
        tenant_id=request.args.get("tenant_id", ""),
    ), 200


@app.get("/admin/samras-layouts")
@require_root_admin
def admin_samras_layouts_page():
    payload, status = _unwrap_api_response(admin_samras_layouts())
    if status != 200:
        abort(status)
    return render_template(
        "admin/samras_layouts.html",
        samras_layouts=payload.get("samras_layouts", []),
    ), 200


@app.get("/admin/users")
@require_root_admin
def admin_user_management_page():
    payload, status = _unwrap_api_response(admin_mss_profiles())
    if status != 200:
        abort(status)
    return render_template(
        "admin/user_management.html",
        mss_profiles=payload.get("mss_profiles", []),
    ), 200


@app.get("/t/<tenant_id>/console")
def tenant_console(tenant_id: str):
    tenant_cfg, error = _require_tenant_console_access(tenant_id)
    if error:
        return error
    enabled_modules = _enabled_console_modules(tenant_cfg)

    return render_template(
        "tenant/console.html",
        tenant_id=tenant_id,
        tenant_cfg=tenant_cfg,
        enabled_modules=enabled_modules,
    ), 200


@app.get("/t/<tenant_id>/console/<module>")
def tenant_console_module(tenant_id: str, module: str):
    tenant_cfg, error = _require_tenant_console_access(tenant_id)
    if error:
        return error

    enabled_modules = _enabled_console_modules(tenant_cfg)
    if module not in enabled_modules:
        abort(404)

    template_name = f"tenant/console_{module}.html"
    try:
        return render_template(
            template_name,
            tenant_id=tenant_id,
            tenant_cfg=tenant_cfg,
            module=module,
            enabled_modules=enabled_modules,
            demo_table_id=DEMO_TABLE_ID,
        ), 200
    except TemplateNotFound:
        abort(404)


@app.get("/login")
def login():
    """Initiate OIDC Authorization Code flow."""
    tenant_id = request.args.get("tenant")
    return_to = request.args.get("return_to")

    if not tenant_id:
        return jsonify({"error": "missing_tenant"}), 400

    tenant_cfg, error = _load_tenant_or_error(tenant_id)
    if error:
        return error
    if return_to and not validate_return_to(tenant_cfg, return_to):
        return jsonify({"error": "invalid_return_to"}), 400

    session["tenant_id"] = tenant_id
    if return_to:
        session["return_to"] = return_to
    else:
        session.pop("return_to", None)

    discovery = _get_discovery()
    authorization_endpoint = discovery["authorization_endpoint"]

    state = os.urandom(16).hex()
    session["oidc_state"] = state

    params = {
        "client_id": OIDC_CLIENT_ID,
        "response_type": "code",
        "scope": "openid profile email",
        "redirect_uri": _callback_url(),
        "state": state,
    }
    return redirect(f"{authorization_endpoint}?{urlencode(params)}")


@app.get("/callback")
def callback():
    """Handle callback, exchange code for tokens, store minimal identity in session."""
    err = request.args.get("error")
    if err:
        return jsonify({
            "error": err,
            "error_description": request.args.get("error_description")
        }), 400

    code = request.args.get("code")
    state = request.args.get("state")
    expected_state = session.get("oidc_state")

    if not code:
        return jsonify({"error": "missing_code"}), 400
    if not state or not expected_state or state != expected_state:
        return jsonify({"error": "invalid_state"}), 400

    session.pop("oidc_state", None)

    discovery = _get_discovery()
    token_endpoint = discovery["token_endpoint"]
    userinfo_endpoint = discovery.get("userinfo_endpoint")

    token_resp = requests.post(
        token_endpoint,
        data={
            "grant_type": "authorization_code",
            "client_id": OIDC_CLIENT_ID,
            "client_secret": OIDC_CLIENT_SECRET,
            "code": code,
            "redirect_uri": _callback_url(),
        },
        timeout=10,
    )
    token_resp.raise_for_status()
    token_json = token_resp.json()

    access_token = token_json.get("access_token")
    if not access_token:
        return jsonify({"error": "no_access_token"}), 500

    # Capture realm roles from access token (Keycloak convention)
    access_claims = jwt_payload(access_token)
    realm_roles = ((access_claims.get("realm_access") or {}).get("roles")) or []

    claims: Dict[str, Any] = {}
    if userinfo_endpoint:
        ui = requests.get(
            userinfo_endpoint,
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10,
        )
        ui.raise_for_status()
        claims = ui.json()

    user_id = claims.get("sub") or access_claims.get("sub")
    if not user_id:
        return jsonify({"error": "missing_sub_in_claims"}), 500

    display_name = (
        claims.get("preferred_username")
        or claims.get("name")
        or claims.get("given_name")
        or None
    )

    session["user"] = {
        "user_id": user_id,
        "display_name": display_name,
        "email": claims.get("email"),
        "realm_roles": realm_roles,
        "issuer": OIDC_ISSUER,
    }
    hierarchy = _load_user_hierarchy(user_id)
    session["user"].update({
        "msn_id": hierarchy["msn_id"] if hierarchy else None,
        "parent_msn_id": hierarchy["parent_msn_id"] if hierarchy else None,
        "role": hierarchy["role"] if hierarchy else None,
    })

    return redirect(url_for("me"))


@app.get("/me")
def me():
    u = session.get("user")
    if not u:
        return jsonify({"authenticated": False}), 401
    payload = {
        "authenticated": True,
        "user": u,
        "hierarchy": {
            "msn_id": u.get("msn_id"),
            "parent_msn_id": u.get("parent_msn_id"),
            "role": u.get("role"),
        },
    }
    tenant_id = session.get("tenant_id")
    if tenant_id:
        payload["tenant_id"] = tenant_id
    return jsonify(payload), 200


@app.get("/logout")
def logout():
    session.clear()
    return jsonify({"ok": True}), 200


@app.get("/t/<tenant_id>/ping")
@require_login
@require_tenant_context
def tenant_ping(tenant_id: str):
    guard = require_tenant_access(tenant_id)
    if guard:
        return guard
    user = session.get("user") or {}
    return jsonify({
        "ok": True,
        "tenant": tenant_id,
        "user": {
            "user_id": user.get("user_id"),
            "display_name": user.get("display_name"),
            "email": user.get("email"),
        },
    }), 200


@app.get("/api/t/<tenant_id>/tables/<table_id>")
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


@app.post("/api/t/<tenant_id>/tables/<table_id>")
@require_login
def tenant_table_create_record(tenant_id: str, table_id: str):
    guard = require_tenant_access(tenant_id)
    if guard:
        return guard

    payload, error = _json_body()
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


@app.get("/api/t/<tenant_id>/tables/<table_id>/<record_id>")
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


@app.put("/api/t/<tenant_id>/tables/<table_id>/<record_id>")
@require_login
def tenant_table_update_record(tenant_id: str, table_id: str, record_id: str):
    guard = require_tenant_access(tenant_id)
    if guard:
        return guard

    try:
        uuid.UUID(record_id)
    except ValueError:
        return jsonify({"error": "invalid_record_id"}), 400

    payload, error = _json_body()
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


@app.delete("/api/t/<tenant_id>/tables/<table_id>/<record_id>")
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


@app.get("/api/samras/<domain>/<int:version>/node/<address>")
def samras_node(domain: str, version: int, address: str):
    layout = _samras_layout_lookup(domain, version)
    if not layout:
        return jsonify({"error": "samras_layout_not_found"}), 404

    address_parts = _parse_samras_address(address)
    if not address_parts:
        return jsonify({"error": "invalid_address"}), 400
    if not _samras_address_in_stream(address_parts, layout["count_stream"]):
        return jsonify({"error": "address_not_found"}), 404

    node = _samras_find_node(layout.get("traversal_spec"), address_parts)
    return jsonify({
        "domain": domain,
        "version": version,
        "address": _samras_node_key(address_parts),
        "node": node,
    }), 200


@app.get("/api/admin/local-domain")
@require_root_admin
def admin_local_domains():
    domains = db.fetchall(
        "SELECT local_id, title FROM platform.local_domain ORDER BY title"
    )
    return jsonify({"local_domains": domains}), 200


@app.post("/api/admin/local-domain")
@require_root_admin
def admin_local_domain_create():
    payload, error = _json_body()
    if error:
        return error
    error = _require_fields(payload, ["local_id", "title"])
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


@app.get("/api/admin/archetypes")
def admin_archetypes():
    user = get_current_user()
    if not user:
        return jsonify({"error": "not_authenticated"}), 401

    tenant_id = request.args.get("tenant_id")
    if tenant_id:
        guard = _require_tenant_admin(tenant_id)
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


@app.post("/api/admin/archetypes")
def admin_archetypes_create():
    payload, error = _json_body()
    if error:
        return error
    error = _require_fields(payload, ["tenant_id", "name", "fields"])
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

    guard = _require_tenant_admin(tenant_id)
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
        error = _require_fields(field, ["position", "name", "type"])
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
        constraint_error = _validate_archetype_field_constraints(ref_domain, constraints)
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


@app.get("/api/admin/manifest")
def admin_manifest():
    user = get_current_user()
    if not user:
        return jsonify({"error": "not_authenticated"}), 401

    tenant_id = request.args.get("tenant_id")
    if tenant_id:
        guard = _require_tenant_admin(tenant_id)
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


@app.post("/api/admin/manifest")
def admin_manifest_create():
    payload, error = _json_body()
    if error:
        return error
    error = _require_fields(payload, ["tenant_id", "table_id", "archetype_id"])
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

    guard = _require_tenant_admin(tenant_id)
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


@app.get("/api/admin/mss-profiles")
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


@app.get("/api/admin/user-hierarchy")
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
        try:
            uuid.UUID(msn_id)
        except ValueError:
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


@app.post("/api/admin/user-hierarchy")
@require_root_admin
def admin_user_hierarchy_create():
    payload, error = _json_body()
    if error:
        return error
    error = _require_fields(payload, ["user_id", "display_name", "role"])
    if error:
        return error

    user_id = payload["user_id"]
    display_name = payload["display_name"]
    role = payload["role"]
    parent_msn_id = payload.get("parent_msn_id")

    if not isinstance(user_id, str) or not user_id.strip():
        return jsonify({"error": "invalid_user_id"}), 400
    if not isinstance(display_name, str) or not display_name.strip():
        return jsonify({"error": "invalid_display_name"}), 400
    if not isinstance(role, str) or not role.strip():
        return jsonify({"error": "invalid_role"}), 400
    if parent_msn_id is not None and not isinstance(parent_msn_id, str):
        return jsonify({"error": "invalid_parent_msn_id"}), 400

    try:
        uuid.UUID(user_id)
    except ValueError:
        return jsonify({"error": "invalid_user_id"}), 400

    parent_id = None
    if parent_msn_id:
        try:
            uuid.UUID(parent_msn_id)
        except ValueError:
            return jsonify({"error": "invalid_parent_msn_id"}), 400
        parent_id = parent_msn_id

    msn_id = str(uuid.uuid4())
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


@app.put("/api/admin/user-hierarchy")
@require_root_admin
def admin_user_hierarchy_update():
    payload, error = _json_body()
    if error:
        return error
    error = _require_fields(payload, ["msn_id"])
    if error:
        return error

    msn_id = payload["msn_id"]
    if not isinstance(msn_id, str) or not msn_id.strip():
        return jsonify({"error": "invalid_msn_id"}), 400
    try:
        uuid.UUID(msn_id)
    except ValueError:
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
            try:
                uuid.UUID(parent_msn_id)
            except ValueError:
                return jsonify({"error": "invalid_parent_msn_id"}), 400
            updates["parent_msn_id"] = parent_msn_id

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


@app.delete("/api/admin/user-hierarchy")
@require_root_admin
def admin_user_hierarchy_delete():
    payload, error = _json_body()
    if error:
        return error
    error = _require_fields(payload, ["msn_id"])
    if error:
        return error

    msn_id = payload["msn_id"]
    if not isinstance(msn_id, str) or not msn_id.strip():
        return jsonify({"error": "invalid_msn_id"}), 400
    try:
        uuid.UUID(msn_id)
    except ValueError:
        return jsonify({"error": "invalid_msn_id"}), 400

    row = db.fetchone(
        "DELETE FROM platform.mss_profile WHERE msn_id = %s RETURNING msn_id",
        (msn_id,),
    )
    if not row:
        return jsonify({"error": "profile_not_found"}), 404
    return jsonify({"deleted": True, "msn_id": row["msn_id"]}), 200


@app.post("/api/admin/mss-profiles")
@require_root_admin
def admin_mss_profiles_create():
    payload, error = _json_body()
    if error:
        return error
    error = _require_fields(payload, ["user_id", "display_name", "role"])
    if error:
        return error

    user_id = payload["user_id"]
    display_name = payload["display_name"]
    role = payload["role"]
    parent_msn_id = payload.get("parent_msn_id")

    if not isinstance(user_id, str) or not user_id.strip():
        return jsonify({"error": "invalid_user_id"}), 400
    if not isinstance(display_name, str) or not display_name.strip():
        return jsonify({"error": "invalid_display_name"}), 400
    if not isinstance(role, str) or not role.strip():
        return jsonify({"error": "invalid_role"}), 400
    if parent_msn_id is not None and not isinstance(parent_msn_id, str):
        return jsonify({"error": "invalid_parent_msn_id"}), 400

    try:
        uuid.UUID(user_id)
    except ValueError:
        return jsonify({"error": "invalid_user_id"}), 400

    parent_id = None
    if parent_msn_id:
        try:
            uuid.UUID(parent_msn_id)
        except ValueError:
            return jsonify({"error": "invalid_parent_msn_id"}), 400
        parent_id = parent_msn_id

    msn_id = str(uuid.uuid4())
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


@app.get("/api/admin/samras-layouts")
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


@app.post("/api/admin/samras-layouts")
@require_root_admin
def admin_samras_layouts_create():
    payload, error = _json_body()
    if error:
        return error
    error = _require_fields(payload, ["domain", "version", "count_stream", "traversal_spec"])
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


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
