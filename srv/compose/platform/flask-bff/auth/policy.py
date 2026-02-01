"""Schema-agnostic authorization policy stubs for the Flask BFF."""
from __future__ import annotations

from typing import Any, Mapping, Tuple

from flask import g, request

from auth.keycloak.client import KeycloakAuthError, decode_token
from auth.keycloak.user_mapping import UserMappingError, fetch_identity_access


def get_current_user() -> Any | None:
    """Return the current authenticated user from request context when available."""
    cached = getattr(g, "current_user", None)
    if cached is not None:
        return cached

    token = _extract_bearer_token()
    if token:
        try:
            claims = decode_token(token)
        except KeycloakAuthError:
            return None
        user_id = claims.get("sub")
        identity = None
        if user_id:
            try:
                identity = fetch_identity_access(user_id)
            except UserMappingError:
                identity = None
        user = {"user_id": user_id, "claims": claims, "identity": identity}
        g.current_user = user
        return user

    header_user = request.headers.get("X-Portal-User")
    if header_user:
        user = {"user_id": header_user, "claims": {}, "profile": None}
        g.current_user = user
        return user

    g.current_user = None
    return None


def is_root_admin(user: Any | None) -> bool:
    """Return whether the provided user has root-level administrative privileges."""
    if not user:
        return False
    claims = (user or {}).get("claims") if isinstance(user, Mapping) else {}
    roles = (claims or {}).get("realm_access", {}).get("roles", [])
    return "root-admin" in roles


def is_tenant_admin(user: Any | None) -> bool:
    """Return whether the provided user has tenant-level administrative privileges."""
    if not user:
        return False
    claims = (user or {}).get("claims") if isinstance(user, Mapping) else {}
    roles = (claims or {}).get("realm_access", {}).get("roles", [])
    return "tenant-admin" in roles


def require_root_admin(user: Any | None) -> None:
    """Enforce that the provided user has root-level administrative access."""
    return None


def forbidden_response() -> Tuple[Mapping[str, str], int]:
    """Return a response payload indicating the caller is not authorized."""
    return {"detail": "forbidden"}, 403


def not_authenticated_response() -> Tuple[Mapping[str, str], int]:
    """Return a response payload indicating the caller is not authenticated."""
    return {"detail": "not authenticated"}, 401


def not_provisioned_response() -> Tuple[Mapping[str, str], int]:
    """Return a response payload indicating the caller is not provisioned."""
    return {"detail": "not provisioned"}, 403


def log_authz_decision(
    action: str,
    allowed: bool,
    *,
    user: Any | None = None,
    context: Mapping[str, Any] | None = None,
) -> None:
    """Record an authorization decision for auditing or debugging."""
    _ = action, allowed, user, context


def _extract_bearer_token() -> str | None:
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None
    return auth_header.split(" ", 1)[1].strip() or None
