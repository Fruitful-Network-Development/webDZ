"""Statonomy SAMRAS importer helpers."""
from __future__ import annotations

import json
import re
import uuid
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

import psycopg2
from psycopg2 import sql
from psycopg2.extras import Json

from utils.general_tables import general_table_name

DEFAULT_INPUT_PATH = "/srv/old-data/SAMRAS-statonomy.json"
DOMAIN = "statonomy"
VERSION = 1
TENANT_ID = "platform"
ARCHETYPE_NAME = "samras_statonomy_nodes"

TABLE_LOCAL_ID = str(uuid.uuid5(uuid.NAMESPACE_DNS, "platformsamras_statonomy_table_v1"))
TABLE_ID_NAMESPACE = uuid.uuid5(uuid.NAMESPACE_DNS, "platformsamras_statonomy_table_v1:records")
TABLE_NAME_MSN_ID = "platform"

ADDRESS_REGEX = re.compile(r"^[0-9]+(_[0-9]+)*$")

TRAVERSAL_SPEC = {
    "encoding": "varint_u32",
    "order": "preorder",
    "root_path": ["octant"],
    "child_key": "members",
    "address_delim": "_",
    "address_field": "msn_id",
}


def encode_varint_u32(value: int) -> bytes:
    if value < 0 or value > 0xFFFFFFFF:
        raise ValueError(f"varint_u32 out of range: {value}")
    out = bytearray()
    while True:
        byte = value & 0x7F
        value >>= 7
        if value:
            out.append(byte | 0x80)
        else:
            out.append(byte)
            break
    return bytes(out)


def encode_count_stream(counts: Iterable[int]) -> bytes:
    out = bytearray()
    for count in counts:
        out.extend(encode_varint_u32(count))
    return bytes(out)


def _load_json(path: str) -> Dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Statonomy JSON root must be an object")
    return data


