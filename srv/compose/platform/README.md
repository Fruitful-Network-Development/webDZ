# Platform Environment Overview

This repository hosts the Dockerized platform stack (Keycloak, Postgres, Flask BFF).
Runtime state is stored in Postgres; demo JSON is only a prototype input for ingestion scripts.

## Current Data Reality (No Legacy Drift)

Authoritative runtime tables:
- `platform.portal_contract_payloads`
- `platform.correspondence`
- `mss.compendium`
- `mss.anthology_entry`
- `mss.taxonomy_local_map`
- `mss.msn_local_map`
- `mss.muniment`

Legacy tables have been **removed** and should not be referenced in code or schema:
- `platform.user_profiles`, `platform.audit_log`
- `platform.mss_profile`, `platform.local_domain`
- `platform.archetype`, `platform.archetype_field`, `platform.manifest`
- `platform.general_table`, `platform.local_list`, `platform.local_list_member`
- `platform.samras_layout`, `platform.samras_archetype`

## Naming Conventions

- Tables with `mss.` are part of the core MSS schema.
- Column naming conventions use `@` for system IDs and `#` for system values:
  - `@.<namespace>.<type>.<depth>.<title>`
  - `#.<class>.<type>.<size>.<title>`

## MSS Standardization + Platform Interplay

- `mss.compendium.<msn_id>` defines the portal entrypoint and links to:
  - `mss.anthology.<msn_id>`
  - optional `standardization` chain (e.g. `platform.conspectus.<msn_id>`)
- `platform.conspectus.<msn_id>` identifies the facilitator:
  - `@.lcl.txt.4.platform_facilitator_local_id`
  - resolved via `meta.platform_opus_beneficiary`
- `platform.beneficiary.<msn_id>` binds a beneficiary to a Keycloak user:
  - `#.nominal.txt.36.keycloak_user_id`
- `platform.correspondence.<msn_id>` stores email domain management references
  (SES, Route53, IAM/Lambda ARNs) and is surfaced in the admin email module.

## Keycloak + Portal Auth

Portal auth verifies Keycloak JWTs and maps `sub` to `identity_access` payloads
stored in `platform.portal_contract_payloads`.

- `OIDC_ISSUER` / `OIDC_CLIENT_ID` (or `KEYCLOAK_ISSUER` / `KEYCLOAK_AUDIENCE`)
- Ensure `platform.beneficiary.*` payloads contain the Keycloak `sub` value.
- `auth/policy.py` resolves the current user; `portal/portal-app.py` validates requests.

### Keycloak User Provisioning (Runbook)

Run these inside the Keycloak container. Authenticate first, then create users
in the `fruitful` realm and set passwords.

```
docker exec -it keycloak /opt/keycloak/bin/kcadm.sh config credentials \
  --server http://localhost:8080 \
  --realm fruitful \
  --user fruitful-admin \
  --password '<PASSWORD>'

docker exec -it keycloak /opt/keycloak/bin/kcadm.sh create users -r fruitful \
  -s username=fruitful-tennant-cvcc_ppoc -s enabled=true

docker exec -it keycloak /opt/keycloak/bin/kcadm.sh create users -r fruitful \
  -s username=fruitful-tennant-tff_ppoc -s enabled=true

docker exec -it keycloak /opt/keycloak/bin/kcadm.sh set-password -r fruitful \
  --username fruitful-tennant-cvcc_ppoc --new-password '<PASSWORD>' --temporary

docker exec -it keycloak /opt/keycloak/bin/kcadm.sh set-password -r fruitful \
  --username fruitful-tennant-tff_ppoc --new-password '<PASSWORD>' --temporary
```

## Schema Migrations

Migrations live in `/srv/compose/platform/platform-schema/`:
- `001_init.sql`: create `platform` schema only.
- `002_mss_init.sql`: legacy placeholder (no-op).
- `004_mss_compendium_anthology_taxonomy.sql`: MSS runtime tables.
- `005_drop_legacy_platform_tables.sql`: remove legacy platform tables.
- `006_platform_correspondence.sql`: correspondence records for email management.

Apply in order:
```
docker compose exec -T platform_db psql -U platform -d platform < platform-schema/001_init.sql
docker compose exec -T platform_db psql -U platform -d platform < platform-schema/002_mss_init.sql
docker compose exec -T platform_db psql -U platform -d platform < platform-schema/004_mss_compendium_anthology_taxonomy.sql
docker compose exec -T platform_db psql -U platform -d platform < platform-schema/005_drop_legacy_platform_tables.sql
docker compose exec -T platform_db psql -U platform -d platform < platform-schema/006_platform_correspondence.sql
```

## Demo Data Ingestion + Cleanup

Ingestion creates/uses `platform.portal_contract_payloads` and populates MSS tables.

```
export DATABASE_URL="postgresql://user:pass@host:5432/dbname"
python /srv/compose/platform/flask-bff/scripts/ingest_demo_data.py \
  --data-dir /srv/compose/platform/flask-bff/demo-data
```

Cleanup removes ingested rows only:
```
export DATABASE_URL="postgresql://user:pass@host:5432/dbname"
python /srv/compose/platform/flask-bff/scripts/beta_cleanup_demo_data.py \
  --data-dir /srv/compose/platform/flask-bff/demo-data
```

## Console Development Guidance

Admin and tenant consoles should only read from MSS tables and contract payloads:
- **Entry point**: `mss.compendium`
- **Navigation tree**: `mss.anthology_entry`
- **Cross-namespace links**: `mss.taxonomy_local_map`, `mss.msn_local_map`
- **Access rules**: `mss.muniment`
- **Platform linkage**: `platform.conspectus` + `platform.beneficiary` payloads via
  `platform.portal_contract_payloads`
- **Email module**: `platform.correspondence` (admin-only CRUD + SES/Route53 references)

Do not introduce new runtime dependencies on legacy `platform.*` tables.
