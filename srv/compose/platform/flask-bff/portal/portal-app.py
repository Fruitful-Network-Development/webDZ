"""Authenticated portal routes and context helpers."""
from __future__ import annotations

from dataclasses import dataclass
import os
from urllib.parse import unquote

import requests
from flask import Blueprint, Flask, abort, current_app, jsonify, request, render_template, session, redirect

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


def _exchange_code_for_token(code: str, redirect_uri: str) -> None:
    issuer = os.getenv("KEYCLOAK_ISSUER") or os.getenv("OIDC_ISSUER")
    client_id = os.getenv("OIDC_CLIENT_ID") or os.getenv("KEYCLOAK_AUDIENCE")
    client_secret = os.getenv("OIDC_CLIENT_SECRET") or os.getenv("KEYCLOAK_CLIENT_SECRET")
    if not issuer or not client_id:
        abort(500, description="OIDC issuer/client_id not configured.")
    token_url = f"{issuer.rstrip('/')}/protocol/openid-connect/token"
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri,
        "client_id": client_id,
    }
    if client_secret:
        data["client_secret"] = client_secret
    response = requests.post(token_url, data=data, timeout=10)
    if response.status_code != 200:
        current_app.logger.warning(
            "Token exchange failed: %s %s (redirect_uri=%s token_url=%s client_id=%s)",
            response.status_code,
            response.text,
            redirect_uri,
            token_url,
            client_id,
        )
        abort(401, description="Token exchange failed.")
    payload = response.json()
    access_token = payload.get("access_token")
    if not access_token:
        abort(401, description="Token exchange missing access_token.")
    session["access_token"] = access_token
    if payload.get("refresh_token"):
        session["refresh_token"] = payload.get("refresh_token")


def _maybe_consume_oidc_code():
    code = request.args.get("code")
    if not code:
        return None
    callback_url = os.getenv("OIDC_CALLBACK_URL", request.base_url)
    _exchange_code_for_token(code, callback_url)
    return redirect(request.base_url)


@portal_blueprint.route("/callback")
def oidc_callback():
    code = request.args.get("code")
    if not code:
        abort(400, description="Missing authorization code.")
    state = request.args.get("state") or ""
    return_to = request.args.get("return_to") or unquote(state) or "/admin"
    if not return_to.startswith("/"):
        return_to = "/admin"
    callback_url = os.getenv("OIDC_CALLBACK_URL", request.base_url)
    _exchange_code_for_token(code, callback_url)
    return redirect(return_to)




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


def _require_root_admin() -> None:
    if not is_root_admin(get_current_user()):
        abort(403, description="Admin access required.")


@portal_blueprint.route("/admin")
def admin_console_overview():
    redirect_response = _maybe_consume_oidc_code()
    if redirect_response:
        return redirect_response
    user_id = _require_authenticated_user()
    _require_root_admin()
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
        "admin_overview.html",
        **_console_auth_context(),
        payload=payload,
    )


@portal_blueprint.route("/admin/tenants")
def admin_tenant_tables():
    redirect_response = _maybe_consume_oidc_code()
    if redirect_response:
        return redirect_response
    user_id = _require_authenticated_user()
    _require_root_admin()
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
        "admin_tenants.html",
        **_console_auth_context(),
        payload=payload,
    )


@portal_blueprint.route("/admin/registry")
def admin_registry():
    redirect_response = _maybe_consume_oidc_code()
    if redirect_response:
        return redirect_response
    user_id = _require_authenticated_user()
    _require_root_admin()
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
        "admin_registry.html",
        **_console_auth_context(),
        payload=payload,
    )


@portal_blueprint.route("/admin/email")
def admin_email_service():
    redirect_response = _maybe_consume_oidc_code()
    if redirect_response:
        return redirect_response
    user_id = _require_authenticated_user()
    _require_root_admin()
    contracts = _get_portal_contracts()
    payload = _call_contract(
        lambda: contracts.console_data.fetch_console_data(
            console_id={"user_id": user_id},
            domains=["admin", "email"],
            filters={"mode": "admin"},
            context={"user_id": user_id},
        ),
        fallback_payload={"user_id": user_id},
        payload_label="console_data.fetch_console_data",
    )
    return render_template(
        "admin_email.html",
        **_console_auth_context(),
        payload=payload,
    )


