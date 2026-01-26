"""Shared route helpers for the Flask BFF."""
from __future__ import annotations

from functools import wraps
from typing import Any, Dict, Optional
from urllib.parse import urlencode

from flask import abort, jsonify, redirect, request, session

from authz import (
    get_current_user,
    is_root_admin,
    is_tenant_admin,
    log_authz_decision,
    not_authenticated_response,
    forbidden_response,
    not_provisioned_response,
)
from tenant_registry import (
    TenantNotFoundError,
    TenantRegistryError,
    TenantValidationError,
    load_tenant,
)


def current_user() -> Optional[Dict[str, Any]]:
    return get_current_user()


def load_tenant_or_error(tenant_id: str):
    try:
        return load_tenant(tenant_id), None
    except TenantNotFoundError as exc:
        return None, (jsonify({"error": exc.code, "message": exc.message}), 404)
    except (TenantValidationError, TenantRegistryError) as exc:
        return None, (jsonify({"error": exc.code, "message": exc.message}), 400)


def load_tenant_or_abort(tenant_id: str):
    try:
        return load_tenant(tenant_id)
    except TenantNotFoundError as exc:
        abort(404, exc.message)
    except (TenantValidationError, TenantRegistryError) as exc:
        abort(400, exc.message)


def require_login(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not current_user():
            return not_authenticated_response()
        return fn(*args, **kwargs)

    return wrapper


def require_tenant_context(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("tenant_id"):
            return jsonify({"error": "missing_tenant"}), 400
        return fn(*args, **kwargs)

    return wrapper


def json_body() -> tuple[Optional[Dict[str, Any]], Optional[tuple[Any, int]]]:
    data = request.get_json(silent=True)
    if data is None:
        return None, (jsonify({"error": "invalid_json"}), 400)
    if not isinstance(data, dict):
        return None, (jsonify({"error": "invalid_json"}), 400)
    return data, None


def require_fields(payload: Dict[str, Any], fields: list[str]) -> Optional[tuple[Any, int]]:
    missing = [field for field in fields if field not in payload]
    if missing:
        return jsonify({"error": "missing_fields", "fields": missing}), 400
    return None


def require_tenant_admin(tenant_id: str) -> Optional[tuple[Any, int]]:
    user = current_user()
    if not user:
        return not_authenticated_response()
    if is_root_admin(user) or is_tenant_admin(user, tenant_id):
        return None
    return forbidden_response()


def require_realm_role(role: str):
    """Require a Keycloak realm role captured during /callback."""

    def deco(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            u = session.get("user")
            if not u:
                return not_authenticated_response()
            roles = u.get("realm_roles") or []
            if role not in roles:
                return jsonify({
                    "error": "forbidden",
                    "message": "Access forbidden.",
                    "missing_role": role,
                }), 403
            return fn(*args, **kwargs)

        return wrapper

    return deco


def require_tenant_access(tenant_id: str):
    u = current_user()
    if not u:
        return not_authenticated_response()
    if not u.get("msn_id"):
        return not_provisioned_response()
    if is_root_admin(u):
        return None
    if is_tenant_admin(u, tenant_id):
        return None
    return forbidden_response()


def unwrap_api_response(result: Any) -> tuple[dict[str, Any], int]:
    if isinstance(result, tuple):
        response, status = result
    else:
        response = result
        status = response.status_code
    payload = response.get_json() if hasattr(response, "get_json") else {}
    return payload or {}, status


def enabled_console_modules(tenant_cfg: dict[str, Any]) -> list[str]:
    modules = tenant_cfg.get("console_modules") or {}
    if isinstance(modules, dict):
        return [name for name, enabled in modules.items() if enabled]
    return list(modules)


def require_tenant_console_access(tenant_id: str) -> tuple[dict[str, Any], Optional[Any]]:
    tenant_cfg = load_tenant_or_abort(tenant_id)
    user = current_user()
    if not user:
        next_path = request.full_path
        if next_path.endswith("?"):
            next_path = next_path[:-1]
        log_authz_decision(
            action="tenant_console_access",
            tenant_id=tenant_id,
            decision="deny",
            reason="missing_user",
            checks=["session_user"],
        )
        login_url = f"/login?{urlencode({'tenant': tenant_id, 'return_to': next_path})}"
        return tenant_cfg, redirect(login_url)
    if not user.get("msn_id"):
        log_authz_decision(
            action="tenant_console_access",
            tenant_id=tenant_id,
            decision="deny",
            reason="not_provisioned",
            checks=["root_admin_role", "tenant_admin_role", "mss_role"],
        )
        return tenant_cfg, not_provisioned_response()
    if not (is_root_admin(user) or is_tenant_admin(user, tenant_id)):
        log_authz_decision(
            action="tenant_console_access",
            tenant_id=tenant_id,
            decision="deny",
            reason="missing_tenant_access",
            checks=["root_admin_role", "tenant_admin_role", "mss_role"],
        )
        return tenant_cfg, forbidden_response()
    log_authz_decision(
        action="tenant_console_access",
        tenant_id=tenant_id,
        decision="allow",
        reason="authorized",
        checks=["root_admin_role", "tenant_admin_role", "mss_role"],
    )
    return tenant_cfg, None
