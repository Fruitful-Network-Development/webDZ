"""Repository interface for data environment access."""
from __future__ import annotations

from typing import Any, Mapping, Optional, Protocol


class DataEnvRepository(Protocol):
    def list_resources(self) -> list[str]:
        ...

    def get_resource(self, resource_id: str) -> Any:
        ...

    def find_by_local_id(self, local_id: str) -> Optional[Mapping[str, Any]]:
        ...

    def get_platform_mss(self) -> Mapping[str, Any]:
        ...

    def get_platform_manifest(self) -> Any:
        ...

    def get_platform_local(self) -> list[Mapping[str, Any]]:
        ...

    def get_platform_fnd(self) -> Mapping[str, Any]:
        ...

