# FLASK BFF APLICATION

At this aplications core, there is `main.py`. IT employs two secondary principal files, `webapp/web-app.py` & `portal/portal-app.py`.

There is not meant to be any JSON in Postgres at runtime; demo-data is only a prototype input for ingestion scripts that populate Postgres tables. 
Also another script removes the prior demo-data footprint (beta cleanup) without dropping schemas.

### table naming convention:
There are tables that have the leading `mss.` in their names. These are pertanent to the core mss schema and have an expected structure that is deffined by the schema itsself.

### column naming convention:
Informative sections are seperated by a peroid, `.`, where the first section notates weather it is a system id, `@`, (Aplicable for msn_id, local_id, or other sub-domain namespace ID's like taxonomy: `@.<ID Namespace>.<Namespace Value Type>.<Namespace Max Depth>.<Column Title>`) or a system value, `#` (`#.<Value Class>.<Value Type>.<Max size of Value>.<Column Title>`).
Value Classes are not yet relivant on how they influence anything but they include: nominal, ordinal, natural, and cardinal.
Value types include: Text (`txt`), Initgers (`int`), Mass (`mass`), Time Stamp (`tmstp`), Coordinates (`crds`), Length (`lgth`), and Currency (`fiat`).

## Data, Console, & Portal Aplication Interplay

The portal aplication is provided the entrypoint, as a core organizing file, by `mss.compendium.<msn_id>`, and also providing other context. The form and content to be expeceted are deffined via the MSS schema. Additional expectation are in play for `mss.anthology.<msn_id>`.
Additionally the MSS schema is built to expect 'further standarizations', if any, under the anthology's local node `1_2_0`. Currently there is only the use of one additional standarization, called `platfrom` and as it relates to an additional schmea. This `platfrom` schema and subsequent tables are used to inform how the portal aplication determines the principal facilitating party. In this case, it is my company, and I am noted as the indevidual assigned to the principal user role of my companies benficiary entry. Since my company is noted as the facilitator in the `platform.conspectus.3_2_3_17_77_6_32_1_4`, then the principle user that is identified is considered the keycloak sign in that is the admin.

These should subsequently reveal the other linked `platform.<title>.<msn_id>` files, with distinctions for tenants and facilitators. That distinction is important to portal-app.py. Note that a tenant/facilitator profile is merely the organization benficiary, and it assigns a platform user to hold the role of a keycloak sign in. Currently the portal-app.py should only be built to assume a single `principle_user`, and thus a singe keycloak user id for signing in.
In the future, I may adapt the platform schema to expect to be informed about the console spesifcs, however, for now it only uses two console builds: the admin, and tenant consoles.

The `mss.muniment.<msn_id>` is a data enviorment structure file, however, is semi platform reliant, as it dictates weather a table is accible as an outside resource. This is where a data enviorment deffines soruces of which may be accessed by anyone. So for my data system, it allows for users to refference my msn subdomain namespcae file called `here`. Also identified here are tables in a given `msn_id` namespace that can be acessed via authorized/authenticated API operations.

### MSS standardization + platform interplay
- MSS compendium defines the portal entrypoint and links to its anthology and optional `standardization` chain.
- `platform.conspectus.<msn_id>` is the first platform-standardized link for facilitator context.
- Facilitator selection is read from `@.lcl.txt.4.platform_facilitator_local_id` and resolved via `meta.platform_opus_beneficiary` to a beneficiary record.
- `platform.beneficiary.<msn_id>` binds a beneficiary to a Keycloak user (`#.nominal.txt.36.keycloak_user_id`).

The data schemas, for mss and platform are still under works and will likely change, however, the flask-bff application code must be solid for core modules and functionalities (like website api calls, console CRUD actions, authentication, UI base, admin console base, tenant console base), however I am really just looking to develop a solid application that doesn't get too specific that it impedes my ability to develop later.


## SCHEMA AGNOSTICS

### Portal responsibility boundaries
What is “portal” vs “console” vs “website API”?
What is the canonical entry-point object (“compendium”)?

### Environment & entry points
How compendium files are located / addressed (naming pattern, lookup rules).
How linked platform.* files are discovered from compendium.

### Multi-tenant assumptions
For now: assume a single “principal_user” sign-in path.
Future: multiple users, user hierarchy, delegated roles.

---

## Data Contracts (Schema-Agnostic Interfaces)

Implement these as Python interfaces / service modules with stub methods and clear docstrings. Do NOT bake in table names or columns; add TODOs with “expected fields” placeholders.

### Identity & Access contract (Keycloak + internal mapping)
How data dictates Keycloak user → tenant assignment
How roles map to console visibility

### Portal configuration contract
How compendium/conspectus/garland/florilegium are represented in DB

###Console data contract
How the data informs the UI (module registry, nav, forms)

### Muniment / access tier contract (public vs internal vs immutable)
How muniment affects API exposure & mutability

---

## Flask App Structure (Refactor Plan)

---

## Core Routes to Implement (Stable Skeleton)

---

## LAYOUT
```
aws-box/srv/compose/platform/flask-bff/
├── README.md
├── .dockerignore
├── Dockerfile
├── gunicorn.conf.py
├── requirements.txt
├── main.py
├── auth/
|  ├── authz.py
|  ├── entrypoint.sh
|  └── __init__.py
├── webapp/
|  ├── web-app.py
|  └── __init__.py
└── portal/
   ├── portal-app.py
   ├── UI/
   |  ├── tenant/
   |  └── admin/
   └── services/
```

There are no uses of in-memory state (temporary, per worker). Rather, the configuration exists inside Postgres and is treated it as the authoritative source (dictated by the schema).

The webapp directory is for later development of services that involve api calls, that are verified by the portal apllication.

---

This service is a Flask BFF that resolves portal/console context from Postgres. Runtime reads **no demo JSON**; demo data is **only** ingested into Postgres by scripts.

## Quick Start (Runbook)

### 1) Ingest demo data (idempotent)

From `/srv/compose/platform`:

```
export DATABASE_URL="postgresql://user:pass@host:5432/dbname"
python /srv/compose/platform/flask-bff/scripts/ingest_demo_data.py \
  --data-dir /srv/compose/platform/flask-bff/demo-data
```

Notes:
- Creates/uses `platform.portal_contract_payloads` by default.
- Populates MSS tables (`mss.compendium`, `mss.anthology_entry`, `mss.taxonomy_local_map`, `mss.msn_local_map`, `mss.muniment`) once migrations are applied.
- Re-running is safe: rows for the same `contract_name + source_file + ingest_source` are replaced.
- MSS rows are replaced by `source_msn_id` (destructive replace scoped to the relevant `msn_id`).
 - Apply `/srv/compose/platform/platform-schema/004_mss_compendium_anthology_taxonomy.sql` before MSS ingestion.

### 2) Seed Keycloak users into `platform.mss_profile`

```
export DATABASE_URL="postgresql://user:pass@host:5432/dbname"
python /srv/compose/platform/flask-bff/scripts/seed_mss_profiles.py \
  --data-dir /srv/compose/platform/flask-bff/demo-data
```

### 3) Cleanup demo data (BETA)

```
export DATABASE_URL="postgresql://user:pass@host:5432/dbname"
python /srv/compose/platform/flask-bff/scripts/beta_cleanup_demo_data.py \
  --data-dir /srv/compose/platform/flask-bff/demo-data
```

This removes only rows created by the ingestion script (`ingest_source=demo-data`) and never drops schemas/tables.

### 4) Verify portal is DB-backed

```
export BASE_URL="http://localhost:8000"
export PORTAL_USER_ID="<keycloak-user-uuid>"

curl -sS -H "X-Portal-User: ${PORTAL_USER_ID}" "${BASE_URL}/portal/${MSN_ID}" | jq .
curl -sS -H "X-Portal-User: ${PORTAL_USER_ID}" "${BASE_URL}/portal/${MSN_ID}/module/network" | jq .
```

### 5) Verify login + admin + tenant console

These endpoints depend on your auth plumbing, but you can still smoke-test:

```
curl -sS -H "X-Portal-User: ${PORTAL_USER_ID}" "${BASE_URL}/portal/login" | jq .
curl -sS "${BASE_URL}/admin"
curl -sS "${BASE_URL}/t/${TENANT_ID}/console"
```

### 6) Service health + module data checks

```
curl -sS -o /dev/null -w "%{http_code}\n" "${BASE_URL}/portal/login"
curl -sS -H "X-Portal-User: ${PORTAL_USER_ID}" \
  "${BASE_URL}/portal/${MSN_ID}/module/network" | jq .
```

### 7) Keycloak user provisioning checks

The portal currently uses `contract_name=identity_access` payloads to resolve the Keycloak user mapping.

```
psql "$DATABASE_URL" -c \
  "SELECT source_file, payload FROM platform.portal_contract_payloads WHERE contract_name='identity_access';"
```

Ensure at least one payload contains a value matching the Keycloak `sub`/user UUID you pass in `X-Portal-User`.

## MSS Storage Expectations

MSS runtime data is stored in Postgres. Demo-data is only a source for ingestion and is never read at runtime.

- `mss.compendium`: compendium entrypoints (title, anthology reference, standardization reference).
- `mss.anthology_entry`: anthology local indices (local_id + title).
- `mss.taxonomy_local_map`: taxonomy index for the compendium (`source_msn_id` + taxonomy_id + title).
- `mss.msn_local_map`: msn index for the compendium (`source_msn_id` + msn_id + title).
- `mss.muniment`: muniment rules (`open` vs `conditional`) for resource access.

Muniment enforcement is documented here and will be enforced at runtime in a later step.

## Schema Migrations

MSS schema migrations live in `/srv/compose/platform/platform-schema/`.
Apply `004_mss_compendium_anthology_taxonomy.sql` before running ingestion to populate MSS tables.

## Keycloak + Portal Auth

Portal auth verifies Keycloak JWTs and maps `sub` to `platform.mss_profile`.

- Set `KEYCLOAK_ISSUER` and `KEYCLOAK_AUDIENCE` (or `OIDC_ISSUER` / `OIDC_CLIENT_ID`).
- Ensure `platform.mss_profile.user_id` matches Keycloak `sub`.
- `auth/policy.py` resolves the current user; `portal/portal-app.py` uses this to validate requests.

## Configuration (Postgres)

Runtime configuration is sourced from Postgres. Connection settings:

- `DATABASE_URL` **or** `PGHOST`, `PGPORT`, `PGUSER`, `PGPASSWORD`, `PGDATABASE`
- `PLATFORM_DB_URL` is also accepted by the ingestion scripts and portal runtime.
- Optional: `PORTAL_DB_POOL_MIN`, `PORTAL_DB_POOL_MAX`
- Contract table settings:
  - `PORTAL_CONTRACT_TABLE` (default: `platform.portal_contract_payloads`)
  - `PORTAL_CONTRACT_COLUMN` (default: `contract_name`)
  - `PORTAL_SOURCE_COLUMN` (default: `source_file`)
  - `PORTAL_PAYLOAD_COLUMN` (default: `payload`)
  - `PORTAL_INGEST_COLUMN` (default: `ingest_source`)
  - `PORTAL_INGEST_SOURCE` (default: `demo-data`)

## Demo Data Contracts

Ingestion maps demo files to contract names in `scripts/demo_data_common.py`:

- `portal_configuration`: `platform.conspectus.*`, `mss.anthology.*`, `mss.compendium.*`
- `identity_access`: `platform.beneficiary.*`
- `console_data`: `3_2_3_*`
- `muniment_access`: `mss.*`

These are stored in `platform.portal_contract_payloads` and resolved at runtime by the contract layer.