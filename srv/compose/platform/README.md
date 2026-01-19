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
