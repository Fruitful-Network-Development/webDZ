# app-portal.py
from flask import Flask, redirect, jsonify, request


def register_portal_routes(app: Flask) -> None:
    """
    Register all portal-related routes:
    - admin
    - tenant console
    - identity landing
    """

    @app.route("/portal")
    def portal_root():
        """
        Entry point after authentication.
        Later this will decide:
        - admin portal
        - tenant portal
        - forbidden / not provisioned
        """
        return jsonify({
            "portal": "root",
            "status": "unresolved",
        })

    @app.route("/admin")
    def admin_console():
        return jsonify({
            "portal": "admin",
            "message": "Admin console placeholder",
        })

    @app.route("/t/<tenant_id>/console")
    def tenant_console(tenant_id: str):
        return jsonify({
            "portal": "tenant",
            "tenant_id": tenant_id,
            "message": "Tenant console placeholder",
        })
