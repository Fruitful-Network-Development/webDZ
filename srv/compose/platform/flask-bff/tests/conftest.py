import importlib
import os
import sys
from pathlib import Path

import pytest

try:
    import psycopg2
    from psycopg2 import sql
except ModuleNotFoundError:
    psycopg2 = None
    sql = None


APP_DIR = Path(__file__).resolve().parents[1]
SCHEMA_DIR = APP_DIR.parent / "platform-schema"


def _purge_modules():
    for name in list(sys.modules.keys()):
        if (
            name in {"app", "db", "config"}
            or name.startswith("routes")
            or name.startswith("utils")
            or name.startswith("core")
            or name.startswith("adapters")
            or name.startswith("platform")
            or name.startswith("tenant")
            or name.startswith("services")
        ):
            sys.modules.pop(name, None)


def load_app(monkeypatch, db_url=None):
    monkeypatch.setenv("OIDC_ISSUER", "https://issuer.example.com/realms/test")
    monkeypatch.setenv("OIDC_CLIENT_ID", "flask-bff")
    monkeypatch.setenv("OIDC_CLIENT_SECRET", "secret")
    monkeypatch.setenv("SESSION_SECRET", "test-secret")
    monkeypatch.setenv(
        "DATA_ENV_ROOT",
        str(Path(__file__).resolve().parent / "fixtures" / "data_env"),
    )
    if db_url:
        monkeypatch.setenv("PLATFORM_DB_URL", db_url)

    if str(APP_DIR) not in sys.path:
        sys.path.insert(0, str(APP_DIR))

    _purge_modules()
    return importlib.import_module("app")


@pytest.fixture(scope="session")
def db_url():
    url = os.getenv("PLATFORM_DB_URL")
    if not url:
        pytest.skip("PLATFORM_DB_URL is required for integration tests")
    return url


@pytest.fixture(scope="session")
def db_conn(db_url):
    if psycopg2 is None:
        pytest.skip("psycopg2 is required for integration tests")
    conn = psycopg2.connect(db_url)
    conn.autocommit = True
    schema_files = [
        SCHEMA_DIR / "001_init.sql",
        SCHEMA_DIR / "002_mss_init.sql",
        SCHEMA_DIR / "003_mss_profile_msn_id_text.sql",
    ]
    with conn.cursor() as cur:
        for schema_file in schema_files:
            cur.execute(schema_file.read_text(encoding="utf-8"))
    yield conn
    conn.close()


@pytest.fixture()
def db_cleanup(db_conn):
    with db_conn.cursor() as cur:
        cur.execute(
            "TRUNCATE platform.mss_profile, platform.local_domain, platform.archetype, "
            "platform.archetype_field, platform.manifest, platform.samras_layout, "
            "platform.samras_archetype, platform.general_table, platform.local_list, "
            "platform.local_list_member RESTART IDENTITY CASCADE"
        )
    yield


def drop_dynamic_table(conn, table_name):
    if sql is None:
        raise RuntimeError("psycopg2 is required for dropping dynamic tables")
    with conn.cursor() as cur:
        cur.execute(
            sql.SQL("DROP TABLE IF EXISTS {table}").format(
                table=sql.Identifier(table_name)
            )
        )
