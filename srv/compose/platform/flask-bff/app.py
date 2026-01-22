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

import os
import time
from typing import Any, Dict, Optional
from urllib.parse import urlencode

import psycopg
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

# Internal-only Phase 3: DB connection via docker network
PLATFORM_DB_HOST = os.getenv("PLATFORM_DB_HOST", "platform_db")
PLATFORM_DB_PORT = int(os.getenv("PLATFORM_DB_PORT", "5432"))
PLATFORM_DB_NAME = os.getenv("PLATFORM_DB_NAME", "platform")
PLATFORM_DB_USER = os.getenv("PLATFORM_DB_USER", "platform")
PLATFORM_DB_PASSWORD = _require_env("PLATFORM_DB_PASSWORD")

# Optional: explicit external base URL. For Phase 3 you typically browse via:
# http://localhost:8001 (SSH port forward)
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "").rstrip("/")


# ----------------------------
# Flask app
# ----------------------------

app = Flask(__name__)
app.secret_key = SESSION_SECRET

# Session cookie policy:
# - Phase 3 internal-only testing likely uses http://localhost:8001 via SSH tunnel,
#   so Secure=False is necessary to allow cookies on http.
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
    Minimal audit log. If the audit table doesn't exist yet, you can safely no-op
    by removing this call, but recommended to keep.
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
                    "detail": detail if detail is not None else None,
                },
            )
        conn.commit()


# ----------------------------
# Routes
# ----------------------------

@app.get("/health")
def health():
    return jsonify({"status": "ok"}), 200


@app.get("/login")
def login():
    """
    Initiate OIDC Authorization Code flow.
    """
    discovery = _get_discovery()
    authorization_endpoint = discovery["authorization_endpoint"]

    # Minimal state (anti-CSRF). For Phase 3, simple random is OK; in Phase 4,
    # you can harden with nonce/state libraries if desired.
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
        # Fallback: store token response minimal info
        claims = {"sub": None}

    user_id = claims.get("sub")
    if not user_id:
        return jsonify({"error": "missing_sub_in_claims"}), 500

    # Choose a display name without storing identifiers
    display_name = (
        claims.get("preferred_username")
        or claims.get("name")
        or claims.get("given_name")
        or None
    )

    # Store only what we need in session (no tokens in browser storage; session is server-side)
    session["user"] = {
        "user_id": user_id,
        "display_name": display_name,
    }

    # Upsert platform user profile
    try:
        _upsert_user_profile(user_id=user_id, display_name=display_name)
        _audit(action="login_success", actor_user_id=user_id, detail={"issuer": OIDC_ISSUER})
    except Exception as e:
        # Keep error explicit for internal-only phase; in Phase 4, you may want less detail.
        return jsonify({"error": "db_upsert_failed", "detail": str(e)}), 500

    return redirect(url_for("me"))


@app.get("/me")
def me():
    """
    Returns current user identity from session.
    """
    u = session.get("user")
    if not u:
        return jsonify({"authenticated": False}), 401

    # Optionally include profile row from DB
    profile = None
    try:
        profile = _get_user_profile(u["user_id"])
    except Exception:
        # For Phase 3, don't fail /me due to DB read issues; return session identity.
        profile = None

    return jsonify(
        {
            "authenticated": True,
            "user": u,
            "profile": profile,
        }
    ), 200


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
