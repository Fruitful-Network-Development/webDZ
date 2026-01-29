"""Tenant console module configuration helpers."""
from __future__ import annotations

from typing import Any


def enabled_console_modules(tenant_cfg: dict[str, Any]) -> list[str]:
    modules = tenant_cfg.get("console_modules") or {}
    if isinstance(modules, dict):
        return [name for name, enabled in modules.items() if enabled]
    return list(modules)
