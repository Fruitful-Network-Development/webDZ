from pathlib import Path

from conftest import load_app


FIXTURE_ROOT = Path(__file__).resolve().parent / "fixtures" / "data_env"


def test_admin_data_env_endpoints(monkeypatch):
    monkeypatch.setenv("DATA_ENV_ROOT", str(FIXTURE_ROOT))
    app_module = load_app(monkeypatch)
    app_module.app.config.update(TESTING=True)

    with app_module.app.test_client() as client:
        with client.session_transaction() as sess:
            sess["user"] = {"user_id": "u-1", "realm_roles": ["root_admin"]}

        resp = client.get("/admin/data-env/resources")
        assert resp.status_code == 200
        assert "platform.mss" in resp.get_json()["resources"]

        resp = client.get("/admin/data-env/resource/platform.mss")
        assert resp.status_code == 200
        assert resp.get_json()["resource"]["msn_id"] == "platform"

        resp = client.get("/admin/platform/mss")
        assert resp.status_code == 200
        assert resp.get_json()["msn_id"] == "platform"

        resp = client.get("/admin/platform/manifest")
        assert resp.status_code == 200
        assert resp.get_json()[0]["archetype"] == "5_1"

        resp = client.get("/admin/platform/local")
        assert resp.status_code == 200
        assert resp.get_json()[0]["local_id"] == "1"

