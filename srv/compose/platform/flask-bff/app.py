# app.py
from flask import Flask

from portal import portal_blueprint
from websites import websites_blueprint


def create_app() -> Flask:
    app = Flask(__name__)

    # Core configuration (placeholder)
    app.config["APP_NAME"] = "platform"
    app.config.setdefault("MUNIMENT_PUBLIC_RESOURCES", {})
    app.config.setdefault("MUNIMENT_DEFAULT_PUBLIC", {"here"})

    # Register route groups
    app.register_blueprint(portal_blueprint)
    app.register_blueprint(websites_blueprint)

    return app
