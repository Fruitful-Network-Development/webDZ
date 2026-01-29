"""Shared route helpers for the Flask BFF."""
from __future__ import annotations

from functools import wraps
from typing import Any, Dict, Optional

from flask import abort, jsonify, request, session

from core.policy import (
    forbidden_response,
    get_current_user,
    is_root_admin,
    is_tenant_admin,
    log_authz_decision,
    not_authenticated_response,
    not_provisioned_response,
)
from tenants.access import require_tenant_access, require_tenant_console_access
from tenants.console_modules import enabled_console_modules
from tenants.registry import (
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


def unwrap_api_response(result: Any) -> tuple[dict[str, Any], int]:
    if isinstance(result, tuple):
        response, status = result
    else:
        response = result
        status = response.status_code
    payload = response.get_json() if hasattr(response, "get_json") else {}
    return payload or {}, status


__all__ = [
    "current_user",
    "enabled_console_modules",
    "forbidden_response",
    "get_current_user",
    "is_root_admin",
    "is_tenant_admin",
    "load_tenant_or_abort",
    "load_tenant_or_error",
    "log_authz_decision",
    "not_authenticated_response",
    "not_provisioned_response",
    "json_body",
    "require_fields",
    "require_login",
    "require_realm_role",
    "require_tenant_access",
    "require_tenant_admin",
    "require_tenant_console_access",
    "require_tenant_context",
    "unwrap_api_response",
]
