"""App bootstrap entry point."""
from flask import Flask

from app import create_app
from portal import configure_portal_context


def bootstrap_app() -> Flask:
    app = create_app()
    configure_portal_context(app)
    return app


def main() -> None:
    app = bootstrap_app()
    app.run(host="0.0.0.0", port=8000, debug=True)


if __name__ == "__main__":
    main()
