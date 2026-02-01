"""Authenticated portal routes and context helpers."""
from __future__ import annotations

from dataclasses import dataclass

from flask import Blueprint, Flask, abort, current_app, jsonify, request

portal_blueprint = Blueprint("portal", __name__)


@dataclass(frozen=True)
class PortalContext:
    msn_id: str
    user_id: str
    module_id: str | None = None


def configure_portal_context(app: Flask) -> None:
    """Initialize portal orchestration state for the app lifecycle."""
    app.extensions.setdefault("portal_context", {"status": "initialized"})


def _require_authenticated_user() -> str:
    user_id = request.headers.get("X-Portal-User")
    if not user_id:
        abort(401, description="Missing portal user header.")
    return user_id


def _build_portal_context(msn_id: str, user_id: str, module_id: str | None = None) -> PortalContext:
    return PortalContext(msn_id=msn_id, user_id=user_id, module_id=module_id)


@portal_blueprint.route("/portal/login", methods=["GET", "POST"])
def portal_login():
    """Portal login placeholder."""
    return jsonify({"status": "login", "message": "Authentication stub."})


@portal_blueprint.route("/portal/<msn_id>")
def portal_entry(msn_id: str):
    user_id = _require_authenticated_user()
    context = _build_portal_context(msn_id, user_id)
    return jsonify({
        "portal": "entry",
        "msn_id": context.msn_id,
        "user_id": context.user_id,
        "orchestrator": current_app.extensions.get("portal_context", {}),
    })


@portal_blueprint.route("/portal/<msn_id>/module/<module_id>")
def portal_module(msn_id: str, module_id: str):
    user_id = _require_authenticated_user()
    context = _build_portal_context(msn_id, user_id, module_id=module_id)
    return jsonify({
        "portal": "module",
        "msn_id": context.msn_id,
        "module_id": context.module_id,
        "user_id": context.user_id,
    })
