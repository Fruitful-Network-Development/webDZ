"""Tenant access rules."""
from __future__ import annotations

from typing import Any, Optional
from urllib.parse import urlencode

from flask import abort, redirect, request

from core.policy import (
    get_current_user,
    is_provisioned,
    is_root_admin,
    is_tenant_admin,
    log_authz_decision,
    forbidden_response,
    not_authenticated_response,
    not_provisioned_response,
)
from tenants.registry import (
    TenantNotFoundError,
    TenantRegistryError,
    TenantValidationError,
    load_tenant,
)


def require_tenant_access(tenant_id: str) -> Optional[tuple[Any, int]]:
    user = get_current_user()
    if not user:
        return not_authenticated_response()
    if not is_provisioned(user):
        return not_provisioned_response()
    if is_root_admin(user):
        return None
    if is_tenant_admin(user, tenant_id):
        return None
    return forbidden_response()


def require_tenant_console_access(tenant_id: str) -> tuple[dict[str, Any], Optional[Any]]:
    try:
        tenant_cfg = load_tenant(tenant_id)
    except TenantNotFoundError as exc:
        abort(404, exc.message)
    except (TenantValidationError, TenantRegistryError) as exc:
        abort(400, exc.message)
    user = get_current_user()
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
    if not is_provisioned(user):
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
