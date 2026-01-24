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
- RETURN_TO_ALLOWLIST        Comma-separated list of allowed return_to URL prefixes.
"""

from __future__ import annotations

import base64
import json
import os
import time
from functools import wraps
from typing import Any, Dict, Optional
from urllib.parse import urlencode

import requests
from flask import Flask, jsonify, redirect, request, session, url_for


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
RETURN_TO_ALLOWLIST = [
    item.strip()
    for item in os.getenv("RETURN_TO_ALLOWLIST", "").split(",")
    if item.strip()
]


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
    return session.get("user")


def _return_to_allowed(return_to: str) -> bool:
    return any(return_to.startswith(prefix) for prefix in RETURN_TO_ALLOWLIST)


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
    u = session.get("user")
    if not u:
        return jsonify({"error": "not_authenticated"}), 401
    roles = u.get("realm_roles") or []
    if "root_admin" in roles:
        return None
    if f"tenant_admin:{tenant_id}" in roles:
        return None
    return jsonify({"error": "forbidden"}), 403


# ----------------------------
# Routes
# ----------------------------

@app.get("/health")
def health():
    return jsonify({"status": "ok"}), 200


@app.get("/admin")
@require_login
def admin_index():
    """Minimal admin surface placeholder (UI can be added later)."""
    return jsonify({"ok": True, "user": _current_user()}), 200


@app.get("/login")
def login():
    """Initiate OIDC Authorization Code flow."""
    tenant_id = request.args.get("tenant")
    return_to = request.args.get("return_to")

    if not tenant_id:
        return jsonify({"error": "missing_tenant"}), 400
    if return_to and not _return_to_allowed(return_to):
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


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