def _load_root_nodes(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    root_nodes = data.get("octant")
    if not isinstance(root_nodes, list):
        raise ValueError("Statonomy JSON must contain an octant list")
    return root_nodes


def _node_children(node: Dict[str, Any]) -> List[Dict[str, Any]]:
    members = node.get("members") or []
    if not isinstance(members, list):
        raise ValueError("Statonomy node members must be a list")
    return members


def iter_nodes_preorder(root_nodes: Iterable[Dict[str, Any]]) -> Iterable[Dict[str, Any]]:
    for node in root_nodes:
        yield node
        for child in iter_nodes_preorder(_node_children(node)):
            yield child


def collect_count_stream(root_nodes: Iterable[Dict[str, Any]]) -> List[int]:
    counts: List[int] = []
    for node in root_nodes:
        counts.append(len(_node_children(node)))
        counts.extend(collect_count_stream(_node_children(node)))
    return counts


def _parse_address(address: str) -> Tuple[List[str], int]:
    if not isinstance(address, str) or not address.strip():
        raise ValueError("Missing msn_id on statonomy node")
    address = address.strip()
    if not ADDRESS_REGEX.match(address):
        raise ValueError(f"Invalid statonomy msn_id: {address}")
    parts = address.split("_")
    return parts, int(parts[-1])


def collect_node_records(root_nodes: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    seen: set[str] = set()
    for node in iter_nodes_preorder(root_nodes):
        address = node.get("msn_id")
        parts, ordinal = _parse_address(address)
        if address in seen:
            raise ValueError(f"Duplicate statonomy msn_id: {address}")
        seen.add(address)
        depth = len(parts)
        parent = "_".join(parts[:-1]) if depth > 1 else None
        child_count = len(_node_children(node))
        records.append({
            "domain": DOMAIN,
            "version": VERSION,
            "msn_id": address,
            "parent_msn_id": parent,
            "depth": depth,
            "ordinal": ordinal,
            "child_count": child_count,
            "leaf": child_count == 0,
        })
    return records


def import_statonomy_samras(
    db_url: str,
    input_path: str = DEFAULT_INPUT_PATH,
) -> Dict[str, Any]:
    data = _load_json(input_path)
    root_nodes = _load_root_nodes(data)
    counts = collect_count_stream(root_nodes)
    count_stream = encode_count_stream(counts)
    records = collect_node_records(root_nodes)

    if not db_url:
        raise RuntimeError("Missing PLATFORM_DB_URL for statonomy import")

    table_name = general_table_name(TABLE_NAME_MSN_ID, TABLE_LOCAL_ID)
    with psycopg2.connect(db_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO platform.samras_layout (domain, version, count_stream, traversal_spec)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (domain, version)
                DO UPDATE SET count_stream = EXCLUDED.count_stream,
                              traversal_spec = EXCLUDED.traversal_spec
                """,
                (DOMAIN, VERSION, count_stream, Json(TRAVERSAL_SPEC)),
            )

            cur.execute(
                "SELECT id FROM platform.samras_archetype WHERE domain = %s",
                (DOMAIN,),
            )
            row = cur.fetchone()
            if row:
                samras_archetype_id = str(row[0])
                cur.execute(
                    """
                    UPDATE platform.samras_archetype
                    SET allowed_modes = %s, description = %s
                    WHERE id = %s
                    """,
                    (
                        ["exact", "group", "existential"],
                        "Canonical statonomy SAMRAS domain shape for msn_id address space",
                        samras_archetype_id,
                    ),
                )
            else:
                samras_archetype_id = str(uuid.uuid4())
                cur.execute(
                    """
                    INSERT INTO platform.samras_archetype
                    (id, domain, allowed_modes, description)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (
                        samras_archetype_id,
                        DOMAIN,
                        ["exact", "group", "existential"],
                        "Canonical statonomy SAMRAS domain shape for msn_id address space",
                    ),
                )

            cur.execute(
                """
                SELECT id FROM platform.archetype
                WHERE tenant_id = %s AND name = %s AND version = %s
                """,
                (TENANT_ID, ARCHETYPE_NAME, VERSION),
            )
            row = cur.fetchone()
            if row:
                archetype_id = str(row[0])
            else:
                archetype_id = str(uuid.uuid4())
                cur.execute(
                    """
                    INSERT INTO platform.archetype (id, tenant_id, name, version)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (archetype_id, TENANT_ID, ARCHETYPE_NAME, VERSION),
                )

            cur.execute(
                "DELETE FROM platform.archetype_field WHERE archetype_id = %s",
                (archetype_id,),
            )
            fields = [
                ("domain", "string", None, {"const": DOMAIN}),
                ("version", "int", None, {"const": VERSION}),
                ("msn_id", "string", None, {"regex": ADDRESS_REGEX.pattern}),
                ("parent_msn_id", "string", None, {"regex": ADDRESS_REGEX.pattern, "nullable": True}),
                ("depth", "int", None, {"min": 1}),
                ("ordinal", "int", None, {"min": 0}),
                ("child_count", "int", None, {"min": 0}),
                ("leaf", "bool", None, None),
            ]
            for position, (name, field_type, ref_domain, constraints) in enumerate(fields, start=1):
                cur.execute(
                    """
                    INSERT INTO platform.archetype_field
                    (archetype_id, position, name, type, ref_domain, constraints)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (
                        archetype_id,
                        position,
                        name,
                        field_type,
                        ref_domain,
                        Json(constraints) if constraints is not None else None,
                    ),
                )

            cur.execute(
                """
                INSERT INTO platform.local_domain (local_id, title)
                VALUES (%s, %s)
                ON CONFLICT (local_id) DO UPDATE SET title = EXCLUDED.title
                """,
                (TABLE_LOCAL_ID, "SAMRAS Statonomy Nodes"),
            )

            cur.execute(
                """
                INSERT INTO platform.manifest (table_id, tenant_id, archetype_id)
                VALUES (%s, %s, %s)
                ON CONFLICT (table_id)
                DO UPDATE SET tenant_id = EXCLUDED.tenant_id,
                              archetype_id = EXCLUDED.archetype_id
                """,
                (TABLE_LOCAL_ID, TENANT_ID, archetype_id),
            )

            cur.execute(
                """
                INSERT INTO platform.general_table
                (tenant_id, table_local_id, mode, table_name, archetype_id, msn_id, enabled)
                VALUES (%s, %s, %s, %s, %s, %s, TRUE)
                ON CONFLICT (tenant_id, table_local_id)
                DO UPDATE SET mode = EXCLUDED.mode,
                              table_name = EXCLUDED.table_name,
                              archetype_id = EXCLUDED.archetype_id,
                              msn_id = EXCLUDED.msn_id,
                              enabled = TRUE,
                              updated_at = now()
                """,
                (TENANT_ID, TABLE_LOCAL_ID, "general", table_name, archetype_id, TABLE_NAME_MSN_ID),
            )

            cur.execute(
                sql.SQL(
                    """
                    CREATE TABLE IF NOT EXISTS {table} (
                        id UUID PRIMARY KEY,
                        created_at TIMESTAMPTZ DEFAULT now(),
                        updated_at TIMESTAMPTZ DEFAULT now(),
                        data JSONB NOT NULL
                    )
                    """
                ).format(table=sql.Identifier(table_name))
            )

            insert_query = sql.SQL(
                """
                INSERT INTO {table} (id, data)
                VALUES (%s, %s)
                ON CONFLICT (id)
                DO UPDATE SET data = EXCLUDED.data, updated_at = now()
                """
            ).format(table=sql.Identifier(table_name))
            for record in records:
                record_id = uuid.uuid5(TABLE_ID_NAMESPACE, f"{DOMAIN}:v{VERSION}:{record['msn_id']}")
                cur.execute(insert_query, (record_id, Json(record)))

    return {
        "node_count": len(records),
        "table_name": table_name,
        "samras_archetype_id": samras_archetype_id,
        "archetype_id": archetype_id,
    }
