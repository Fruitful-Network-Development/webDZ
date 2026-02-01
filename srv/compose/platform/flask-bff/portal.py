"""Authenticated portal routes and context helpers."""
from __future__ import annotations

from dataclasses import dataclass

from flask import Blueprint, Flask, abort, current_app, jsonify, request

from contracts.console_data import ConsoleDataContract
from contracts.identity_access import IdentityAccessContract
from contracts.portal_configuration import PortalConfigurationContract

portal_blueprint = Blueprint("portal", __name__)


@dataclass(frozen=True)
class PortalContext:
    msn_id: str
    user_id: str
    module_id: str | None = None


@dataclass(frozen=True)
class PortalContracts:
    identity_access: IdentityAccessContract
    portal_configuration: PortalConfigurationContract
    console_data: ConsoleDataContract


def configure_portal_context(app: Flask) -> None:
    """Initialize portal orchestration state for the app lifecycle."""
    app.extensions.setdefault("portal_context", {"status": "initialized"})
    app.extensions.setdefault(
        "portal_contracts",
        PortalContracts(
            identity_access=IdentityAccessContract(),
            portal_configuration=PortalConfigurationContract(),
            console_data=ConsoleDataContract(),
        ),
    )


def _get_portal_contracts() -> PortalContracts:
    contracts = current_app.extensions.get("portal_contracts")
    if not isinstance(contracts, PortalContracts):
        abort(500, description="Portal contracts unavailable.")
    return contracts


def _require_authenticated_user() -> str:
    user_id = request.headers.get("X-Portal-User")
    if not user_id:
        abort(401, description="Missing portal user header.")
    return user_id


def _build_portal_context(msn_id: str, user_id: str, module_id: str | None = None) -> PortalContext:
    return PortalContext(msn_id=msn_id, user_id=user_id, module_id=module_id)


def _call_contract(method, fallback_payload, payload_label: str):
    try:
        return method()
    except NotImplementedError:
        return {"status": "stub", "contract": payload_label, "payload": fallback_payload}


@portal_blueprint.route("/portal/login", methods=["GET", "POST"])
def portal_login():
    """Portal login placeholder."""
    user_id = _require_authenticated_user()
    contracts = _get_portal_contracts()
    access_payload = _call_contract(
        lambda: contracts.identity_access.evaluate_access(
            subject={"user_id": user_id},
            requested_scopes=["portal:login"],
            context={"route": "portal_login"},
        ),
        fallback_payload={"user_id": user_id, "scopes": ["portal:login"]},
        payload_label="identity_access.evaluate_access",
    )
    return jsonify({"status": "login", "user_id": user_id, "access": access_payload})


@portal_blueprint.route("/portal/<msn_id>")
def portal_entry(msn_id: str):
    user_id = _require_authenticated_user()
    context = _build_portal_context(msn_id, user_id)
    contracts = _get_portal_contracts()
    config_payload = _call_contract(
        lambda: contracts.portal_configuration.fetch_configuration(
            portal_id={"msn_id": context.msn_id},
            sections=["entry"],
            context={"user_id": context.user_id},
        ),
        fallback_payload={"msn_id": context.msn_id, "sections": ["entry"]},
        payload_label="portal_configuration.fetch_configuration",
    )
    return jsonify({
        "portal": "entry",
        "msn_id": context.msn_id,
        "user_id": context.user_id,
        "orchestrator": current_app.extensions.get("portal_context", {}),
        "configuration": config_payload,
    })


@portal_blueprint.route("/portal/<msn_id>/module/<module_id>")
def portal_module(msn_id: str, module_id: str):
    user_id = _require_authenticated_user()
    context = _build_portal_context(msn_id, user_id, module_id=module_id)
    contracts = _get_portal_contracts()
    module_payload = _call_contract(
        lambda: contracts.console_data.fetch_console_data(
            console_id={
                "msn_id": context.msn_id,
                "module_id": context.module_id,
                "user_id": context.user_id,
            },
            domains=["module"],
            context={"user_id": context.user_id},
        ),
        fallback_payload={"msn_id": context.msn_id, "module_id": context.module_id},
        payload_label="console_data.fetch_console_data",
    )
    return jsonify({
        "portal": "module",
        "msn_id": context.msn_id,
        "module_id": context.module_id,
        "user_id": context.user_id,
        "module": module_payload,
    })
