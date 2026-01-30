# app.py
from flask import Flask

from portal import register_portal_routes
from websites import register_website_routes


def create_app() -> Flask:
    app = Flask(__name__)

    # Core configuration (placeholder)
    app.config["APP_NAME"] = "platform"

    # Register route groups
    register_portal_routes(app)
    register_website_routes(app)

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=8000, debug=True)
