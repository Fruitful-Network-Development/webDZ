import importlib
import sys
import types
from pathlib import Path


def _load_app(monkeypatch):
    monkeypatch.setenv("OIDC_ISSUER", "https://issuer.example.com/realms/test")
    monkeypatch.setenv("OIDC_CLIENT_ID", "flask-bff")
    monkeypatch.setenv("OIDC_CLIENT_SECRET", "secret")
    monkeypatch.setenv("SESSION_SECRET", "test-secret")
    monkeypatch.setenv(
        "DATA_ENV_ROOT",
        str(Path(__file__).resolve().parent / "fixtures" / "data_env"),
    )

    requests_stub = types.SimpleNamespace(
        get=lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("requests not available")),
        post=lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("requests not available")),
    )
    monkeypatch.setitem(sys.modules, "requests", requests_stub)

    app_dir = Path(__file__).resolve().parents[1]
    if str(app_dir) not in sys.path:
        sys.path.insert(0, str(app_dir))
    if "app" in sys.modules:
        del sys.modules["app"]
    return importlib.import_module("app")


def test_login_missing_tenant(monkeypatch):
    app_module = _load_app(monkeypatch)
    app_module.app.config.update(TESTING=True)

    with app_module.app.test_client() as client:
        resp = client.get("/login")
        assert resp.status_code == 400
        assert resp.get_json() == {"error": "missing_tenant"}


def test_login_disallowed_return_to(monkeypatch):
    app_module = _load_app(monkeypatch)
    app_module.app.config.update(TESTING=True)

    with app_module.app.test_client() as client:
        resp = client.get(
            "/login?tenant=cuyahogaterravita&return_to=https://evil.example.com/"
        )
        assert resp.status_code == 400
        assert resp.get_json() == {"error": "invalid_return_to"}


def test_ping_requires_login(monkeypatch):
    app_module = _load_app(monkeypatch)
    app_module.app.config.update(TESTING=True)

    with app_module.app.test_client() as client:
        resp = client.get("/t/x/ping")
        assert resp.status_code == 401
        assert resp.get_json() == {
            "error": "not_authenticated",
            "message": "Authentication required.",
        }


def test_ping_allows_tenant_admin(monkeypatch):
    app_module = _load_app(monkeypatch)
    app_module.app.config.update(TESTING=True)

    with app_module.app.test_client() as client:
        with client.session_transaction() as sess:
            sess["tenant_id"] = "x"
            sess["user"] = {
                "user_id": "u-1",
                "msn_id": "TEST-MSN-1",
                "realm_roles": ["tenant_admin:x"],
            }
        resp = client.get("/t/x/ping")
        assert resp.status_code == 200
        assert resp.get_json()["tenant"] == "x"


def test_ping_blocks_wrong_tenant_admin(monkeypatch):
    app_module = _load_app(monkeypatch)
    app_module.app.config.update(TESTING=True)

    with app_module.app.test_client() as client:
        with client.session_transaction() as sess:
            sess["tenant_id"] = "x"
            sess["user"] = {
                "user_id": "u-1",
                "msn_id": "TEST-MSN-2",
                "realm_roles": ["tenant_admin:y"],
            }
        resp = client.get("/t/x/ping")
        assert resp.status_code == 403
        assert resp.get_json() == {"error": "forbidden", "message": "Access forbidden."}


def test_tenants_requires_auth(monkeypatch):
    app_module = _load_app(monkeypatch)
    app_module.app.config.update(TESTING=True)

    with app_module.app.test_client() as client:
        resp = client.get("/_tenants")
        assert resp.status_code == 401
        assert resp.get_json() == {
            "error": "not_authenticated",
            "message": "Authentication required.",
        }


def test_tenants_forbidden_without_root_admin(monkeypatch):
    app_module = _load_app(monkeypatch)
    app_module.app.config.update(TESTING=True)

    with app_module.app.test_client() as client:
        with client.session_transaction() as sess:
            sess["user"] = {"user_id": "u-1", "realm_roles": ["tenant_admin:x"]}
        resp = client.get("/_tenants")
        assert resp.status_code == 403
        assert resp.get_json() == {
            "error": "forbidden",
            "message": "Access forbidden.",
            "missing_role": "root_admin",
        }

def test_root_renders_landing_when_unauth(monkeypatch):
    app_module = _load_app(monkeypatch)
    app_module.app.config.update(TESTING=True)

    with app_module.app.test_client() as client:
        resp = client.get("/")
        assert resp.status_code == 200
        assert b"Sign in" in resp.data


def test_admin_redirects_to_login_when_unauth(monkeypatch):
    app_module = _load_app(monkeypatch)
    app_module.app.config.update(TESTING=True)

    with app_module.app.test_client() as client:
        resp = client.get("/admin", follow_redirects=False)
        assert resp.status_code == 302
        assert resp.headers["Location"] == "/login?tenant=platform&return_to=/admin"


def test_tenants_allows_root_admin(monkeypatch):
    app_module = _load_app(monkeypatch)
    app_module.app.config.update(TESTING=True)

    with app_module.app.test_client() as client:
        with client.session_transaction() as sess:
            sess["user"] = {"user_id": "u-1", "realm_roles": ["root_admin"]}
        resp = client.get("/_tenants")
        assert resp.status_code == 200
        assert "cuyahogaterravita" in resp.get_json()["tenants"]


def test_admin_overview_renders(monkeypatch):
    app_module = _load_app(monkeypatch)
    app_module.app.config.update(TESTING=True)

    with app_module.app.test_client() as client:
        with client.session_transaction() as sess:
            sess["user"] = {"user_id": "u-1", "realm_roles": ["root_admin"]}
        resp = client.get("/admin")
        assert resp.status_code == 200
        assert b"Admin Console" in resp.data


def test_admin_tenants_api(monkeypatch):
    app_module = _load_app(monkeypatch)
    app_module.app.config.update(TESTING=True)

    with app_module.app.test_client() as client:
        with client.session_transaction() as sess:
            sess["user"] = {"user_id": "u-1", "realm_roles": ["root_admin"]}
        resp = client.get("/api/admin/tenants")
        assert resp.status_code == 200
        assert "platform" in resp.get_json()["tenants"]


def test_tenant_detail_strips_secret(monkeypatch):
    app_module = _load_app(monkeypatch)
    app_module.app.config.update(TESTING=True)

    def _fake_load_tenant(tenant_id: str):
        return {
            "tenant_id": tenant_id,
            "client_domain": "example.com",
            "allowed_return_to": ["https://example.com/"],
            "oidc_client_id": "flask-bff",
            "oidc_client_secret": "super-secret",
            "oidc_client_secret_env": "ENV_SECRET_NAME",
            "console_modules": {"schema_builder": True},
        }

    import routes.common as common

    monkeypatch.setattr(common, "load_tenant", _fake_load_tenant)

    with app_module.app.test_client() as client:
        with client.session_transaction() as sess:
            sess["user"] = {"user_id": "u-1", "realm_roles": ["root_admin"]}
        resp = client.get("/_tenants/example")
        assert resp.status_code == 200
        tenant = resp.get_json()["tenant"]
        assert tenant["oidc_client_secret_env"] == "ENV_SECRET_NAME"
        assert "oidc_client_secret" not in tenant
