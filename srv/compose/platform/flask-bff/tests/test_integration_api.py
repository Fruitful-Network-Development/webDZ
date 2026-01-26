import base64
import uuid

import pytest

from conftest import drop_dynamic_table, load_app


def _seed_admin_workflow(db_conn, tenant_id: str):
    local_id = str(uuid.uuid4())
    archetype_id = str(uuid.uuid4())
    root_user_id = str(uuid.uuid4())
    root_msn_id = f"ROOT-{uuid.uuid4()}"

    with db_conn.cursor() as cur:
        cur.execute(
            "INSERT INTO platform.mss_profile (msn_id, user_id, display_name, role) VALUES (%s, %s, %s, %s)",
            (root_msn_id, root_user_id, "Root Admin", "root-admin"),
        )
        cur.execute(
            "INSERT INTO platform.local_domain (local_id, title) VALUES (%s, %s)",
            (local_id, "Companion Animals"),
        )
        cur.execute(
            "INSERT INTO platform.archetype (id, tenant_id, name, version) VALUES (%s, %s, %s, %s)",
            (archetype_id, tenant_id, "companion_animals", 1),
        )
        cur.execute(
            """
            INSERT INTO platform.archetype_field
            (archetype_id, position, name, type, ref_domain, constraints)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (archetype_id, 1, "name", "string", None, None),
        )
        cur.execute(
            "INSERT INTO platform.manifest (table_id, tenant_id, archetype_id) VALUES (%s, %s, %s)",
            (local_id, tenant_id, archetype_id),
        )

    return {
        "tenant_id": tenant_id,
        "local_id": local_id,
        "archetype_id": archetype_id,
        "root_user_id": root_user_id,
        "root_msn_id": root_msn_id,
    }


def _seed_network_workflow(db_conn, tenant_id: str):
    table_local_id = str(uuid.uuid4())
    archetype_id = str(uuid.uuid4())
    root_user_id = str(uuid.uuid4())
    root_msn_id = f"ROOT-{uuid.uuid4()}"

    with db_conn.cursor() as cur:
        cur.execute(
            "INSERT INTO platform.mss_profile (msn_id, user_id, display_name, role) VALUES (%s, %s, %s, %s)",
            (root_msn_id, root_user_id, "Root Admin", "root-admin"),
        )
        cur.execute(
            "INSERT INTO platform.local_domain (local_id, title) VALUES (%s, %s)",
            (table_local_id, "Participant Farms"),
        )
        cur.execute(
            "INSERT INTO platform.archetype (id, tenant_id, name, version) VALUES (%s, %s, %s, %s)",
            (archetype_id, tenant_id, "participant_farms", 1),
        )
        fields = [
            (1, "msn_id", "string"),
            (2, "local_id", "string"),
            (3, "logo", "string"),
            (4, "images", "array"),
            (5, "bio", "string"),
            (6, "sources", "array"),
        ]
        for position, name, field_type in fields:
            cur.execute(
                """
                INSERT INTO platform.archetype_field
                (archetype_id, position, name, type, ref_domain, constraints)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (archetype_id, position, name, field_type, None, None),
            )
        cur.execute(
            "INSERT INTO platform.manifest (table_id, tenant_id, archetype_id) VALUES (%s, %s, %s)",
            (table_local_id, tenant_id, archetype_id),
        )

    return {
        "tenant_id": tenant_id,
        "table_local_id": table_local_id,
        "archetype_id": archetype_id,
        "root_user_id": root_user_id,
        "root_msn_id": root_msn_id,
    }


