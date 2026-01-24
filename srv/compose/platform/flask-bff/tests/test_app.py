import importlib
import sys
import types
from pathlib import Path


def _load_app(monkeypatch, allowlist="https://cuyahogaterravita.com/,https://fruitfulnetworkdevelopment.com/"):
    monkeypatch.setenv("OIDC_ISSUER", "https://issuer.example.com/realms/test")
    monkeypatch.setenv("OIDC_CLIENT_ID", "flask-bff")
    monkeypatch.setenv("OIDC_CLIENT_SECRET", "secret")
    monkeypatch.setenv("SESSION_SECRET", "test-secret")
    monkeypatch.setenv("RETURN_TO_ALLOWLIST", allowlist)

    if "requests" not in sys.modules:
        requests_stub = types.SimpleNamespace(
            get=lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("requests not available")),
            post=lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("requests not available")),
        )
        sys.modules["requests"] = requests_stub

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
    app_module = _load_app(monkeypatch, allowlist="https://allowed.example.com/")
    app_module.app.config.update(TESTING=True)

    with app_module.app.test_client() as client:
        resp = client.get("/login?tenant=alpha&return_to=https://evil.example.com/")
        assert resp.status_code == 400
        assert resp.get_json() == {"error": "invalid_return_to"}


def test_ping_requires_login(monkeypatch):
    app_module = _load_app(monkeypatch)
    app_module.app.config.update(TESTING=True)

    with app_module.app.test_client() as client:
        resp = client.get("/t/x/ping")
        assert resp.status_code == 401
        assert resp.get_json() == {"error": "not_authenticated"}


def test_ping_allows_tenant_admin(monkeypatch):
    app_module = _load_app(monkeypatch)
    app_module.app.config.update(TESTING=True)

    with app_module.app.test_client() as client:
        with client.session_transaction() as sess:
            sess["tenant_id"] = "x"
            sess["user"] = {
                "user_id": "u-1",
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
                "realm_roles": ["tenant_admin:y"],
            }
        resp = client.get("/t/x/ping")
        assert resp.status_code == 403
        assert resp.get_json() == {"error": "forbidden"}
