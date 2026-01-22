import os
import psycopg
from psycopg.rows import dict_row
from flask import Flask, redirect, url_for, session, request, jsonify
from authlib.integrations.flask_client import OAuth

def db_conn():
    return psycopg.connect(
        host=os.environ["PLATFORM_DB_HOST"],
        port=os.environ.get("PLATFORM_DB_PORT", "5432"),
        dbname=os.environ["PLATFORM_DB_NAME"],
        user=os.environ["PLATFORM_DB_USER"],
        password=os.environ["PLATFORM_DB_PASSWORD"],
        row_factory=dict_row,
    )


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

    def ensure_schema():
    with db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS user_profiles (
                    user_id TEXT PRIMARY KEY,
                    preferred_username TEXT,
                    email TEXT,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
                );
            """)
        conn.commit()

    oauth = OAuth(app)

    oauth.register(
        name="keycloak",
        client_id=os.environ["OIDC_CLIENT_ID"],
        client_secret=os.environ["OIDC_CLIENT_SECRET"],
        server_metadata_url=f"{os.environ['OIDC_ISSUER']}/.well-known/openid-configuration",
        client_kwargs={"scope": "openid profile email"},
    )

    ensure_schema()

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

        # Persist minimal profile to platform DB
        u = session["user"]
        with db_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO user_profiles (user_id, preferred_username, email)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (user_id)
                    DO UPDATE SET
                        preferred_username = EXCLUDED.preferred_username,
                        email = EXCLUDED.email,
                        updated_at = now();
                """, (u["sub"], u.get("preferred_username"), u.get("email")))
            conn.commit()

        return redirect("/me")

    @app.get("/db/me")
    def db_me():
        user = session.get("user")
        if not user:
            return {"error": "not authenticated"}, 401
        with db_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM user_profiles WHERE user_id = %s", (user["sub"],))
                row = cur.fetchone()
        return row or {"error": "not found"}, (200 if row else 404)

    
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

    # @app.get("/_set_test")
    # def set_test():
    #     session["user"] = {"sub": "test", "preferred_username": "test"}
    #     return redirect("/me")

    return app


app = create_app()