@pytest.mark.usefixtures("db_cleanup")
def test_schema_registry_endpoints(monkeypatch, db_conn, db_url):
    app_module = load_app(monkeypatch, db_url=db_url)
    app_module.app.config.update(TESTING=True)

    with app_module.app.test_client() as client:
        with client.session_transaction() as sess:
            sess["user"] = {
                "user_id": str(uuid.uuid4()),
                "realm_roles": ["root_admin"],
            }

        local_id = str(uuid.uuid4())
        resp = client.post("/api/admin/local-domain", json={
            "local_id": local_id,
            "title": "Companion Animals",
        })
        assert resp.status_code == 201

        count_stream = base64.b64encode(bytes([2, 2])).decode("utf-8")
        resp = client.post("/api/admin/samras-layouts", json={
            "domain": "animals",
            "version": 1,
            "count_stream": count_stream,
            "traversal_spec": {"nodes": {"0.1": {"label": "Canine"}}},
        })
        assert resp.status_code == 201

        tenant_id = "cuyahogaterravita"
        resp = client.post("/api/admin/archetypes", json={
            "tenant_id": tenant_id,
            "name": "companion_animals",
            "fields": [
                {"position": 1, "name": "name", "type": "string"},
                {
                    "position": 2,
                    "name": "taxa_ref",
                    "type": "string",
                    "ref_domain": "SAMRAS:animals/1",
                    "constraints": {"samras_mode": "exact"},
                },
            ],
        })
        assert resp.status_code == 201
        archetype_id = resp.get_json()["id"]

        resp = client.post("/api/admin/manifest", json={
            "tenant_id": tenant_id,
            "table_id": local_id,
            "archetype_id": archetype_id,
        })
        assert resp.status_code == 201

        resp = client.get("/api/admin/local-domain")
        assert resp.status_code == 200
        assert any(row["local_id"] == local_id for row in resp.get_json()["local_domains"])

        resp = client.get("/api/admin/archetypes", query_string={"tenant_id": tenant_id})
        assert resp.status_code == 200
        assert any(row["id"] == archetype_id for row in resp.get_json()["archetypes"])

        resp = client.get("/api/admin/manifest", query_string={"tenant_id": tenant_id})
        assert resp.status_code == 200
        assert any(row["table_id"] == local_id for row in resp.get_json()["manifest"])

        resp = client.get("/api/admin/samras-layouts")
        assert resp.status_code == 200
        assert any(row["domain"] == "animals" for row in resp.get_json()["samras_layouts"])


