"""Shared helpers for ingesting and cleaning demo data."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional


class DemoDataError(ValueError):
    """Raised when demo data cannot be parsed or validated."""


@dataclass(frozen=True)
class ContractMapping:
    """Define how demo-data files map to contract placeholders."""

    name: str
    filename_prefixes: tuple[str, ...]
    contract_reference: str


CONTRACT_MAPPINGS = (
    ContractMapping(
        name="portal_configuration",
        filename_prefixes=(
            "platform.conspectus",
            "mss.anthology",
            "mss.compendium",
        ),
        contract_reference="PortalConfigurationContract (contracts/portal_configuration.py)",
    ),
    ContractMapping(
        name="identity_access",
        filename_prefixes=("platform.beneficiary",),
        contract_reference="IdentityAccessContract (contracts/identity_access.py)",
    ),
    ContractMapping(
        name="console_data",
        filename_prefixes=("3_2_3",),
        contract_reference="ConsoleDataContract (contracts/console_data.py)",
    ),
    ContractMapping(
        name="muniment_access",
        filename_prefixes=("mss.",),
        contract_reference="MunimentAccessContract (contracts/muniment_access.py)",
    ),
)


def resolve_contract(filename: str, default_contract: Optional[str] = None) -> str:
    """Return the contract placeholder for the file name."""

    for mapping in CONTRACT_MAPPINGS:
        if any(filename.startswith(prefix) for prefix in mapping.filename_prefixes):
            return mapping.name
    if default_contract:
        return default_contract
    return "unmapped_contract"


def iter_demo_files(data_dir: Path, glob_pattern: str = "*.json") -> Iterable[Path]:
    """Yield demo-data files in a predictable order."""

    return sorted(path for path in data_dir.glob(glob_pattern) if path.is_file())


def parse_demo_payload(path: Path) -> list[dict]:
    """Parse demo data payloads, handling pseudo-JSON objects."""

    raw_text = path.read_text(encoding="utf-8")
    try:
        payload = json.loads(raw_text)
    except json.JSONDecodeError:
        return _parse_pseudo_json_objects(raw_text, path)

    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        return [payload]
    raise DemoDataError(f"Unsupported JSON payload in {path}")


def _parse_pseudo_json_objects(raw_text: str, path: Path) -> list[dict]:
    """Extract JSON objects from files wrapped in placeholder braces."""

    items: list[dict] = []
    depth = 0
    in_string = False
    escape = False
    start: Optional[int] = None

    for index, char in enumerate(raw_text):
        if in_string:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == '"':
                in_string = False
            continue

        if char == '"':
            in_string = True
            continue

        if char == "{":
            depth += 1
            if depth == 2:
                start = index
            continue

        if char == "}":
            if depth == 2 and start is not None:
                fragment = raw_text[start : index + 1]
                items.append(_parse_fragment(fragment, path))
                start = None
            depth -= 1

    if not items:
        raise DemoDataError(f"No JSON objects found in {path}")

    return items


def _parse_fragment(fragment: str, path: Path) -> dict:
    try:
        parsed = json.loads(fragment)
    except json.JSONDecodeError:
        coerced = _coerce_missing_colons(fragment)
        try:
            parsed = json.loads(coerced)
        except json.JSONDecodeError as exc:
            snippet = fragment.strip().replace("\n", " ")
            raise DemoDataError(f"Invalid JSON fragment in {path}: {snippet}") from exc

    if not isinstance(parsed, dict):
        raise DemoDataError(f"Expected object payload in {path}, got {type(parsed).__name__}")
    return parsed


def _coerce_missing_colons(fragment: str) -> str:
    """Attempt to replace pseudo key/value pairs that omit colons."""
    chars = list(fragment)
    container_stack: list[str] = []
    in_string = False
    escape = False
    string_prev_non_space: str | None = None
    index = 0

    while index < len(chars):
        char = chars[index]

        if in_string:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == '"':
                in_string = False
                if container_stack and container_stack[-1] == "object" and string_prev_non_space in ("{", ","):
                    look = index + 1
                    while look < len(chars) and chars[look].isspace():
                        look += 1
                    if look < len(chars) and chars[look] == ",":
                        look_ahead = look + 1
                        while look_ahead < len(chars) and chars[look_ahead].isspace():
                            look_ahead += 1
                        if look_ahead < len(chars) and chars[look_ahead] == '"':
                            chars[look] = ":"
            index += 1
            continue

        if char == '"':
            in_string = True
            prev = index - 1
            while prev >= 0 and chars[prev].isspace():
                prev -= 1
            string_prev_non_space = chars[prev] if prev >= 0 else None
        elif char == "{":
            container_stack.append("object")
        elif char == "[":
            container_stack.append("array")
        elif char in ("]", "}"):
            if container_stack:
                container_stack.pop()

        index += 1

    return "".join(chars)
