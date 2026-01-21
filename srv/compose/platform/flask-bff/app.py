import os
from flask import Flask, redirect, url_for, session, request, jsonify
from authlib.integrations.flask_client import OAuth

def create_app():
    app = Flask(__name__)

    # Session signing (no server-side store yet; Phase 3 is minimal)
    app.secret_key = os.environ["SESSION_SECRET"]

    # Phase 3 NOTE:
    # We are testing over http://localhost:8001 via SSH tunnel,
    # so Secure cookies MUST be disabled for now.
    app.config.update(
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=False,  # MUST flip to True in Phase 4 (HTTPS)
    )

    oauth = OAuth(app)

    oauth.register(
        name="keycloak",
        client_id=os.environ["OIDC_CLIENT_ID"],
        client_secret=os.environ["OIDC_CLIENT_SECRET"],
        server_metadata_url=f"{os.environ['OIDC_ISSUER']}/.well-known/openid-configuration",
        client_kwargs={"scope": "openid profile email"},
    )

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.get("/login")
    def login():
        redirect_uri = url_for("callback", _external=True)
        return oauth.keycloak.authorize_redirect(redirect_uri)

    @app.get("/callback")
    def callback():
        token = oauth.keycloak.authorize_access_token()
        userinfo = token.get("userinfo")

        if not userinfo:
            return "Login failed", 401

        # Store minimal identity in session
        session["user"] = {
            "sub": userinfo.get("sub"),
            "preferred_username": userinfo.get("preferred_username"),
            "email": userinfo.get("email"),
        }

        return redirect("/me")

    @app.get("/me")
    def me():
        user = session.get("user")
        if not user:
            return {"error": "not authenticated"}, 401
        return jsonify(user)

    @app.get("/logout")
    def logout():
        session.clear()
        return {"status": "logged out"}

    return app


app = create_app()
