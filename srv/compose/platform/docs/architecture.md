# Architecture

## Stack overview

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

- Keycloak state persists in its Postgres database.
- Docker volumes store database data; loss implies re-provisioning identity
  state.

## Operational invariants

- One BFF service
- One Keycloak realm
- Many tenants
- Static client sites remain static
- All authentication flows through the BFF
- All application data access flows through the BFF
- Infrastructure remains manually operated

## What this stack does not do

- Serve static client sites.
- Store application business data outside the platform schema.
