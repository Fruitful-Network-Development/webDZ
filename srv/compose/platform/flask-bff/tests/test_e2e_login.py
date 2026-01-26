import base64
import json
import uuid
from urllib.parse import parse_qs, urlparse

from conftest import load_app


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"status {self.status_code}")

    def json(self):
        return self._payload


def _encode_segment(payload):
    return base64.urlsafe_b64encode(json.dumps(payload).encode("utf-8")).decode("utf-8").rstrip("=")


def test_login_flow_and_console_render(monkeypatch, db_conn, db_url, db_cleanup):
    app_module = load_app(monkeypatch, db_url=db_url)
    app_module.app.config.update(TESTING=True)

    user_id = str(uuid.uuid4())
    msn_id = "SAMRAS-TEST-LOGIN"
    with db_conn.cursor() as cur:
        cur.execute(
            "INSERT INTO platform.mss_profile (msn_id, user_id, display_name, role) VALUES (%s, %s, %s, %s)",
            (msn_id, user_id, "Login User", "member"),
        )

    tenant_id = "cuyahogaterravita"
    return_to = f"/t/{tenant_id}/console"

    discovery = {
        "authorization_endpoint": "https://issuer.example.com/auth",
        "token_endpoint": "https://issuer.example.com/token",
        "userinfo_endpoint": "https://issuer.example.com/userinfo",
    }

    access_payload = {
        "sub": user_id,
        "realm_access": {"roles": ["root_admin"]},
    }
    token = f"{_encode_segment({'alg': 'none'})}.{_encode_segment(access_payload)}.sig"

    def fake_get(url, *args, **kwargs):
        if url.endswith("/.well-known/openid-configuration"):
            return FakeResponse(discovery)
        if url == discovery["userinfo_endpoint"]:
            return FakeResponse({
                "sub": user_id,
                "preferred_username": "login-user",
                "email": "login@example.com",
            })
        raise AssertionError(f"unexpected GET {url}")

    def fake_post(url, *args, **kwargs):
        if url == discovery["token_endpoint"]:
            return FakeResponse({"access_token": token})
        raise AssertionError(f"unexpected POST {url}")

    import routes.auth as auth_routes

    monkeypatch.setattr(auth_routes, "requests", type("Req", (), {"get": fake_get, "post": fake_post})())
    monkeypatch.setattr(auth_routes, "validate_return_to", lambda *_args, **_kwargs: True)

    with app_module.app.test_client() as client:
        login_resp = client.get(f"/login?tenant={tenant_id}&return_to={return_to}")
        assert login_resp.status_code == 302

        redirect_url = urlparse(login_resp.headers["Location"])
        query = parse_qs(redirect_url.query)
        state = query["state"][0]

        callback_resp = client.get(
            f"/callback?code=demo-code&state={state}",
            follow_redirects=False,
        )
        assert callback_resp.status_code == 302
        assert callback_resp.headers["Location"] == return_to

        me_resp = client.get("/me")
        assert me_resp.status_code == 200
        payload = me_resp.get_json()
        assert payload["authenticated"] is True
        assert payload["hierarchy"]["msn_id"] == msn_id

        admin_resp = client.get("/admin")
        assert admin_resp.status_code == 200

        console_resp = client.get(f"/t/{tenant_id}/console")
        assert console_resp.status_code == 200
        assert b"Animals" in console_resp.data

        animals_resp = client.get(f"/t/{tenant_id}/console/animals")
        assert animals_resp.status_code == 200
        from config import DEMO_TABLE_ID

        assert f"GET /api/t/{tenant_id}/tables/{DEMO_TABLE_ID}".encode("utf-8") in animals_resp.data
