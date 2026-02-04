"""App bootstrap entry point."""
from __future__ import annotations

from importlib.machinery import SourceFileLoader
from importlib.util import module_from_spec, spec_from_loader
from pathlib import Path
import os
import sys

from flask import Flask

BASE_DIR = Path(__file__).resolve().parent


def _load_module(module_name: str, file_path: Path):
    loader = SourceFileLoader(module_name, str(file_path))
    spec = spec_from_loader(module_name, loader)
    if spec is None:
        raise RuntimeError(f"Unable to load module: {file_path}")
    module = module_from_spec(spec)
    sys.modules[module_name] = module
    loader.exec_module(module)  # type: ignore[arg-type]
    return module


def create_app() -> Flask:
    app = Flask(__name__)
    app.config.setdefault("APP_NAME", "platform")
    app.config.setdefault("MUNIMENT_PUBLIC_RESOURCES", {})
    app.config.setdefault("MUNIMENT_DEFAULT_PUBLIC", {"here"})
    session_secret = os.getenv("SESSION_SECRET")
    if session_secret:
        app.config["SECRET_KEY"] = session_secret
    cookie_secure = os.getenv("COOKIE_SECURE", "").lower() in ("1", "true", "yes")
    app.config["SESSION_COOKIE_SECURE"] = cookie_secure
    app.config.setdefault("SESSION_COOKIE_SAMESITE", "Lax")
    app.config.setdefault("SESSION_COOKIE_HTTPONLY", True)

    portal_module = _load_module("portal.portal_app", BASE_DIR / "portal" / "portal-app.py")
    webapp_module = _load_module("webapp.web_app", BASE_DIR / "webapp" / "web-app.py")

    portal_module.configure_portal_context(app)
    app.register_blueprint(portal_module.portal_blueprint)
    app.register_blueprint(webapp_module.websites_blueprint)

    return app


def main() -> None:
    app = create_app()
    app.run(host="0.0.0.0", port=8000, debug=True)


if __name__ == "__main__":
    main()
