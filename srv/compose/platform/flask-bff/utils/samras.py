"""SAMRAS helpers for schema registry and validation."""
from __future__ import annotations

import json
import re
from typing import Any, Dict, Optional, Tuple

import db

SAMRAS_MODES = {"exact", "group", "existential"}


def is_samras_domain(ref_domain: Optional[str]) -> bool:
    if not ref_domain:
        return False
    return ref_domain.strip().upper().startswith("SAMRAS")


def parse_samras_ref_domain(ref_domain: str) -> Tuple[Optional[str], Optional[int]]:
    ref_domain = ref_domain.strip()
    if not is_samras_domain(ref_domain):
        return None, None
    suffix = ref_domain[len("SAMRAS"):]
    if not suffix:
        return None, None
    suffix = suffix.lstrip(":/")
    if not suffix:
        return None, None
    parts = [part for part in re.split(r"[:/]", suffix) if part]
    if len(parts) < 2:
        return None, None
    domain = parts[0].strip()
    if not domain:
        return None, None
    try:
        version = int(parts[1])
    except ValueError:
        return None, None
    return domain, version


def samras_layout_lookup(domain: str, version: int) -> Optional[Dict[str, Any]]:
    row = db.fetchone(
        """
        SELECT domain, version, count_stream, traversal_spec
        FROM platform.samras_layout
        WHERE domain = %s AND version = %s
        """,
        (domain, version),
    )
    if not row:
        return None
    count_stream = row.get("count_stream")
    if count_stream is None:
        count_bytes = b""
    else:
        count_bytes = bytes(count_stream)
    row["count_stream"] = [byte for byte in count_bytes]
    return row


def parse_samras_address(address: str) -> Optional[list[int]]:
    if not isinstance(address, str):
        return None
    address = address.strip()
    if not address:
        return None
    parts = re.split(r"[./-]", address)
    parsed = []
    for part in parts:
        if not part.isdigit():
            return None
        parsed.append(int(part))
    return parsed if parsed else None


def samras_address_in_stream(address: list[int], count_stream: list[int]) -> bool:
    if not address:
        return False
    if len(address) > len(count_stream):
        return False
    for idx, count in zip(address, count_stream):
        if idx < 0 or idx >= count:
            return False
    return True


def samras_node_key(address: list[int]) -> str:
    return ".".join(str(part) for part in address)


def samras_find_node(traversal_spec: Any, address: list[int]) -> Optional[Any]:
    if traversal_spec is None:
        return None
    if isinstance(traversal_spec, dict):
        nodes = traversal_spec.get("nodes")
        if isinstance(nodes, dict):
            return nodes.get(samras_node_key(address))
    current = traversal_spec
    for idx in address:
        if isinstance(current, dict):
            children = current.get("children")
        elif isinstance(current, list):
            children = current
        else:
            return None
        if not isinstance(children, list) or idx >= len(children):
            return None
        current = children[idx]
    return current


def resolve_samras_context(field: Dict[str, Any]) -> Tuple[Optional[dict], Optional[str]]:
    constraints = field.get("constraints") or {}
    ref_domain = field.get("ref_domain")
    domain, version = parse_samras_ref_domain(ref_domain or "")
    if not domain:
        domain = constraints.get("samras_domain") or constraints.get("domain")
    if version is None:
        version_value = constraints.get("samras_version", constraints.get("version"))
        if isinstance(version_value, int):
            version = version_value
        elif isinstance(version_value, str) and version_value.isdigit():
            version = int(version_value)
    if not domain or version is None:
        return None, "missing_samras_layout"
    layout = samras_layout_lookup(domain, version)
    if not layout:
        return None, "missing_samras_layout"
    return layout, None


def resolve_samras_mode(constraints: Dict[str, Any]) -> Tuple[Optional[str], Optional[str]]:
    mode = constraints.get("samras_mode") or constraints.get("mode")
    if mode is None:
        return "exact", None
    if not isinstance(mode, str):
        return None, "invalid_samras_mode"
    mode = mode.strip().lower()
    if mode not in SAMRAS_MODES:
        return None, "invalid_samras_mode"
    return mode, None


def validate_samras_reference(
    field: Dict[str, Any],
    value: Dict[str, Any],
    has_system_id: bool,
    has_system_value: bool,
) -> Optional[str]:
    constraints = field.get("constraints") or {}
    mode, error = resolve_samras_mode(constraints)
    if error:
        return error
    if mode == "exact":
        if not has_system_id:
            return "missing_system_id"
        if has_system_value:
            return "system_value_not_allowed"
    address_value = value.get("system_id") if has_system_id else value.get("system_value")
    if not isinstance(address_value, str):
        return "invalid_samras_address"
    address = parse_samras_address(address_value)
    if not address:
        return "invalid_samras_address"
    layout, error = resolve_samras_context(field)
    if error:
        return error
    if not samras_address_in_stream(address, layout["count_stream"]):
        return "invalid_samras_address"
    return None


def validate_archetype_field_constraints(
    ref_domain: Optional[str],
    constraints: Optional[Dict[str, Any]],
) -> Optional[str]:
    if constraints is None:
        return None
    if not isinstance(constraints, dict):
        return "invalid_constraints"
    if is_samras_domain(ref_domain):
        mode, error = resolve_samras_mode(constraints)
        if error:
            return error
        if mode:
            constraints["samras_mode"] = mode
        return None
    if "samras_mode" in constraints:
        return "samras_mode_not_allowed"
    return None
