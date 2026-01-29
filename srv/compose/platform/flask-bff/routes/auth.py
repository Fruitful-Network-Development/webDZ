"""Authentication and session routes."""
from __future__ import annotations

import base64
import json
import os
import time
from typing import Any, Dict
from urllib.parse import urlencode

import requests
from flask import Blueprint, jsonify, redirect, request, session, url_for

from config import OIDC_CLIENT_ID, OIDC_CLIENT_SECRET, OIDC_ISSUER, PUBLIC_BASE_URL
from core.mss_profile import load_user_hierarchy
from routes.common import load_tenant_or_error
from tenants.registry import TenantRegistryError, load_tenant, validate_return_to


auth_bp = Blueprint("auth", __name__)


_discovery_cache: Dict[str, Any] = {}
_discovery_cache_at: float = 0.0
_DISCOVERY_TTL_SECONDS = 300


def _call_requests(method: str, *args, **kwargs):
    fn = getattr(requests, method)
    if getattr(fn, "__self__", None) is not None:
        return fn.__func__(*args, **kwargs)
    return fn(*args, **kwargs)


def _get_discovery() -> Dict[str, Any]:
    global _discovery_cache, _discovery_cache_at
    now = time.time()
    if _discovery_cache and (now - _discovery_cache_at) < _DISCOVERY_TTL_SECONDS:
        return _discovery_cache

    url = f"{OIDC_ISSUER}/.well-known/openid-configuration"
    resp = _call_requests("get", url, timeout=10)
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
    return f"{_public_base_url()}{url_for('auth.callback')}"


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


@auth_bp.get("/login", endpoint="login")
def login():
    """Initiate OIDC Authorization Code flow."""
    tenant_id = request.args.get("tenant")
    return_to = request.args.get("return_to")

    if not tenant_id:
        return jsonify({"error": "missing_tenant"}), 400

    tenant_cfg, error = load_tenant_or_error(tenant_id)
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


@auth_bp.get("/callback", endpoint="callback")
def callback():
    """Handle callback, exchange code for tokens, store minimal identity in session."""
    err = request.args.get("error")
    if err:
        return jsonify({
            "error": err,
            "error_description": request.args.get("error_description"),
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

    token_resp = _call_requests(
        "post",
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

    # Capture roles and groups from access token (Keycloak conventions)
    access_claims = jwt_payload(access_token)
    realm_roles = ((access_claims.get("realm_access") or {}).get("roles")) or []
    client_roles = (
        ((access_claims.get("resource_access") or {}).get(OIDC_CLIENT_ID) or {}).get("roles")
        or []
    )
    groups = access_claims.get("groups") or []

    claims: Dict[str, Any] = {}
    if userinfo_endpoint:
        ui = _call_requests(
            "get",
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
    username = claims.get("preferred_username") or claims.get("name")

    session["user"] = {
        "user_id": user_id,
        "username": username,
        "display_name": display_name,
        "email": claims.get("email"),
        "realm_roles": realm_roles,
        "client_roles": client_roles,
        "groups": groups,
        "issuer": OIDC_ISSUER,
    }
    hierarchy = load_user_hierarchy(user_id)
    session["user"].update({
        "msn_id": hierarchy["msn_id"] if hierarchy else None,
        "parent_msn_id": hierarchy["parent_msn_id"] if hierarchy else None,
        "role": hierarchy["role"] if hierarchy else None,
    })

    tenant_id = session.get("tenant_id")
    return_to = session.pop("return_to", None)

    if tenant_id:
        try:
            tenant_cfg = load_tenant(tenant_id)
            if return_to and validate_return_to(tenant_cfg, return_to):
                redirect_target = return_to
            else:
                redirect_target = f"/t/{tenant_id}/console"
        except TenantRegistryError:
            redirect_target = return_to or f"/t/{tenant_id}/console"
    else:
        redirect_target = return_to or "/admin"

    return redirect(redirect_target)


@auth_bp.get("/me", endpoint="me")
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


@auth_bp.get("/logout", endpoint="logout")
def logout():
    session.clear()
    return jsonify({"ok": True}), 200
