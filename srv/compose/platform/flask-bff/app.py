"""
Flask BFF (Phase 3: internal-only)

Goals:
- Minimal OIDC login against Keycloak (Authorization Code flow)
- Server-side token exchange
- Session cookie handled by BFF (no tokens in browser storage)
- Internal-only exposure (tested via SSH port-forward to localhost:8001)
- Platform DB writes to platform.user_profiles (schema-owned, no DDL here)

Data model intent:
- platform.user_profiles is a platform-owned identity resolution record:
  - user_id (UUID) = Keycloak 'sub'
  - display_name (optional)
  - no credentials, no MFA state, no client operational data
  - no identifiers (email/phone) stored here
"""

from __future__ import annotations

import base64
import json
import os
import time
from functools import wraps
from typing import Any, Dict, Optional
from urllib.parse import urlencode

import psycopg
from psycopg.types.json import Json as PgJson
import requests
from flask import Flask, abort, jsonify, redirect, request, session, url_for, render_template

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

# Internal-only Phase 3: DB connection via docker network
PLATFORM_DB_HOST = os.getenv("PLATFORM_DB_HOST", "platform_db")
PLATFORM_DB_PORT = int(os.getenv("PLATFORM_DB_PORT", "5432"))
PLATFORM_DB_NAME = os.getenv("PLATFORM_DB_NAME", "platform")
PLATFORM_DB_USER = os.getenv("PLATFORM_DB_USER", "platform")
PLATFORM_DB_PASSWORD = _require_env("PLATFORM_DB_PASSWORD")

# Optional: explicit external base URL.
# For Phase 3 you typically browse via http://localhost:8001 (SSH port forward)
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "").rstrip("/")


# ----------------------------
# Flask app
# ----------------------------

app = Flask(__name__)
app.secret_key = SESSION_SECRET

# Session cookie policy:
# - Phase 3 internal-only testing uses http://localhost:8001 via SSH tunnel,
#   so Secure=False is necessary for cookies on http.
# - In Phase 4 (public HTTPS), set Secure=True.
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=False,  # flip to True when served over HTTPS
)

# ----------------------------
# OIDC discovery
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


def _callback_url() -> str:
    # Prefer explicit base URL if provided; otherwise use Flask's external URL generation.
    # For Phase 3 with SSH port forwarding, PUBLIC_BASE_URL should be blank and your
    # browser URL will be http://localhost:8001.
    if PUBLIC_BASE_URL:
        return f"{PUBLIC_BASE_URL}/callback"
    return url_for("callback", _external=True)


# ----------------------------
# JWT helpers (Phase 3 scaffold)
# ----------------------------

def _b64url_decode(s: str) -> bytes:
    # Base64url without padding
    s += "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode(s.encode("utf-8"))


def jwt_payload(jwt_token: str) -> Dict[str, Any]:
    """
    Parse JWT payload without verifying signature.

    Phase 3 rationale:
    - BFF receives tokens directly from Keycloak over TLS, server-to-server.
    - We only need role scaffolding to unblock admin-gating.
    Phase 4:
    - Replace with verified decoding using Keycloak JWKS.
    """
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
    return session.get("user")


def _require_login():
    """
    Phase 3 UI guard: if not authenticated, redirect to /login.
    If a 'next' param is present on /login, you can later wire it to return users
    to the target route after callback; for now this is sufficient for the skeleton UI.
    """
    if not _current_user():
        nxt = request.path
        # Preserve target for future use; harmless if /login ignores it for now.
        return redirect(f"/login?next={nxt}")
    return None


# ----------------------------
# Authorization helpers
# ----------------------------

def require_realm_role(role: str):
    """
    Require that the authenticated user has the specified Keycloak realm role.
    Roles are captured from access_token realm_access.roles during /callback.
    """
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


# ----------------------------
# Database helpers
# ----------------------------

def _db_conn() -> psycopg.Connection:
    return psycopg.connect(
        host=PLATFORM_DB_HOST,
        port=PLATFORM_DB_PORT,
        dbname=PLATFORM_DB_NAME,
        user=PLATFORM_DB_USER,
        password=PLATFORM_DB_PASSWORD,
        connect_timeout=5,
    )


def _upsert_user_profile(user_id: str, display_name: Optional[str]) -> None:
    """
    Upsert into platform.user_profiles.
    Assumes schema exists already (created by platform_schema init job).
    user_id is a UUID string (Keycloak 'sub').
    """
    sql = """
    INSERT INTO platform.user_profiles (user_id, display_name, created_at, updated_at)
    VALUES (%(user_id)s::uuid, %(display_name)s, now(), now())
    ON CONFLICT (user_id) DO UPDATE
      SET display_name = EXCLUDED.display_name,
          updated_at = now();
    """
    with _db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, {"user_id": user_id, "display_name": display_name})
        conn.commit()


def _get_user_profile(user_id: str) -> Optional[Dict[str, Any]]:
    sql = """
    SELECT user_id::text, display_name, created_at, updated_at
    FROM platform.user_profiles
    WHERE user_id = %(user_id)s::uuid
    """
    with _db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, {"user_id": user_id})
            row = cur.fetchone()
            if not row:
                return None
            return {
                "user_id": row[0],
                "display_name": row[1],
                "created_at": row[2].isoformat() if row[2] else None,
                "updated_at": row[3].isoformat() if row[3] else None,
            }


