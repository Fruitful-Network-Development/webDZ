"""Authorization helpers for the Flask BFF."""
from __future__ import annotations

from functools import wraps
from typing import Any, Dict, Iterable, Optional

from flask import abort, session


def get_current_user() -> Optional[Dict[str, Any]]:
    return session.get("user")


def _roles_for(user: Optional[Dict[str, Any]]) -> Iterable[str]:
    if not user:
        return []
    return user.get("realm_roles") or []


def _groups_for(user: Optional[Dict[str, Any]]) -> Iterable[str]:
    if not user:
        return []
    return user.get("groups") or user.get("realm_groups") or []


def is_root_admin(user: Optional[Dict[str, Any]]) -> bool:
    return "root_admin" in _roles_for(user)


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


def require_root_admin(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        user = get_current_user()
        if not user:
            abort(401)
        if not is_root_admin(user):
            abort(403)
        return fn(*args, **kwargs)

    return wrapper
