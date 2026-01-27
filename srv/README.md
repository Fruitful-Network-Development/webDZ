# Platform Auth & BFF Stack

This stack adds authentication and a backend-for-frontend (BFF) layer while
keeping host static sites unchanged.

## Conceptual ontology

The platform is guided by a small set of conceptual planes. Each plane owns a
distinct responsibility, and the system is designed to keep the planes
orthogonal and composable.

- **Identity & Access Plane**: Keycloak + BFF session model, tenant routing, and
  authorization. Users are global; tenant access is resolved by roles and
  platform rules. Clients never receive tokens.
- **Data Discipline Plane**: MSS table classes, schema-as-data, and authority
  boundaries. Tables are interpreted via manifests and archetypes, not
  self-describing.
- **Structure Addressing Plane**: SAMRAS layouts and reference semantics for
  hierarchical addressing. Shape is authoritative; meaning is layered.
- **Experience Plane**: Admin and tenant consoles, module boundaries, and UI
  shell contracts. Core is stable; modules plug in without redefining identity
  or data contracts.
- **Operations Plane**: Runbooks, migrations, provisioning, and demo workflows.

## Layout
```text
aws-box/
├── README.md
├── docs/
│   ├── runbook.md
│   └── etc-documentation/etc.md
└── srv/
    ├── webapps/
    │   └── clients/
    │       ├── fruitfulnetworkdevelopment.com/
    │       ├── cuyahogavalleycountrysideconservancy.org/
    │       ├── trappfamilyfarm.com/
    │       └── cuyahogaterravita.com/
    └── compose/
        └── platform/
            ├── docker-compose.yml
            ├── .env
            ├── rsync.filter
            ├── platform-schema/
            ├── scripts/
            ├── keycloak/realm/
            └── flask-bff/
                ├── Dockerfile
                ├── data/tenants/
                ├── routes/
                ├── templates/
                ├── static/
                ├── utils/
                └── tests/
```

## Architecture at a glance

- **Services**: Keycloak (IdP), Flask BFF, Postgres (platform schema + Keycloak).
- **Ingress**: NGINX terminates TLS; containers bind to localhost only.
- **Public interfaces**: `auth.<domain>` → Keycloak, `api.<domain>` → Flask BFF.
- **Runtime flow**: static site → BFF login → Keycloak → BFF callback → secure
  cookie → `/api/` requests.
- **Non-goals**: serve static sites; store business data outside the platform
  schema; expose tokens to browsers.

## Doc map

- `docs/identity-access.md` — auth flow, roles, tenant registry, access rules.
- `docs/data-discipline.md` — MSS table classes, schema-as-data, invariants,
  SAMRAS addressing.
- `docs/console-experience.md` — admin/tenant console concepts and modules.
- `keycloak/realm/README.md` — realm export/import guidance.

## Quick pointers

- Login entry point: `/login?tenant=<tenant_id>&return_to=<path>`
- Root admin provisioning script: `scripts/provision_root_admin.sh`
- Migration scripts: `platform-schema/001_init.sql`, `002_mss_init.sql`,
  `003_mss_profile_msn_id_text.sql`

## Architecture

### Stack overview

The server stack is composed of **Keycloak**, **Flask BFF**, and **PostgreSQL**,
deployed via Docker Compose under `/srv/compose/platform`. NGINX remains on the
host to terminate TLS and proxy traffic. Client sites are static and are served
directly from the filesystem.

1. **Keycloak**: The single identity provider (IdP) for all users. It handles
   login, MFA, and credential management. The platform never exposes Keycloak
   tokens directly to browsers.
2. **Flask BFF**: The platform-owned backend-for-frontend that initiates OIDC
   flows, exchanges codes with Keycloak server-side, enforces tenant boundaries,
   and holds session state in a secure cookie. It serves the admin and tenant
   consoles.
3. **PostgreSQL**: Holds the platform schema (`platform`), including MSS tables
   and tenant-facing data. Keycloak uses its own separate database.

### Public interfaces

- `auth.<domain>` → Keycloak (pure proxy vhost).
- `api.<domain>` → Flask BFF (pure proxy vhost).
- Primary client domains remain static, with optional proxy routes for auth UI.

### Trust boundaries

- NGINX is the only public ingress.
- Containers bind to localhost; NGINX proxies to them explicitly.
- Static sites never store tokens; sessions live in the BFF.

### Runtime flow (BFF)

1. User visits a static client site (served by NGINX).
2. User selects “Sign in” → redirect to the BFF login route.
3. BFF starts an OIDC redirect to Keycloak.
4. Keycloak authenticates and redirects back to the BFF callback.
5. BFF exchanges the code for tokens server-to-server and sets a secure cookie.
6. Static site requests `/api/` endpoints; the cookie authenticates the call.

### Persistence

- Keycloak state persists in its Postgres database.
- Docker volumes store database data; loss implies re-provisioning identity
  state.

### Operational invariants

- One BFF service
- One Keycloak realm
- Many tenants
- Static client sites remain static
- All authentication flows through the BFF
- All application data access flows through the BFF
- Infrastructure remains manually operated

### What this stack does not do

- Serve static client sites.
- Store application business data outside the platform schema.

## Operations

### Runbook

#### Rebuild/restart services

```
cd /srv/compose/platform
docker compose up -d --force-recreate --build flask_bff
```

#### Apply migrations (001/002/003) to platform_db

`002_mss_init.sql` is authoritative for MSS schema (including
`mss_profile.msn_id` as TEXT). `003_mss_profile_msn_id_text.sql` is a safety
guard for existing DBs; keep it in the runbook to avoid drift.

```
cd /srv/compose/platform
cat platform-schema/001_init.sql | docker exec -i platform_db psql -U platform -d platform
cat platform-schema/002_mss_init.sql | docker exec -i platform_db psql -U platform -d platform
cat platform-schema/003_mss_profile_msn_id_text.sql | docker exec -i platform_db psql -U platform -d platform
```

#### Provision root admin (MSS profile)

```
cd /srv/compose/platform
USER_ID="<keycloak-user-uuid>" MSN_ID="<samras-text-id>" ./scripts/provision_root_admin.sh
```

#### Login URL pattern

```
https://api.fruitfulnetworkdevelopment.com/login?tenant=<tenant_id>&return_to=<path>
```

Working example:

```
https://api.fruitfulnetworkdevelopment.com/login?tenant=platform&return_to=/admin
```

### Admin console expectations

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

### Expected success criteria

- `GET http://127.0.0.1:8001/health` returns `200`
- `GET http://127.0.0.1:8001/login?tenant=platform&return_to=/admin` returns `302`
- After login in browser:
  - `/admin` loads (200)
  - `/t/platform/console` loads (200)
  - `/t/platform/console/animals` loads (200)

### MSS profile design note

`platform.mss_profile.msn_id` (and `parent_msn_id`) are **TEXT** by design
(SAMRAS-style IDs), not UUID.

### Keycloak realm exports

See `keycloak/realm/README.md` for export/import guidance.
