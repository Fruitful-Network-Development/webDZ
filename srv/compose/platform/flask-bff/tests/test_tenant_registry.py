import json
import sys
from pathlib import Path

APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

import tenant_registry


def test_list_tenants_reads_index():
    tenants = tenant_registry.list_tenants()
    assert "cuyahogaterravita" in tenants


def test_load_tenant_requires_tenant_id(tmp_path, monkeypatch):
    tenants_dir = tmp_path / "tenants"
    tenants_dir.mkdir()

    schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "required": ["tenant_id"],
        "properties": {"tenant_id": {"type": "string"}},
    }
    (tenants_dir / "tenant.schema.json").write_text(json.dumps(schema))
    (tenants_dir / "index.json").write_text(json.dumps({"tenants": ["alpha"]}))

    tenant_dir = tenants_dir / "alpha"
    tenant_dir.mkdir()
    (tenant_dir / "tenant.json").write_text(json.dumps({"client_domain": "example.com"}))

    monkeypatch.setattr(tenant_registry, "TENANTS_DIR", tenants_dir)
    tenant_registry._validator_cache.clear()

    try:
        tenant_registry.load_tenant("alpha")
    except tenant_registry.TenantValidationError as exc:
        assert exc.code == "tenant_invalid"
        assert "tenant_id" in exc.message
    else:
        raise AssertionError("Expected TenantValidationError")


def test_validate_return_to():
    tenant_cfg = {"allowed_return_to": ["https://allowed.example.com/"]}
    assert tenant_registry.validate_return_to(tenant_cfg, None)
    assert tenant_registry.validate_return_to(tenant_cfg, "https://allowed.example.com/")
    assert not tenant_registry.validate_return_to(
        tenant_cfg, "https://evil.example.com/"
    )
