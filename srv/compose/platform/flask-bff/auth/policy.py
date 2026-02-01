"""Schema-agnostic authorization policy stubs for the Flask BFF."""
from __future__ import annotations

from typing import Any, Mapping, Tuple


def get_current_user() -> Any | None:
    """Return the current authenticated user from request context when available."""
    return None


def is_root_admin(user: Any | None) -> bool:
    """Return whether the provided user has root-level administrative privileges."""
    return False


def is_tenant_admin(user: Any | None) -> bool:
    """Return whether the provided user has tenant-level administrative privileges."""
    return False


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
