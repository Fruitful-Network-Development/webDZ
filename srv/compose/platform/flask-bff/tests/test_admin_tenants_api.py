import json
import uuid
from pathlib import Path

import pytest

from conftest import load_app

import tenant_registry


def _seed_tenant_registry(tmp_path: Path) -> Path:
    tenants_dir = tmp_path / "tenants"
    tenants_dir.mkdir()
    schema_src = (
        Path(__file__).resolve().parents[1]
        / "data"
        / "tenants"
        / "tenant.schema.json"
    )
    (tenants_dir / "tenant.schema.json").write_text(
        schema_src.read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    (tenants_dir / "index.json").write_text(
        json.dumps({"tenants": []}, indent=2) + "\n",
        encoding="utf-8",
    )
    return tenants_dir


def _configure_registry(monkeypatch, tenants_dir: Path) -> None:
    monkeypatch.setattr(tenant_registry, "TENANTS_DIR", tenants_dir)
    tenant_registry._validator_cache.clear()


def _root_admin_session(client) -> None:
    with client.session_transaction() as sess:
        sess["user"] = {
            "user_id": str(uuid.uuid4()),
            "realm_roles": ["root_admin"],
        }


def _tenant_payload(tenant_id: str) -> dict:
    return {
        "tenant_id": tenant_id,
        "client_domain": "tenant.example.com",
        "allowed_return_to": ["/admin"],
        "oidc_client_id": "client-id",
        "oidc_client_secret_env": "OIDC_SECRET",
        "console_modules": {"animals": True},
    }


@pytest.mark.usefixtures("db_cleanup")
def test_admin_tenant_create_success(monkeypatch, tmp_path, db_url):
    app_module = load_app(monkeypatch, db_url=db_url)
    app_module.app.config.update(TESTING=True)

    tenants_dir = _seed_tenant_registry(tmp_path)
    _configure_registry(monkeypatch, tenants_dir)

    with app_module.app.test_client() as client:
        _root_admin_session(client)
        payload = _tenant_payload("tenant-create")
        resp = client.post("/api/admin/tenants", json=payload)
        assert resp.status_code == 201
        assert resp.get_json()["tenant"]["tenant_id"] == "tenant-create"

    assert "tenant-create" in tenant_registry.list_tenants()
    assert (tenants_dir / "tenant-create" / "tenant.json").exists()


@pytest.mark.usefixtures("db_cleanup")
def test_admin_tenant_create_schema_failure(monkeypatch, tmp_path, db_url):
    app_module = load_app(monkeypatch, db_url=db_url)
    app_module.app.config.update(TESTING=True)

    tenants_dir = _seed_tenant_registry(tmp_path)
    _configure_registry(monkeypatch, tenants_dir)

    with app_module.app.test_client() as client:
        _root_admin_session(client)
        payload = _tenant_payload("tenant-bad")
        payload.pop("client_domain")
        resp = client.post("/api/admin/tenants", json=payload)
        assert resp.status_code == 400
        assert resp.get_json()["error"] == "tenant_invalid"


@pytest.mark.usefixtures("db_cleanup")
def test_admin_tenant_get_and_update(monkeypatch, tmp_path, db_url):
    app_module = load_app(monkeypatch, db_url=db_url)
    app_module.app.config.update(TESTING=True)

    tenants_dir = _seed_tenant_registry(tmp_path)
    _configure_registry(monkeypatch, tenants_dir)

    with app_module.app.test_client() as client:
        _root_admin_session(client)
        payload = _tenant_payload("tenant-update")
        create_resp = client.post("/api/admin/tenants", json=payload)
        assert create_resp.status_code == 201

        get_resp = client.get("/api/admin/tenants/tenant-update")
        assert get_resp.status_code == 200
        assert get_resp.get_json()["tenant"]["tenant_id"] == "tenant-update"

        payload["client_domain"] = "updated.example.com"
        update_resp = client.put("/api/admin/tenants/tenant-update", json=payload)
        assert update_resp.status_code == 200
        assert update_resp.get_json()["tenant"]["client_domain"] == "updated.example.com"


@pytest.mark.usefixtures("db_cleanup")
def test_admin_tenant_update_invalid_schema(monkeypatch, tmp_path, db_url):
    app_module = load_app(monkeypatch, db_url=db_url)
    app_module.app.config.update(TESTING=True)

    tenants_dir = _seed_tenant_registry(tmp_path)
    _configure_registry(monkeypatch, tenants_dir)

    with app_module.app.test_client() as client:
        _root_admin_session(client)
        payload = _tenant_payload("tenant-update-invalid")
        create_resp = client.post("/api/admin/tenants", json=payload)
        assert create_resp.status_code == 201

        payload.pop("allowed_return_to")
        update_resp = client.put("/api/admin/tenants/tenant-update-invalid", json=payload)
        assert update_resp.status_code == 400
        assert update_resp.get_json()["error"] == "tenant_invalid"


@pytest.mark.usefixtures("db_cleanup")
def test_admin_tenant_delete_soft(monkeypatch, tmp_path, db_url):
    app_module = load_app(monkeypatch, db_url=db_url)
    app_module.app.config.update(TESTING=True)

    tenants_dir = _seed_tenant_registry(tmp_path)
    _configure_registry(monkeypatch, tenants_dir)

    with app_module.app.test_client() as client:
        _root_admin_session(client)
        payload = _tenant_payload("tenant-soft")
        create_resp = client.post("/api/admin/tenants", json=payload)
        assert create_resp.status_code == 201

        delete_resp = client.delete("/api/admin/tenants/tenant-soft")
        assert delete_resp.status_code == 200
        assert delete_resp.get_json()["tenant"]["disabled"] is True

    assert "tenant-soft" not in tenant_registry.list_tenants()
    tenant_data = json.loads(
        (tenants_dir / "tenant-soft" / "tenant.json").read_text(encoding="utf-8")
    )
    assert tenant_data["disabled"] is True


@pytest.mark.usefixtures("db_cleanup")
def test_admin_tenant_delete_hard(monkeypatch, tmp_path, db_url):
    app_module = load_app(monkeypatch, db_url=db_url)
    app_module.app.config.update(TESTING=True)

    tenants_dir = _seed_tenant_registry(tmp_path)
    _configure_registry(monkeypatch, tenants_dir)

    with app_module.app.test_client() as client:
        _root_admin_session(client)
        payload = _tenant_payload("tenant-hard")
        create_resp = client.post("/api/admin/tenants", json=payload)
        assert create_resp.status_code == 201

        delete_resp = client.delete("/api/admin/tenants/tenant-hard", query_string={"hard": "1"})
        assert delete_resp.status_code == 200
        assert delete_resp.get_json()["tenant"]["hard"] is True

    assert "tenant-hard" not in tenant_registry.list_tenants()
    assert not (tenants_dir / "tenant-hard").exists()
