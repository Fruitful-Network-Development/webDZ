"""Platform policy and access rules."""
from __future__ import annotations

import json
import logging
from functools import wraps
from typing import Any, Dict, Iterable, Optional
from urllib.parse import urlencode

from flask import current_app, jsonify, redirect, render_template, request, session


_LOGGER = logging.getLogger("authz")
_LOGGER.setLevel(logging.INFO)


def get_current_user() -> Optional[Dict[str, Any]]:
    return session.get("user")


def _roles_for(user: Optional[Dict[str, Any]]) -> Iterable[str]:
    if not user:
        return []
    roles = []
    roles.extend(user.get("realm_roles") or [])
    roles.extend(user.get("client_roles") or [])
    return roles


def _groups_for(user: Optional[Dict[str, Any]]) -> Iterable[str]:
    if not user:
        return []
    return user.get("groups") or user.get("realm_groups") or []


def is_root_admin(user: Optional[Dict[str, Any]]) -> bool:
    if "root_admin" in _roles_for(user):
        return True
    return (user or {}).get("role") == "root-admin"


def is_tenant_admin(user: Optional[Dict[str, Any]], tenant_id: str) -> bool:
    """Phase 5 placeholder for tenant access.

    NOTE: This should evolve to enforce tenant-specific RBAC once Keycloak group
    mappings or attribute-based access is formalized.
    """
    roles = set(_roles_for(user))
    if "tenant_admin" in roles:
        return True
    if f"tenant_admin:{tenant_id}" in roles:
        return True

    groups = set(_groups_for(user))
    if f"/tenants/{tenant_id}/admins" in groups:
        return True
    if f"tenant:{tenant_id}:admin" in groups:
        return True

    return False


def is_provisioned(user: Optional[Dict[str, Any]]) -> bool:
    return bool((user or {}).get("msn_id"))


def log_authz_decision(
    *,
    action: str,
    tenant_id: Optional[str],
    decision: str,
    reason: str,
    checks: Optional[list[str]] = None,
) -> None:
    user = get_current_user() or {}
    payload = {
        "event": "authz_decision",
        "action": action,
        "tenant_id": tenant_id,
        "path": request.path,
        "method": request.method,
        "decision": decision,
        "reason": reason,
        "checks": checks or [],
        "user": {
            "user_id": user.get("user_id"),
            "username": user.get("username"),
            "email": user.get("email"),
            "realm_roles": user.get("realm_roles") or [],
            "client_roles": user.get("client_roles") or [],
            "groups": user.get("groups") or [],
            "msn_id": user.get("msn_id"),
            "mss_role": user.get("role"),
            "parent_msn_id": user.get("parent_msn_id"),
        },
    }
    message = json.dumps(payload, separators=(",", ":"))
    try:
        current_app.logger.info(message)
    except RuntimeError:
        _LOGGER.info(message)


def not_provisioned_response():
    if _is_api_request():
        return jsonify({
            "error": "not_provisioned",
            "message": "Account not provisioned.",
        }), 403
    return render_template("not_provisioned.html"), 403


def forbidden_response(message: str | None = None):
    payload = {
        "error": "forbidden",
        "message": message or "Access forbidden.",
    }
    if _is_api_request():
        return jsonify(payload), 403
    return render_template("forbidden.html", message=payload["message"]), 403


def not_authenticated_response():
    return jsonify({
        "error": "not_authenticated",
        "message": "Authentication required.",
    }), 401


def _is_api_request() -> bool:
    if request.path.startswith("/api/") or request.path.startswith("/_"):
        return True
    return request.path.endswith("/ping")


def _login_redirect(return_to: str) -> Any:
    login_url = f"/login?{urlencode({'tenant': 'platform', 'return_to': return_to})}"
    return redirect(login_url)


def require_root_admin(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        user = get_current_user()
        if not user:
            log_authz_decision(
                action="admin_access",
                tenant_id=None,
                decision="deny",
                reason="missing_user",
                checks=["session_user"],
            )
            if _is_api_request():
                return not_authenticated_response()
            next_path = request.full_path
            if next_path.endswith("?"):
                next_path = next_path[:-1]
            return _login_redirect(next_path)
        if not is_root_admin(user):
            if not is_provisioned(user):
                log_authz_decision(
                    action="admin_access",
                    tenant_id=None,
                    decision="deny",
                    reason="not_provisioned",
                    checks=["root_admin_role", "mss_role"],
                )
                return not_provisioned_response()
            log_authz_decision(
                action="admin_access",
                tenant_id=None,
                decision="deny",
                reason="missing_root_admin",
                checks=["root_admin_role", "mss_role"],
            )
            return forbidden_response("Root admin access required.")
        log_authz_decision(
            action="admin_access",
            tenant_id=None,
            decision="allow",
            reason="root_admin",
            checks=["root_admin_role", "mss_role"],
        )
        return fn(*args, **kwargs)

    return wrapper
