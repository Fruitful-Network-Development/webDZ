# Flask BFF (Platform)

This service is a Flask BFF that resolves portal + console context from Postgres.
Runtime reads **no demo JSON**; demo data is **only** ingested into Postgres by scripts.

## App Structure

- `main.py`: Flask app bootstrap (loads portal + webapp blueprints).
- `portal/portal-app.py`: portal + console routes.
- `webapp/web-app.py`: public webapp APIs.
- `portal/portal_store.py`: DB access layer (MSS + contract payloads).

## Runtime Data Sources

Authoritative tables:
- `platform.portal_contract_payloads`
- `platform.correspondence`
- `mss.compendium`
- `mss.anthology_entry`
- `mss.taxonomy_local_map`
- `mss.msn_local_map`
- `mss.muniment`

## Quick Start (Runbook)

### 1) Apply migrations

```
docker compose exec -T platform_db psql -U platform -d platform < /srv/compose/platform/platform-schema/004_mss_compendium_anthology_taxonomy.sql
docker compose exec -T platform_db psql -U platform -d platform < /srv/compose/platform/platform-schema/006_platform_correspondence.sql
```

### 2) Ingest demo data (idempotent)

```
export DATABASE_URL="postgresql://user:pass@host:5432/dbname"
python /srv/compose/platform/flask-bff/scripts/ingest_demo_data.py \
  --data-dir /srv/compose/platform/flask-bff/demo-data
```

Notes:
- Creates/uses `platform.portal_contract_payloads` by default.
- Populates MSS tables and `platform.correspondence`.
- Re-running is safe (rows are replaced per source file).

### 3) Cleanup demo data (BETA)

```
export DATABASE_URL="postgresql://user:pass@host:5432/dbname"
python /srv/compose/platform/flask-bff/scripts/beta_cleanup_demo_data.py \
  --data-dir /srv/compose/platform/flask-bff/demo-data
```

### 4) Verify portal is DB-backed

```
export BASE_URL="http://localhost:8000"
export PORTAL_USER_ID="<keycloak-user-uuid>"

curl -sS -H "X-Portal-User: ${PORTAL_USER_ID}" "${BASE_URL}/portal/${MSN_ID}" | jq .
curl -sS -H "X-Portal-User: ${PORTAL_USER_ID}" "${BASE_URL}/portal/${MSN_ID}/module/network" | jq .
```

## Admin Console (Email Module)

Admin console routes:
- `/admin` (overview)
- `/admin/tenants` (tenant tables)
- `/admin/registry` (facilitator + muniment registry)
- `/admin/email` (correspondence records)

Admin API endpoints:
- `GET /api/admin/correspondence`
- `POST /api/admin/correspondence`
- `PUT /api/admin/correspondence/<id>`
- `DELETE /api/admin/correspondence/<id>`

Public newsletter stubs (muniment-gated):
- `POST /api/newsletter/subscribe`
- `POST /api/newsletter/unsubscribe`

## Keycloak + Portal Auth

Portal auth verifies Keycloak JWTs and maps `sub` to `identity_access` payloads
stored in `platform.portal_contract_payloads`.

- Set `KEYCLOAK_ISSUER` and `KEYCLOAK_AUDIENCE` (or `OIDC_ISSUER` / `OIDC_CLIENT_ID`).
- Ensure `platform.beneficiary.*` payloads contain the Keycloak `sub` value.

## Configuration (Postgres)

- `DATABASE_URL` **or** `PGHOST`, `PGPORT`, `PGUSER`, `PGPASSWORD`, `PGDATABASE`
- `PLATFORM_DB_URL` is also accepted by ingestion scripts and portal runtime.
- Optional: `PORTAL_DB_POOL_MIN`, `PORTAL_DB_POOL_MAX`
- Contract table settings:
  - `PORTAL_CONTRACT_TABLE` (default: `platform.portal_contract_payloads`)
  - `PORTAL_CONTRACT_COLUMN` (default: `contract_name`)
  - `PORTAL_SOURCE_COLUMN` (default: `source_file`)
  - `PORTAL_PAYLOAD_COLUMN` (default: `payload`)
  - `PORTAL_INGEST_COLUMN` (default: `ingest_source`)
  - `PORTAL_INGEST_SOURCE` (default: `demo-data`)
