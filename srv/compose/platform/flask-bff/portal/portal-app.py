"""Authenticated portal routes and context helpers."""
from __future__ import annotations

from dataclasses import dataclass

from flask import Blueprint, Flask, abort, current_app, jsonify, request, render_template

from auth.identity_access import IdentityAccessContract
from auth.authz import get_current_user, is_root_admin, is_tenant_admin
from portal.console.console_data import ConsoleDataContract
from portal.portal_configuration import PortalConfigurationContract
from portal.portal_store import PortalStore, PortalStoreError

portal_blueprint = Blueprint("portal", __name__, template_folder="console/UI")


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
    store = PortalStore()
    app.extensions.setdefault("portal_context", {"status": "initialized"})
    app.extensions.setdefault(
        "portal_contracts",
        PortalContracts(
            identity_access=IdentityAccessContract(store),
            portal_configuration=PortalConfigurationContract(store),
            console_data=ConsoleDataContract(store),
        ),
    )


def _get_portal_contracts() -> PortalContracts:
    contracts = current_app.extensions.get("portal_contracts")
    if not isinstance(contracts, PortalContracts):
        abort(500, description="Portal contracts unavailable.")
    return contracts


def _require_authenticated_user() -> str:
    current_user = get_current_user()
    if isinstance(current_user, dict):
        user_id = current_user.get("user_id")
        if user_id:
            return str(user_id)
    user_id = request.headers.get("X-Portal-User")
    if not user_id:
        abort(401, description="Missing portal user header or bearer token.")
    return user_id


def _build_portal_context(msn_id: str, user_id: str, module_id: str | None = None) -> PortalContext:
    return PortalContext(msn_id=msn_id, user_id=user_id, module_id=module_id)


def _call_contract(method, fallback_payload, payload_label: str):
    try:
        return method()
    except PortalStoreError as exc:
        abort(500, description=f"{payload_label} failed: {exc}")
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


def _console_auth_context() -> dict[str, object]:
    current_user = get_current_user()
    return {
        "current_user": current_user,
        "is_root_admin": is_root_admin(current_user),
        "is_tenant_admin": is_tenant_admin(current_user),
    }


@portal_blueprint.route("/admin")
def admin_console_overview():
    user_id = _require_authenticated_user()
    contracts = _get_portal_contracts()
    payload = _call_contract(
        lambda: contracts.console_data.fetch_console_data(
            console_id={"user_id": user_id},
            domains=["admin", "overview"],
            filters={"mode": "admin"},
            context={"user_id": user_id},
        ),
        fallback_payload={"user_id": user_id},
        payload_label="console_data.fetch_console_data",
    )
    return render_template(
        "console/admin_overview.html",
        **_console_auth_context(),
        payload=payload,
    )


@portal_blueprint.route("/admin/tenants")
def admin_tenant_tables():
    user_id = _require_authenticated_user()
    contracts = _get_portal_contracts()
    payload = _call_contract(
        lambda: contracts.console_data.fetch_console_data(
            console_id={"user_id": user_id},
            domains=["admin", "tenants"],
            filters={"mode": "admin"},
            context={"user_id": user_id},
        ),
        fallback_payload={"user_id": user_id},
        payload_label="console_data.fetch_console_data",
    )
    return render_template(
        "console/admin_tenants.html",
        **_console_auth_context(),
        payload=payload,
    )


@portal_blueprint.route("/admin/registry")
def admin_registry():
    user_id = _require_authenticated_user()
    contracts = _get_portal_contracts()
    payload = _call_contract(
        lambda: contracts.console_data.fetch_console_data(
            console_id={"user_id": user_id},
            domains=["admin", "registry"],
            filters={"mode": "admin"},
            context={"user_id": user_id},
        ),
        fallback_payload={"user_id": user_id},
        payload_label="console_data.fetch_console_data",
    )
    return render_template(
        "console/admin_registry.html",
        **_console_auth_context(),
        payload=payload,
    )


@portal_blueprint.route("/console/<msn_id>")
def tenant_console(msn_id: str):
    user_id = _require_authenticated_user()
    contracts = _get_portal_contracts()
    payload = _call_contract(
        lambda: contracts.console_data.fetch_console_data(
            console_id={"msn_id": msn_id, "user_id": user_id},
            domains=["tenant"],
            context={"user_id": user_id},
        ),
        fallback_payload={"msn_id": msn_id, "user_id": user_id},
        payload_label="console_data.fetch_console_data",
    )
    return render_template(
        "console/tenant_console.html",
        **_console_auth_context(),
        payload=payload,
    )


@portal_blueprint.route("/api/admin/tenants")
def admin_tenant_list():
    contracts = _get_portal_contracts()
    payload = _call_contract(
        lambda: contracts.console_data.fetch_console_data(
            console_id={"source": "admin"},
            domains=["admin", "tenants"],
            filters={"mode": "admin"},
        ),
        fallback_payload={},
        payload_label="console_data.fetch_console_data",
    )
    compendium = payload.get("compendium", []) if isinstance(payload, dict) else []
    tenants = [item.get("msn_id") for item in compendium if item.get("msn_id")]
    return jsonify({"tenants": tenants})