@pytest.mark.usefixtures("db_cleanup")
def test_admin_general_table_create(monkeypatch, db_conn, db_url):
    app_module = load_app(monkeypatch, db_url=db_url)
    app_module.app.config.update(TESTING=True)

    tenant_id = "tenant-test"
    local_id = str(uuid.uuid4())
    archetype_id = str(uuid.uuid4())
    root_user_id = str(uuid.uuid4())
    root_msn_id = "ROOT-ADMIN-001"

    with db_conn.cursor() as cur:
        cur.execute(
            "INSERT INTO platform.mss_profile (msn_id, user_id, display_name, role) VALUES (%s, %s, %s, %s)",
            (root_msn_id, root_user_id, "Root Admin", "root-admin"),
        )
        cur.execute(
            "INSERT INTO platform.local_domain (local_id, title) VALUES (%s, %s)",
            (local_id, "Companion Animals"),
        )
        cur.execute(
            "INSERT INTO platform.archetype (id, tenant_id, name, version) VALUES (%s, %s, %s, %s)",
            (archetype_id, tenant_id, "companion_animals", 1),
        )
        cur.execute(
            """
            INSERT INTO platform.archetype_field
            (archetype_id, position, name, type, ref_domain, constraints)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (archetype_id, 1, "name", "string", None, None),
        )
        cur.execute(
            "INSERT INTO platform.manifest (table_id, tenant_id, archetype_id) VALUES (%s, %s, %s)",
            (local_id, tenant_id, archetype_id),
        )

    with app_module.app.test_client() as client:
        with client.session_transaction() as sess:
            sess["user"] = {
                "user_id": root_user_id,
                "realm_roles": ["root_admin"],
            }

        create_resp = client.post(
            "/api/admin/tables",
            json={
                "tenant_id": tenant_id,
                "table_local_id": local_id,
                "mode": "general",
            },
        )
        assert create_resp.status_code == 201
        payload = create_resp.get_json()
        assert payload["table_name"]
        assert payload["archetype_id"] == archetype_id

    drop_dynamic_table(db_conn, payload["table_name"])


@pytest.mark.usefixtures("db_cleanup")
def test_network_records_list(monkeypatch, db_conn, db_url):
    app_module = load_app(monkeypatch, db_url=db_url)
    app_module.app.config.update(TESTING=True)

    seeded = _seed_network_workflow(db_conn, "tenant-network")

    with app_module.app.test_client() as client:
        with client.session_transaction() as sess:
            sess["user"] = {
                "user_id": seeded["root_user_id"],
                "realm_roles": ["root_admin"],
            }
        provision_resp = client.post(
            "/api/admin/tables",
            json={
                "tenant_id": seeded["tenant_id"],
                "table_local_id": seeded["table_local_id"],
                "mode": "general",
            },
        )
        assert provision_resp.status_code == 201
        table_name = provision_resp.get_json()["table_name"]

    record_one = {
        "msn_id": "SAMRAS:cvcc/participant_farms/001",
        "local_id": str(uuid.uuid4()),
        "logo": "heritage-hollow.png",
        "images": ["heritage-hollow-1.jpg", "heritage-hollow-2.jpg"],
        "bio": "Heritage Hollow Farm raises pasture poultry and grows heirloom produce.",
        "sources": ["https://example.com/heritage-hollow"],
    }
    record_two = {
        "msn_id": "SAMRAS:cvcc/participant_farms/002",
        "local_id": str(uuid.uuid4()),
        "logo": "riverbend-acres.png",
        "images": ["riverbend-1.jpg"],
        "bio": "Riverbend Acres focuses on regenerative grazing and community CSA programs.",
        "sources": ["https://example.com/riverbend", "https://example.com/riverbend/story"],
    }

    with app_module.app.test_client() as client:
        with client.session_transaction() as sess:
            sess["user"] = {
                "user_id": seeded["root_user_id"],
                "msn_id": seeded["root_msn_id"],
                "realm_roles": ["root_admin"],
            }

        create_one = client.post(
            f"/api/t/{seeded['tenant_id']}/tables/{seeded['table_local_id']}",
            json=record_one,
        )
        assert create_one.status_code == 201

        create_two = client.post(
            f"/api/t/{seeded['tenant_id']}/tables/{seeded['table_local_id']}",
            json=record_two,
        )
        assert create_two.status_code == 201

        list_resp = client.get(
            f"/api/t/{seeded['tenant_id']}/tables/{seeded['table_local_id']}"
        )
        assert list_resp.status_code == 200
        records = list_resp.get_json()["records"]
        local_ids = {row["data"]["local_id"] for row in records}
        assert record_one["local_id"] in local_ids
        assert record_two["local_id"] in local_ids

    drop_dynamic_table(db_conn, table_name)


@pytest.mark.usefixtures("db_cleanup")
def test_admin_workflow_provision(monkeypatch, db_conn, db_url):
    app_module = load_app(monkeypatch, db_url=db_url)
    app_module.app.config.update(TESTING=True)

    seeded = _seed_admin_workflow(db_conn, "tenant-workflow")

    with app_module.app.test_client() as client:
        with client.session_transaction() as sess:
            sess["user"] = {
                "user_id": seeded["root_user_id"],
                "realm_roles": ["root_admin"],
            }

        resp = client.post(
            "/api/admin/tables",
            json={
                "tenant_id": seeded["tenant_id"],
                "table_local_id": seeded["local_id"],
                "mode": "general",
            },
        )
        assert resp.status_code == 201
        payload = resp.get_json()
        assert payload["table_name"]
        assert payload["archetype_id"] == seeded["archetype_id"]

        second_resp = client.post(
            "/api/admin/tables",
            json={
                "tenant_id": seeded["tenant_id"],
                "table_local_id": seeded["local_id"],
                "mode": "general",
            },
        )
        assert second_resp.status_code == 200
        assert second_resp.get_json()["status"] == "already_provisioned"

    drop_dynamic_table(db_conn, payload["table_name"])


@pytest.mark.usefixtures("db_cleanup")
def test_root_admin_record_round_trip(monkeypatch, db_conn, db_url):
    app_module = load_app(monkeypatch, db_url=db_url)
    app_module.app.config.update(TESTING=True)

    seeded = _seed_admin_workflow(db_conn, "tenant-records")

    with app_module.app.test_client() as client:
        with client.session_transaction() as sess:
            sess["user"] = {
                "user_id": seeded["root_user_id"],
                "realm_roles": ["root_admin"],
            }
        provision_resp = client.post(
            "/api/admin/tables",
            json={
                "tenant_id": seeded["tenant_id"],
                "table_local_id": seeded["local_id"],
                "mode": "general",
            },
        )
        assert provision_resp.status_code == 201
        table_name = provision_resp.get_json()["table_name"]

    with app_module.app.test_client() as client:
        with client.session_transaction() as sess:
            sess["user"] = {
                "user_id": seeded["root_user_id"],
                "msn_id": seeded["root_msn_id"],
                "realm_roles": ["root_admin"],
            }

        create_resp = client.post(
            f"/api/t/{seeded['tenant_id']}/tables/{seeded['local_id']}",
            json={"name": "Luna"},
        )
        assert create_resp.status_code == 201
        record_id = create_resp.get_json()["record"]["record_id"]

        list_resp = client.get(
            f"/api/t/{seeded['tenant_id']}/tables/{seeded['local_id']}"
        )
        assert list_resp.status_code == 200
        assert any(row["record_id"] == record_id for row in list_resp.get_json()["records"])

        fetch_resp = client.get(
            f"/api/t/{seeded['tenant_id']}/tables/{seeded['local_id']}/{record_id}"
        )
        assert fetch_resp.status_code == 200
        assert fetch_resp.get_json()["record"]["data"]["name"] == "Luna"

    drop_dynamic_table(db_conn, table_name)


@pytest.mark.usefixtures("db_cleanup")
def test_admin_list_resolution_workflow(monkeypatch, db_conn, db_url):
    app_module = load_app(monkeypatch, db_url=db_url)
    app_module.app.config.update(TESTING=True)

    tenant_id = "tenant-lists"
    list_local_id = str(uuid.uuid4())
    member_one = str(uuid.uuid4())
    member_two = str(uuid.uuid4())

    with db_conn.cursor() as cur:
        cur.execute(
            "INSERT INTO platform.local_domain (local_id, title) VALUES (%s, %s)",
            (member_one, "Canine"),
        )
        cur.execute(
            "INSERT INTO platform.local_domain (local_id, title) VALUES (%s, %s)",
            (member_two, "Feline"),
        )

    with app_module.app.test_client() as client:
        with client.session_transaction() as sess:
            sess["user"] = {
                "user_id": str(uuid.uuid4()),
                "realm_roles": ["root_admin"],
            }

        create_resp = client.post(
            "/api/admin/lists",
            json={
                "tenant_id": tenant_id,
                "list_local_id": list_local_id,
                "members": [member_one, member_two],
                "name": "Pets",
            },
        )
        assert create_resp.status_code == 201

        get_resp = client.get(f"/api/admin/lists/{list_local_id}")
        assert get_resp.status_code == 200
        members = get_resp.get_json()["list"]["members"]
        assert members[0]["title"] == "Canine"
        assert members[1]["title"] == "Feline"


@pytest.mark.usefixtures("db_cleanup")
def test_table_crud_and_samras_validation(monkeypatch, db_conn, db_url):
    app_module = load_app(monkeypatch, db_url=db_url)
    app_module.app.config.update(TESTING=True)

    tenant_id = "tenant-test"
    local_id = str(uuid.uuid4())
    archetype_id = str(uuid.uuid4())
    root_user_id = str(uuid.uuid4())
    root_msn_id = "ROOT-ADMIN-002"
    tenant_user_id = str(uuid.uuid4())
    tenant_msn_id = "TENANT-ADMIN-001"

    with db_conn.cursor() as cur:
        cur.execute(
            "INSERT INTO platform.mss_profile (msn_id, user_id, display_name, role) VALUES (%s, %s, %s, %s)",
            (root_msn_id, root_user_id, "Root Admin", "root-admin"),
        )
        cur.execute(
            "INSERT INTO platform.mss_profile (msn_id, user_id, display_name, role) VALUES (%s, %s, %s, %s)",
            (tenant_msn_id, tenant_user_id, "Tenant Admin", "admin"),
        )
        cur.execute(
            "INSERT INTO platform.local_domain (local_id, title) VALUES (%s, %s)",
            (local_id, "Companion Animals"),
        )
        cur.execute(
            "INSERT INTO platform.archetype (id, tenant_id, name, version) VALUES (%s, %s, %s, %s)",
            (archetype_id, tenant_id, "companion_animals", 1),
        )
        cur.execute(
            """
            INSERT INTO platform.archetype_field
            (archetype_id, position, name, type, ref_domain, constraints)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (archetype_id, 1, "name", "string", None, None),
        )
        cur.execute(
            """
            INSERT INTO platform.archetype_field
            (archetype_id, position, name, type, ref_domain, constraints)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (archetype_id, 2, "taxa_ref", "string", "SAMRAS:animals/1", '{"samras_mode": "exact"}'),
        )
        cur.execute(
            "INSERT INTO platform.manifest (table_id, tenant_id, archetype_id) VALUES (%s, %s, %s)",
            (local_id, tenant_id, archetype_id),
        )
        cur.execute(
            "INSERT INTO platform.samras_layout (domain, version, count_stream, traversal_spec) VALUES (%s, %s, %s, %s)",
            ("animals", 1, bytes([2, 2]), '{"nodes": {"0.1": {"label": "Canine"}}}'),
        )

    with app_module.app.test_client() as client:
        with client.session_transaction() as sess:
            sess["user"] = {
                "user_id": root_user_id,
                "realm_roles": ["root_admin"],
            }
        create_resp = client.post(
            "/api/admin/tables",
            json={
                "tenant_id": tenant_id,
                "table_local_id": local_id,
                "mode": "general",
            },
        )
        assert create_resp.status_code == 201
        table_name = create_resp.get_json()["table_name"]

    with app_module.app.test_client() as client:
        with client.session_transaction() as sess:
            sess["user"] = {
                "user_id": tenant_user_id,
                "msn_id": tenant_msn_id,
                "realm_roles": [f"tenant_admin:{tenant_id}"],
            }

        invalid_resp = client.post(
            f"/api/t/{tenant_id}/tables/{local_id}",
            json={"name": "Luna", "taxa_ref": {"system_value": "0.1"}},
        )
        assert invalid_resp.status_code == 400
        assert invalid_resp.get_json()["reason"] == "missing_system_id"

        create_resp = client.post(
            f"/api/t/{tenant_id}/tables/{local_id}",
            json={"name": "Luna", "taxa_ref": {"system_id": "0.1"}},
        )
        assert create_resp.status_code == 201
        record = create_resp.get_json()["record"]
        record_id = record["record_id"]
        assert record["data"]["name"] == "Luna"

        list_resp = client.get(f"/api/t/{tenant_id}/tables/{local_id}")
        assert list_resp.status_code == 200
        assert any(row["record_id"] == record_id for row in list_resp.get_json()["records"])

        fetch_resp = client.get(f"/api/t/{tenant_id}/tables/{local_id}/{record_id}")
        assert fetch_resp.status_code == 200
        assert fetch_resp.get_json()["record"]["data"]["name"] == "Luna"

        update_resp = client.put(
            f"/api/t/{tenant_id}/tables/{local_id}/{record_id}",
            json={"name": "Nova", "taxa_ref": {"system_id": "0.1"}},
        )
        assert update_resp.status_code == 200
        assert update_resp.get_json()["record"]["data"]["name"] == "Nova"

        delete_resp = client.delete(
            f"/api/t/{tenant_id}/tables/{local_id}/{record_id}"
        )
        assert delete_resp.status_code == 200

        missing_resp = client.get(f"/api/t/{tenant_id}/tables/{local_id}/{record_id}")
        assert missing_resp.status_code == 404

    drop_dynamic_table(db_conn, table_name)


@pytest.mark.usefixtures("db_cleanup")
def test_list_resolution(monkeypatch, db_conn, db_url):
    app_module = load_app(monkeypatch, db_url=db_url)
    app_module.app.config.update(TESTING=True)

    tenant_id = "tenant-test"
    list_local_id = str(uuid.uuid4())
    member_one = str(uuid.uuid4())
    member_two = str(uuid.uuid4())

    with db_conn.cursor() as cur:
        cur.execute(
            "INSERT INTO platform.local_domain (local_id, title) VALUES (%s, %s)",
            (member_one, "Canine"),
        )
        cur.execute(
            "INSERT INTO platform.local_domain (local_id, title) VALUES (%s, %s)",
            (member_two, "Feline"),
        )

    with app_module.app.test_client() as client:
        with client.session_transaction() as sess:
            sess["user"] = {
                "user_id": str(uuid.uuid4()),
                "realm_roles": ["root_admin"],
            }

        create_resp = client.post(
            "/api/admin/lists",
            json={
                "tenant_id": tenant_id,
                "list_local_id": list_local_id,
                "members": [member_one, member_two],
                "name": "Pets",
            },
        )
        assert create_resp.status_code == 201

        get_resp = client.get(f"/api/admin/lists/{list_local_id}")
        assert get_resp.status_code == 200
        members = get_resp.get_json()["list"]["members"]
        assert members[0]["title"] == "Canine"
        assert members[1]["title"] == "Feline"


@pytest.mark.usefixtures("db_cleanup")
def test_user_hierarchy_crud(monkeypatch, db_conn, db_url):
    app_module = load_app(monkeypatch, db_url=db_url)
    app_module.app.config.update(TESTING=True)

    user_id = str(uuid.uuid4())

    with app_module.app.test_client() as client:
        with client.session_transaction() as sess:
            sess["user"] = {
                "user_id": str(uuid.uuid4()),
                "realm_roles": ["root_admin"],
            }

        create_resp = client.post(
            "/api/admin/user-hierarchy",
            json={
                "user_id": user_id,
                "display_name": "Test User",
                "role": "member",
            },
        )
        assert create_resp.status_code == 201
        profile = create_resp.get_json()["profile"]
        msn_id = profile["msn_id"]

        lookup_resp = client.get("/api/admin/user-hierarchy", query_string={"user_id": user_id})
        assert lookup_resp.status_code == 200
        assert lookup_resp.get_json()["profile"]["msn_id"] == msn_id

        list_resp = client.get("/api/admin/user-hierarchy")
        assert list_resp.status_code == 200
        assert any(row["msn_id"] == msn_id for row in list_resp.get_json()["profiles"])

        update_resp = client.put(
            "/api/admin/user-hierarchy",
            json={"msn_id": msn_id, "display_name": "Updated", "role": "admin"},
        )
        assert update_resp.status_code == 200
        assert update_resp.get_json()["profile"]["display_name"] == "Updated"

        delete_resp = client.delete(
            "/api/admin/user-hierarchy",
            json={"msn_id": msn_id},
        )
        assert delete_resp.status_code == 200
