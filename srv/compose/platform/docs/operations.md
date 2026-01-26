# Operations

## Runbook

### Rebuild/restart services

```
cd /srv/compose/platform
docker compose up -d --force-recreate --build flask_bff
```

### Apply migrations (001/002/003) to platform_db

`002_mss_init.sql` is authoritative for MSS schema (including
`mss_profile.msn_id` as TEXT). `003_mss_profile_msn_id_text.sql` is a safety
guard for existing DBs; keep it in the runbook to avoid drift.

```
cd /srv/compose/platform
cat platform-schema/001_init.sql | docker exec -i platform_db psql -U platform -d platform
cat platform-schema/002_mss_init.sql | docker exec -i platform_db psql -U platform -d platform
cat platform-schema/003_mss_profile_msn_id_text.sql | docker exec -i platform_db psql -U platform -d platform
```

### Provision root admin (MSS profile)

```
cd /srv/compose/platform
USER_ID="<keycloak-user-uuid>" MSN_ID="<samras-text-id>" ./scripts/provision_root_admin.sh
```

### Login URL pattern

```
https://api.fruitfulnetworkdevelopment.com/login?tenant=<tenant_id>&return_to=<path>
```

Working example:

```
https://api.fruitfulnetworkdevelopment.com/login?tenant=platform&return_to=/admin
```

## Phase 5 admin console expectations

Canonical UI paths:

- `/` (landing, redirects to `/admin` for root admins)
- `/admin`
- `/admin/tenants` and `/admin/tenants/<tenant_id>`
- `/admin/local-domains`
- `/admin/archetypes`
- `/admin/manifest`
- `/admin/samras-layouts`
- `/admin/users`
- `/admin/services`
- `/admin/tables` and `/admin/lists`
- `/t/<tenant_id>/console`

Alias redirects:

- `/admin/overview` → `/admin`
- `/admin/tenant/<tenant_id>` → `/admin/tenants/<tenant_id>`
- `/admin/local-domain` → `/admin/local-domains`
- `/admin/samras` → `/admin/samras-layouts`

Auth behavior:

- HTML routes redirect to `/login?tenant=platform&return_to=<path>` when unauthenticated.
- JSON API routes return `401` with `{ "error": "not_authenticated" }`.
- Unauthorized or not provisioned returns `403` with a consistent message.

Troubleshooting:

- `401 not_authenticated`: session missing or expired → sign in again.
- `403 forbidden`: authenticated but missing admin/tenant role.
- `403 not_provisioned`: authenticated but missing MSS profile.
- `409`: provisioning conflicts (missing manifest/local domain, already provisioned).

## Expected success criteria

- `GET http://127.0.0.1:8001/health` returns `200`
- `GET http://127.0.0.1:8001/login?tenant=platform&return_to=/admin` returns `302`
- After login in browser:
  - `/admin` loads (200)
  - `/t/platform/console` loads (200)
  - `/t/platform/console/animals` loads (200)

## MSS profile design note

`platform.mss_profile.msn_id` (and `parent_msn_id`) are **TEXT** by design
(SAMRAS-style IDs), not UUID.

## Keycloak realm exports

See `keycloak/realm/README.md` for export/import guidance.
