"""Tenant configuration registry backed by JSON files."""
from __future__ import annotations

import json
import os
import re
import shutil
import tempfile
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


class TenantExistsError(TenantRegistryError):
    def __init__(self, tenant_id: str):
        super().__init__(
            code="tenant_exists",
            message=f"Tenant '{tenant_id}' already exists",
            details={"tenant_id": tenant_id},
        )


class TenantIdError(TenantRegistryError):
    def __init__(self, tenant_id: str):
        super().__init__(
            code="invalid_tenant_id",
            message=f"Invalid tenant_id '{tenant_id}'",
            details={"tenant_id": tenant_id},
        )


def _index_path() -> Path:
    return TENANTS_DIR / "index.json"


def _schema_path() -> Path:
    return TENANTS_DIR / "tenant.schema.json"


def _tenant_path(tenant_id: str) -> Path:
    return TENANTS_DIR / tenant_id / "tenant.json"


def _tenant_dir(tenant_id: str) -> Path:
    return TENANTS_DIR / tenant_id


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


_TENANT_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")


def validate_tenant_id(tenant_id: str) -> str:
    if not isinstance(tenant_id, str):
        raise TenantIdError(str(tenant_id))
    cleaned = tenant_id.strip()
    if not cleaned:
        raise TenantIdError(tenant_id)
    if os.sep in cleaned or (os.altsep and os.altsep in cleaned):
        raise TenantIdError(tenant_id)
    if ".." in cleaned or "/" in cleaned or "\\" in cleaned:
        raise TenantIdError(tenant_id)
    if not _TENANT_ID_PATTERN.fullmatch(cleaned):
        raise TenantIdError(tenant_id)
    return cleaned


def _reference_mode(path: Optional[Path]) -> Optional[int]:
    if path and path.exists():
        return path.stat().st_mode & 0o777
    return None


def _write_json_atomic(path: Path, payload: Any, *, reference_path: Optional[Path] = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = _reference_mode(path) or _reference_mode(reference_path)
    temp_handle = None
    temp_path = None
    try:
        temp_handle = tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=str(path.parent),
            delete=False,
        )
        temp_path = Path(temp_handle.name)
        json.dump(payload, temp_handle, indent=2)
        temp_handle.write("\n")
        temp_handle.flush()
        os.fsync(temp_handle.fileno())
        temp_handle.close()
        if mode is not None:
            os.chmod(temp_handle.name, mode)
        os.replace(temp_handle.name, path)
    except Exception:
        if temp_handle and not temp_handle.closed:
            temp_handle.close()
        if temp_path and temp_path.exists():
            temp_path.unlink(missing_ok=True)
        raise


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


def _load_index_data() -> Dict[str, Any]:
    data = _load_json(_index_path())
    if not isinstance(data, dict) or "tenants" not in data:
        raise TenantIndexError("index.json must contain a 'tenants' list")
    tenants = data["tenants"]
    if not isinstance(tenants, list) or not all(isinstance(t, str) for t in tenants):
        raise TenantIndexError("'tenants' must be a list of strings")
    return data


def _write_index(tenants: List[str]) -> None:
    _write_json_atomic(
        _index_path(),
        {"tenants": tenants},
        reference_path=_index_path(),
    )


def _ensure_tenant_schema(tenant_id: str, data: Dict[str, Any]) -> None:
    validator = _validator()
    errors = sorted(validator.iter_errors(data), key=lambda e: e.path)
    if errors:
        raise TenantValidationError(tenant_id, errors[0].message)
    if data.get("tenant_id") != tenant_id:
        raise TenantValidationError(
            tenant_id,
            "tenant_id field does not match requested tenant",
        )


def create_tenant(data: Dict[str, Any]) -> Dict[str, Any]:
    tenant_id = validate_tenant_id(data.get("tenant_id"))
    _ensure_tenant_schema(tenant_id, data)

    tenant_dir = _tenant_dir(tenant_id)
    tenant_path = _tenant_path(tenant_id)
    if tenant_dir.exists() or tenant_path.exists():
        raise TenantExistsError(tenant_id)

    index_data = _load_index_data()
    tenants = index_data["tenants"]
    if tenant_id in tenants:
        raise TenantExistsError(tenant_id)

    dir_mode = _reference_mode(TENANTS_DIR)
    tenant_dir.mkdir(mode=dir_mode or 0o755, exist_ok=False)
    if dir_mode is not None:
        os.chmod(tenant_dir, dir_mode)

    try:
        _write_json_atomic(
            tenant_path,
            data,
            reference_path=_index_path(),
        )
        tenants = tenants + [tenant_id]
        _write_index(tenants)
    except Exception:
        shutil.rmtree(tenant_dir, ignore_errors=True)
        raise

    return data


def update_tenant(tenant_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    tenant_id = validate_tenant_id(tenant_id)
    tenant_path = _tenant_path(tenant_id)
    if not tenant_path.exists():
        raise TenantNotFoundError(tenant_id)

    _ensure_tenant_schema(tenant_id, data)
    _write_json_atomic(
        tenant_path,
        data,
        reference_path=tenant_path,
    )
    return data


def delete_tenant(tenant_id: str, *, hard: bool = False) -> Dict[str, Any]:
    tenant_id = validate_tenant_id(tenant_id)
    tenant_dir = _tenant_dir(tenant_id)
    tenant_path = _tenant_path(tenant_id)
    if not tenant_path.exists():
        raise TenantNotFoundError(tenant_id)

    index_data = _load_index_data()
    tenants = [t for t in index_data["tenants"] if t != tenant_id]

    if hard:
        _write_index(tenants)
        try:
            shutil.rmtree(tenant_dir)
        except Exception as exc:
            _write_index(index_data["tenants"])
            raise TenantRegistryError(
                code="tenant_delete_failed",
                message=f"Failed to delete tenant '{tenant_id}': {exc}",
                details={"tenant_id": tenant_id},
            ) from exc
        return {"tenant_id": tenant_id, "deleted": True, "hard": True}

    current = _load_json(tenant_path)
    updated = dict(current)
    updated["disabled"] = True
    try:
        _write_json_atomic(
            tenant_path,
            updated,
            reference_path=tenant_path,
        )
        _write_index(tenants)
    except Exception:
        _write_json_atomic(
            tenant_path,
            current,
            reference_path=tenant_path,
        )
        raise

    return updated


def load_tenant(tenant_id: str) -> Dict[str, Any]:
    tenant_id = validate_tenant_id(tenant_id)
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
