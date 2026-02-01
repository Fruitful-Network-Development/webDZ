"""Public website APIs and muniment enforcement."""
from __future__ import annotations

from flask import Blueprint, abort, current_app, jsonify

websites_blueprint = Blueprint("websites", __name__)


def _is_resource_public(msn_id: str, resource: str) -> bool:
    configured = current_app.config.get("MUNIMENT_PUBLIC_RESOURCES", {})
    public_resources = configured.get(msn_id)
    if public_resources is None:
        default_public = current_app.config.get("MUNIMENT_DEFAULT_PUBLIC", set())
        return resource in default_public
    return resource in public_resources


def _enforce_muniment_rules(msn_id: str, resource: str) -> None:
    if not _is_resource_public(msn_id, resource):
        abort(403, description="Resource not published by muniment rules.")


@websites_blueprint.route("/api/<msn_id>/<resource>")
def public_resource(msn_id: str, resource: str):
    _enforce_muniment_rules(msn_id, resource)
    return jsonify({
        "msn_id": msn_id,
        "resource": resource,
        "access": "public",
    })
