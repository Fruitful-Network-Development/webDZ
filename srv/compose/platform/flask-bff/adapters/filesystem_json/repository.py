"""Filesystem-backed data environment repository."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Mapping, Optional

from adapters.filesystem_json.loader import load_resources
from core.config.data_env import DATA_ENV_BOOTSTRAP
from core.data_env.errors import (
    DataEnvBootstrapError,
    DataEnvResourceNotFound,
)
from core.data_env.repository import DataEnvRepository
from core.data_env.validators import (
    validate_local_domain,
    validate_manifest,
    validate_mss,
)


class FilesystemJsonDataEnvRepository(DataEnvRepository):
    def __init__(self, root_path: Path):
        self._root_path = root_path
        self._resources = load_resources(root_path, ignore_files=[DATA_ENV_BOOTSTRAP])
        self._bootstrap = self._load_bootstrap(root_path)
        self._local_index = self._build_local_index()
        self._validate_core_resources()

    def list_resources(self) -> list[str]:
        return sorted(self._resources.keys())

    def get_resource(self, resource_id: str) -> Any:
        if resource_id not in self._resources:
            raise DataEnvResourceNotFound(resource_id)
        return self._resources[resource_id]

    def find_by_local_id(self, local_id: str) -> Optional[Mapping[str, Any]]:
        if not isinstance(local_id, str):
            return None
        return self._local_index.get(local_id)

    def get_platform_mss(self) -> Mapping[str, Any]:
        return self._get_core("platform_mss")

    def get_platform_manifest(self) -> Any:
        return self._get_core("platform_manifest")

    def get_platform_local(self) -> list[Mapping[str, Any]]:
        payload = self._get_core("platform_local")
        return payload if isinstance(payload, list) else []

    def get_platform_fnd(self) -> Mapping[str, Any]:
        return self._get_core("platform_fnd")

    def _get_core(self, key: str) -> Any:
        resource_id = self._bootstrap.get(key)
        if not resource_id:
            raise DataEnvBootstrapError(
                str(self._root_path / DATA_ENV_BOOTSTRAP),
                f"missing bootstrap key '{key}'",
            )
        return self.get_resource(resource_id)

    def _load_bootstrap(self, root_path: Path) -> Dict[str, str]:
        bootstrap_path = root_path / DATA_ENV_BOOTSTRAP
        if not bootstrap_path.exists():
            raise DataEnvBootstrapError(str(bootstrap_path), "missing bootstrap file")
        try:
            payload = json.loads(bootstrap_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise DataEnvBootstrapError(
                str(bootstrap_path),
                f"invalid JSON: {exc.msg}",
            ) from exc
        if not isinstance(payload, dict):
            raise DataEnvBootstrapError(str(bootstrap_path), "bootstrap must be an object")
        return {str(k): str(v) for k, v in payload.items()}

    def _build_local_index(self) -> Dict[str, Mapping[str, Any]]:
        local_resource_id = self._bootstrap.get("platform_local")
        if not local_resource_id:
            return {}
        payload = self._resources.get(local_resource_id)
        if not isinstance(payload, list):
            return {}
        index: Dict[str, Mapping[str, Any]] = {}
        for entry in payload:
            if not isinstance(entry, Mapping):
                continue
            local_id = entry.get("local_id")
            if isinstance(local_id, str):
                index[local_id] = entry
        return index

    def _validate_core_resources(self) -> None:
        mss_id = self._bootstrap.get("platform_mss")
        if mss_id:
            validate_mss(mss_id, self.get_resource(mss_id))
        manifest_id = self._bootstrap.get("platform_manifest")
        if manifest_id:
            validate_manifest(manifest_id, self.get_resource(manifest_id))
        local_id = self._bootstrap.get("platform_local")
        if local_id:
            validate_local_domain(local_id, self.get_resource(local_id))