@portal_blueprint.route("/console/<msn_id>")
def tenant_console(msn_id: str):
    redirect_response = _maybe_consume_oidc_code()
    if redirect_response:
        return redirect_response
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
        "tenant_console.html",
        **_console_auth_context(),
        payload=payload,
    )


@portal_blueprint.route("/api/admin/tenants")
def admin_tenant_list():
    _require_root_admin()
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


@portal_blueprint.route("/api/admin/correspondence", methods=["GET", "POST"])
def admin_correspondence_collection():
    _require_root_admin()
    contracts = _get_portal_contracts()
    store: PortalStore = contracts.console_data._store  # type: ignore[attr-defined]

    if request.method == "GET":
        msn_id = request.args.get("msn_id") or None
        entries = store.fetch_correspondence_entries(msn_id)
        return jsonify({"items": entries})

    payload = request.get_json(silent=True) or {}
    msn_id = payload.get("msn_id")
    source_file = payload.get("source_file")
    entry_payload = payload.get("payload")
    if not msn_id or not source_file or not isinstance(entry_payload, dict):
        abort(400, description="msn_id, source_file, and payload are required.")
    created = store.create_correspondence_entry(
        msn_id=str(msn_id),
        source_file=str(source_file),
        payload=entry_payload,
    )
    return jsonify({"item": created}), 201


@portal_blueprint.route("/api/admin/correspondence/<int:entry_id>", methods=["PUT", "DELETE"])
def admin_correspondence_item(entry_id: int):
    _require_root_admin()
    contracts = _get_portal_contracts()
    store: PortalStore = contracts.console_data._store  # type: ignore[attr-defined]

    if request.method == "DELETE":
        deleted = store.delete_correspondence_entry(entry_id=entry_id)
        return jsonify({"deleted": deleted})

    payload = request.get_json(silent=True) or {}
    entry_payload = payload.get("payload")
    if not isinstance(entry_payload, dict):
        abort(400, description="payload must be an object.")
    updated = store.update_correspondence_entry(entry_id=entry_id, payload=entry_payload)
    return jsonify({"item": updated})


@portal_blueprint.route("/api/newsletter/subscribe", methods=["POST"])
def newsletter_subscribe():
    payload = request.get_json(silent=True) or {}
    msn_id = payload.get("msn_id")
    opus_local_id = payload.get("opus_local_id")
    email = payload.get("email")
    if not msn_id or not opus_local_id or not email:
        abort(400, description="msn_id, opus_local_id, and email are required.")
    contracts = _get_portal_contracts()
    muniments = contracts.console_data._store.fetch_muniment_entries(str(msn_id))  # type: ignore[attr-defined]
    allowed = any(
        (row.get("opus_local_id") == opus_local_id)
        and (row.get("muniment") or "").lower() == "open"
        for row in muniments
    )
    if not allowed:
        abort(403, description="Newsletter subscription not permitted.")
    return jsonify({"status": "accepted", "msn_id": msn_id, "opus_local_id": opus_local_id, "email": email})


@portal_blueprint.route("/api/newsletter/unsubscribe", methods=["POST"])
def newsletter_unsubscribe():
    payload = request.get_json(silent=True) or {}
    msn_id = payload.get("msn_id")
    opus_local_id = payload.get("opus_local_id")
    email = payload.get("email")
    if not msn_id or not opus_local_id or not email:
        abort(400, description="msn_id, opus_local_id, and email are required.")
    contracts = _get_portal_contracts()
    muniments = contracts.console_data._store.fetch_muniment_entries(str(msn_id))  # type: ignore[attr-defined]
    allowed = any(
        (row.get("opus_local_id") == opus_local_id)
        and (row.get("muniment") or "").lower() == "open"
        for row in muniments
    )
    if not allowed:
        abort(403, description="Newsletter unsubscribe not permitted.")
    return jsonify({"status": "accepted", "msn_id": msn_id, "opus_local_id": opus_local_id, "email": email})