def _audit(action: str, actor_user_id: Optional[str] = None, detail: Optional[Dict[str, Any]] = None) -> None:
    """
    Minimal audit log.
    """
    sql = """
    INSERT INTO platform.audit_log (at, actor_user_id, action, detail)
    VALUES (now(), %(actor_user_id)s::uuid, %(action)s, %(detail)s::jsonb)
    """
    with _db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                sql,
                {
                    "actor_user_id": actor_user_id,
                    "action": action,
                    # psycopg v3 requires explicit JSON adaptation for dicts
                    "detail": (PgJson(detail) if detail is not None else None),
                },
            )
        conn.commit()


# ----------------------------
# Routes
# ----------------------------

@app.get("/health")
def health():
    return jsonify({"status": "ok"}), 200


@app.get("/admin")
def admin_index():
    """
    Phase 3 UI skeleton: render an admin dashboard page.
    Internal-only access via SSH tunnel (http://localhost:8001).
    """
    guard = _require_login()
    if guard:
        return guard
    user = _current_user()
    return render_template("admin/index.html", title="Admin", user=user)


@app.get("/login")
def login():
    """
    Initiate OIDC Authorization Code flow.
    """
    discovery = _get_discovery()
    authorization_endpoint = discovery["authorization_endpoint"]

    # Minimal state (anti-CSRF).
    state = os.urandom(16).hex()
    session["oidc_state"] = state

    params = {
        "client_id": OIDC_CLIENT_ID,
        "response_type": "code",
        "scope": "openid profile",
        "redirect_uri": _callback_url(),
        "state": state,
    }

    return redirect(f"{authorization_endpoint}?{urlencode(params)}")


@app.get("/callback")
def callback():
    """
    Handle OIDC callback, exchange code for tokens server-side,
    store minimal identity in session, and upsert user profile.
    """
    err = request.args.get("error")
    if err:
        desc = request.args.get("error_description")
        return jsonify({"error": err, "error_description": desc}), 400

    code = request.args.get("code")
    state = request.args.get("state")
    expected_state = session.get("oidc_state")

    if not code:
        return jsonify({"error": "missing_code"}), 400
    if not state or not expected_state or state != expected_state:
        return jsonify({"error": "invalid_state"}), 400

    # One-time use state
    session.pop("oidc_state", None)

    discovery = _get_discovery()
    token_endpoint = discovery["token_endpoint"]
    userinfo_endpoint = discovery.get("userinfo_endpoint")

    # Exchange code for tokens
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

    # Capture realm roles from the access token (Keycloak convention)
    access_claims = jwt_payload(access_token)
    realm_roles = ((access_claims.get("realm_access") or {}).get("roles")) or []

    # Fetch userinfo for stable 'sub' and display fields
    claims: Dict[str, Any] = {}
    if userinfo_endpoint:
        ui = requests.get(
            userinfo_endpoint,
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10,
        )
        ui.raise_for_status()
        claims = ui.json()
    else:
        claims = {"sub": None}

    user_id = claims.get("sub")
    if not user_id:
        return jsonify({"error": "missing_sub_in_claims"}), 500

    display_name = (
        claims.get("preferred_username")
        or claims.get("name")
        or claims.get("given_name")
        or None
    )

    # Store only what we need in session
    session["user"] = {
        "user_id": user_id,
        "display_name": display_name,
        "realm_roles": realm_roles,
        "issuer": OIDC_ISSUER,
    }

    # Upsert platform user profile + audit
    try:
        _upsert_user_profile(user_id=user_id, display_name=display_name)
        _audit(action="login_success", actor_user_id=user_id, detail={"issuer": OIDC_ISSUER})
    except Exception as e:
        return jsonify({"error": "db_upsert_failed", "detail": str(e)}), 500

    return redirect(url_for("me"))


@app.get("/me")
def me():
    """
    Returns current user identity from session (convenience view).
    """
    u = session.get("user")
    if not u:
        return jsonify({"authenticated": False}), 401

    # Convenience: include DB profile if available; do not fail if DB read errors.
    profile = None
    try:
        profile = _get_user_profile(u["user_id"])
    except Exception:
        profile = None

    return jsonify(
        {
            "authenticated": True,
            "user": u,
            "profile": profile,
        }
    ), 200


@app.get("/db/me")
def db_me():
    """
    Proof endpoint: returns current user identity as recorded in platform DB.
    This is the A.5 "prove persistence" surface (strict).
    """
    u = session.get("user")
    if not u or not u.get("user_id"):
        return jsonify({"error": "not_authenticated"}), 401

    profile = _get_user_profile(u["user_id"])
    if profile is None:
        return jsonify({"error": "profile_missing"}), 404

    return jsonify({"profile": profile}), 200


@app.get("/admin/ping")
def admin_ping():
    """
    Phase 3 proof endpoint for the UI skeleton.
    Requirement: authenticated session only (no role gating yet).
    """
    guard = _require_login()
    if guard:
        return guard
    return jsonify({"status": "ok"}), 200


@app.get("/logout")
def logout():
    """
    Clears the BFF session.
    Phase 3: does not call Keycloak end-session endpoint.
    """
    u = session.get("user")
    try:
        if u and u.get("user_id"):
            _audit(action="logout", actor_user_id=u["user_id"], detail=None)
    except Exception:
        pass

    session.clear()
    return jsonify({"ok": True}), 200


if __name__ == "__main__":
    # For local debugging inside container; production should use gunicorn.
    app.run(host="0.0.0.0", port=8000, debug=True)
