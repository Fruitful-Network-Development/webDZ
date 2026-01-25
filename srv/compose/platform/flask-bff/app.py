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
import time
import uuid
from functools import wraps
from typing import Any, Dict, Optional
from urllib.parse import urlencode

import requests
from flask import Flask, abort, jsonify, redirect, render_template, request, session, url_for

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
    tenant_cfg = _load_tenant_or_abort(tenant_id)
    user = get_current_user()
    if not user:
        next_path = request.full_path
        if next_path.endswith("?"):
            next_path = next_path[:-1]
        login_url = f"/login?{urlencode({'tenant': tenant_id, 'next': next_path})}"
        return redirect(login_url)
    if not (is_root_admin(user) or is_tenant_admin(user, tenant_id)):
        abort(403)

    modules = tenant_cfg.get("console_modules") or {}
    if isinstance(modules, dict):
        enabled_modules = [name for name, enabled in modules.items() if enabled]
    else:
        enabled_modules = list(modules)

    return render_template(
        "tenant/console.html",
        tenant_id=tenant_id,
        tenant_cfg=tenant_cfg,
        enabled_modules=enabled_modules,
    ), 200


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

    return redirect(url_for("me"))


@app.get("/me")
def me():
    u = session.get("user")
    if not u:
        return jsonify({"authenticated": False}), 401
    payload = {"authenticated": True, "user": u}
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
