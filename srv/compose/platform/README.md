# /srv/compose/platform

## Auth & BFF stack

This stack introduces authentication and a backend-for-frontend (BFF) layer
while keeping the host’s static sites unchanged.

## Purpose

Describe the services in the Auth/BFF stack, how they relate, and what they
expose.

## Services

- **Keycloak (IdP)**: handles authentication, sessions, and identity flows.
- **Postgres (Keycloak-only)**: persistence for Keycloak state.
- **Flask BFF**: handles login/logout flows and issues secure session cookies.

## Public interfaces

- `auth.<domain>` → Keycloak (pure proxy vhost).
- `api.<domain>` → Flask BFF (pure proxy vhost).
- Primary client domains remain static, with optional proxy routes for auth UI.

## Trust boundaries

- NGINX is the only public ingress.
- Containers bind to localhost; NGINX proxies to them explicitly.
- Static sites never store tokens; sessions live in the BFF.

## Runtime flow (BFF)

1. User visits a static client site (served by NGINX).
2. User selects “Sign in” → redirect to the BFF login route.
3. BFF starts an OIDC redirect to Keycloak.
4. Keycloak authenticates and redirects back to the BFF callback.
5. BFF exchanges the code for tokens server-to-server and sets a secure cookie.
6. Static site requests `/api/` endpoints; the cookie authenticates the call.

## Persistence

- Keycloak state persists in Postgres.
- Docker volumes store database data; loss implies re-provisioning identity
  state.
- Environment templates (`env.example`) document required variables.

## What this stack does not do

- Serve static client sites.
- Store application business data unrelated to identity.

## Phase 5 Runbook

### Rebuild/restart services

```
cd /srv/compose/platform
docker compose up -d --force-recreate --build flask_bff
```

### Apply migrations (001/002/003) to platform_db

`002_mss_init.sql` is authoritative for MSS schema (including `mss_profile.msn_id` as TEXT).
`003_mss_profile_msn_id_text.sql` is a safety guard for existing DBs; keep it in the runbook to avoid drift.

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

### Expected success criteria

- `GET http://127.0.0.1:8001/health` returns `200`
- `GET http://127.0.0.1:8001/login?tenant=platform&return_to=/admin` returns `302`
- After login in browser:
  - `/admin` loads (200)
  - `/t/platform/console` loads (200)
  - `/t/platform/console/animals` loads (200)

### MSS profile design note

`platform.mss_profile.msn_id` (and `parent_msn_id`) are **TEXT** by design (SAMRAS-style IDs), not UUID.
