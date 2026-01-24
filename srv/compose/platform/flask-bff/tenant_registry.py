"""Tenant configuration registry backed by JSON files."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from jsonschema import Draft202012Validator, FormatChecker


TENANTS_DIR = Path(__file__).resolve().parent / "data" / "tenants"


@dataclass
class TenantRegistryError(Exception):
    code: str
    message: str
    details: Optional[Dict[str, Any]] = None

    def __str__(self) -> str:
        return self.message


class TenantNotFoundError(TenantRegistryError):
    def __init__(self, tenant_id: str):
        super().__init__(
            code="tenant_not_found",
            message=f"Tenant '{tenant_id}' not found",
            details={"tenant_id": tenant_id},
        )


class TenantValidationError(TenantRegistryError):
    def __init__(self, tenant_id: str, error: str):
        super().__init__(
            code="tenant_invalid",
            message=f"Tenant '{tenant_id}' failed validation: {error}",
            details={"tenant_id": tenant_id, "error": error},
        )


class TenantIndexError(TenantRegistryError):
    def __init__(self, error: str):
        super().__init__(
            code="tenant_index_invalid",
            message=f"Tenant index invalid: {error}",
            details={"error": error},
        )


def _index_path() -> Path:
    return TENANTS_DIR / "index.json"


def _schema_path() -> Path:
    return TENANTS_DIR / "tenant.schema.json"


def _tenant_path(tenant_id: str) -> Path:
    return TENANTS_DIR / tenant_id / "tenant.json"


def _load_json(path: Path) -> Any:
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except FileNotFoundError as exc:
        raise TenantRegistryError(
            code="file_not_found",
            message=f"Required tenant registry file missing: {path}",
            details={"path": str(path)},
        ) from exc
    except json.JSONDecodeError as exc:
        raise TenantRegistryError(
            code="invalid_json",
            message=f"Invalid JSON in {path}: {exc.msg}",
            details={"path": str(path), "line": exc.lineno},
        ) from exc


_validator_cache: Dict[str, Draft202012Validator] = {}


def _validator() -> Draft202012Validator:
    schema_path = str(_schema_path())
    cached = _validator_cache.get(schema_path)
    if cached:
        return cached
    schema = _load_json(_schema_path())
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    _validator_cache.clear()
    _validator_cache[schema_path] = validator
    return validator


def list_tenants() -> List[str]:
    data = _load_json(_index_path())
    if not isinstance(data, dict) or "tenants" not in data:
        raise TenantIndexError("index.json must contain a 'tenants' list")
    tenants = data["tenants"]
    if not isinstance(tenants, list) or not all(isinstance(t, str) for t in tenants):
        raise TenantIndexError("'tenants' must be a list of strings")
    return tenants


def load_tenant(tenant_id: str) -> Dict[str, Any]:
    path = _tenant_path(tenant_id)
    if not path.exists():
        raise TenantNotFoundError(tenant_id)
    data = _load_json(path)
    validator = _validator()
    errors = sorted(validator.iter_errors(data), key=lambda e: e.path)
    if errors:
        raise TenantValidationError(tenant_id, errors[0].message)
    if data.get("tenant_id") != tenant_id:
        raise TenantValidationError(
            tenant_id,
            "tenant_id field does not match requested tenant",
        )
    return data


def validate_return_to(tenant_cfg: Dict[str, Any], return_to_url: Optional[str]) -> bool:
    if return_to_url is None:
        return True
    allowed = tenant_cfg.get("allowed_return_to") or []
    return return_to_url in allowed


def tenant_public_view(tenant_cfg: Dict[str, Any]) -> Dict[str, Any]:
    sanitized = dict(tenant_cfg)
    for key in list(sanitized.keys()):
        if "secret" in key and key != "oidc_client_secret_env":
            sanitized.pop(key)
    return sanitized
