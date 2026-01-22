# /srv/compose/platform

## Auth & BFF Stack

This stack introduces authentication and a Backend-for-Frontend (BFF) layer
while keeping the host’s static client sites unchanged.

It is the **platform control plane** for identity, authorization, and
authenticated application access. All components in this directory are
containerized and supervised together via Docker Compose.

---

## Purpose

This stack exists to:

- Provide a centralized identity provider (IdP) for all users
- Establish a BFF that is the **only component allowed to interact with the IdP**
- Issue secure, server-managed sessions for browser clients
- Serve as the foundation for future platform and admin UIs
- Maintain strict separation between:
  - infrastructure
  - identity
  - platform control logic
  - client-specific operational data

This stack intentionally does **not** replace or modify existing static client
sites.

---

## Services

### Keycloak (IdP)
- Handles authentication, login flows, and identity lifecycle
- Owns credentials, MFA, password resets, and session issuance
- Exposed publicly via `auth.<domain>` through an NGINX proxy
- Never accessed directly by client sites

### Postgres (Keycloak-only)
- Dedicated persistence for Keycloak state
- Stores users, realms, clients, sessions, and IdP configuration
- Data is stored in Docker volumes
- Loss of this database implies re-provisioning identity state

### Flask BFF
- Platform-owned Backend-for-Frontend
- Initiates OIDC login flows against Keycloak
- Exchanges authorization codes server-side
- Issues secure session cookies (`HttpOnly; Secure; SameSite=Lax`)
- Enforces authorization and tenant boundaries
- Acts as the future home of:
  - platform admin UI
  - authenticated user portal
  - controlled mutation endpoints

---

## Public Interfaces

- `auth.<domain>` → Keycloak (pure proxy vhost)
- `api.<domain>` → Flask BFF (pure proxy vhost; **not enabled initially**)

Primary client domains:
- remain static
- are served directly from the filesystem
- may optionally link or redirect users to the BFF for authentication

No client domain ever proxies directly to Keycloak.

---

## Trust Boundaries

- **NGINX is the only public ingress**
- All containers bind to `localhost` only
- NGINX explicitly proxies to container ports
- Static client sites:
  - never store access tokens
  - never store refresh tokens
  - never communicate directly with Keycloak
- All authentication state lives in the BFF session layer

---

## Runtime Flow (BFF)

1. User visits a static client site (served by NGINX).
2. User selects “Sign in” → redirected to the BFF login route.
3. BFF initiates an OIDC redirect to Keycloak.
4. Keycloak authenticates the user.
5. Keycloak redirects back to the BFF callback endpoint.
6. BFF exchanges the authorization code server-to-server.
7. BFF establishes a secure session and sets a cookie.
8. Static site JavaScript may call `/api/*` endpoints.
9. The BFF authenticates requests using the session cookie.

At no point are tokens exposed to the browser.

---

## Persistence

### Identity Persistence
- Keycloak state is persisted in its dedicated Postgres database
- Backed by Docker volumes
- Database lifecycle is tied to identity availability

### Platform Persistence (Phase 3+)
A **separate platform database** may be introduced for identity resolution and
authorization metadata.

This database is **not shared** with Keycloak.

---

## Table Naming & Semantics (Platform DB)

### `platform.user_profiles`

**Platform-owned identity resolution table.**

- Stores canonical user records keyed by Keycloak UUID (`user_id`)
- Represents a stable, system-wide identity across all clients
- Is authoritative for:
  - identity resolution
  - platform-level user presence
  - cross-client linkage

**Explicitly does NOT store:**
- passwords or credentials
- authentication or MFA state
- session tokens
- client-specific operational data

This table exists to resolve “who is this person” across systems, not “how do
they authenticate” or “what data do they own in a given client.”

### Companion Tables (Phase 3+)
- `platform.user_identifiers` (normalized email/phone hashes)
- `platform.client_memberships` (user ↔ client ↔ role)
- `platform.audit_log` (security and mutation events)

All platform tables live under the `platform` schema to avoid name pollution and
to keep table names clean and unprefixed.

---

## What This Stack Does NOT Do

- Serve static client frontends
- Store client operational or business data
- Modify NGINX configuration
- Execute arbitrary shell commands
- Manage systemd services directly
- Issue or renew TLS certificates

These remain **infrastructure responsibilities**, not platform UI actions.

---

## Operational Philosophy

- Configuration is staged via GitHub and rsync
- Activation is always explicit and manual
- No service becomes public by accident
- Identity and platform control are introduced incrementally
- Failure in this stack should not break static client sites

This directory defines a **control plane**, not a general-purpose backend.
