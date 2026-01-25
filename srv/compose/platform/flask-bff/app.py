"""Flask BFF (Keycloak-only, DB-free)."""
from __future__ import annotations

from flask import Flask, jsonify, session

import db
from authz import get_current_user, is_root_admin
from config import COOKIE_SECURE, SESSION_SECRET
from routes.admin import admin_bp
from routes.auth import auth_bp
from routes.common import require_login, require_tenant_access, require_tenant_context
from routes.tables import seed_demo_data, tables_bp
from routes.tenant import tenant_bp
from routes.user import user_bp


def create_app() -> Flask:
    app = Flask(__name__)
    app.secret_key = SESSION_SECRET

    # Session cookie policy:
    # - Phase 3 (SSH tunnel via http://localhost:8001): COOKIE_SECURE=false
    # - Phase 4 (public HTTPS): COOKIE_SECURE=true
    app.config.update(
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=COOKIE_SECURE,
    )

    # Flask versions differ on lifecycle hooks; avoid before_serving/after_serving.
    # Initialize lazily once per Gunicorn worker, before the first request is handled.
    _init_state = {"done": False}

    @app.before_request
    def _init_once() -> None:
        if _init_state["done"]:
            return
        _init_state["done"] = True
        db.get_conn()
        seed_demo_data()

    # Ensure DB cleanup when the application context tears down.
    @app.teardown_appcontext
    def _close_db(_exc) -> None:
        db.close_conn()

    @app.context_processor
    def inject_template_context():
        user = get_current_user()
        return {
            "current_user": user,
            "is_root_admin": is_root_admin(user) if user else False,
        }

    @app.get("/health")
    def health():
        return jsonify({"status": "ok"}), 200

    @app.get("/t/<tenant_id>/ping")
    @require_login
    @require_tenant_context
    def tenant_ping(tenant_id: str):
        guard = require_tenant_access(tenant_id)
        if guard:
            return guard
        user = session.get("user") or {}
        return jsonify({
            "ok": True,
            "tenant": tenant_id,
            "user": {
                "user_id": user.get("user_id"),
                "display_name": user.get("display_name"),
                "email": user.get("email"),
            },
        }), 200

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(tables_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(tenant_bp)

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
