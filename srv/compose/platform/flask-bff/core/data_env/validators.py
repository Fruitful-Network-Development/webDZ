"""Minimal validation for core data env resources."""
from __future__ import annotations

from typing import Any, Mapping, Sequence

from core.data_env.errors import DataEnvValidationError


def validate_mss(resource_id: str, payload: Any) -> None:
    if not isinstance(payload, Mapping):
        raise DataEnvValidationError(resource_id, "mss payload must be an object")
    missing = []
    if not payload.get("msn_id"):
        missing.append("msn_id")
    if not payload.get("entity_type"):
        missing.append("entity_type")
    exposed = payload.get("exposed")
    if not isinstance(exposed, list):
        missing.append("exposed")
    if missing:
        raise DataEnvValidationError(resource_id, f"missing fields: {', '.join(missing)}")


def validate_manifest(resource_id: str, payload: Any) -> None:
    if not isinstance(payload, list):
        raise DataEnvValidationError(resource_id, "manifest payload must be a list")
    for entry in payload:
        if not isinstance(entry, Mapping):
            raise DataEnvValidationError(resource_id, "manifest entries must be objects")
        if not entry.get("archetype"):
            raise DataEnvValidationError(resource_id, "manifest entry missing archetype")
        if not entry.get("table"):
            raise DataEnvValidationError(resource_id, "manifest entry missing table")
        has_column = "column_count" in entry or "colummn_count" in entry
        if not has_column:
            raise DataEnvValidationError(resource_id, "manifest entry missing column_count")


def validate_local_domain(resource_id: str, payload: Any) -> None:
    if not isinstance(payload, list):
        raise DataEnvValidationError(resource_id, "local domain must be a list")
    for entry in payload:
        if not isinstance(entry, Mapping):
            raise DataEnvValidationError(resource_id, "local domain entries must be objects")
        if not entry.get("local_id"):
            raise DataEnvValidationError(resource_id, "local domain entry missing local_id")
        if not entry.get("title"):
            raise DataEnvValidationError(resource_id, "local domain entry missing title")

