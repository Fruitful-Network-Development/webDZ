# /srv/compose/platform

This directory defines the **platform identity and control plane** for Fruitful Network Development.
It introduces centralized authentication, a Backend-for-Frontend (BFF), and platform-owned identity
persistence **without altering existing static client sites**.

This README reflects the state after successful Phase 3 bring-up:
- Keycloak IdP running and reachable
- Flask BFF handling OIDC login and sessions
- Platform Postgres persisting platform-owned identity records
- Realm roles (e.g. `root_admin`) in active use

---

## Directory Purpose

`/srv/compose/platform` contains one Docker Compose stack that is responsible for:

- Identity and authentication (Keycloak)
- Server-side session management (Flask BFF)
- Platform-level identity resolution (Postgres, `platform` schema)
- Future admin and user UIs (served by the BFF)

This stack **does not** serve static client sites and **does not** manage infrastructure services
such as NGINX or TLS certificates.

---

## Containerization Rationale

Compose stacks live under `/srv/compose` when a service benefits from isolation,
portability, or well-defined lifecycle management.

### Why these services are containerized
- Third-party services (Keycloak) are isolated from the host.
- Safer upgrades and rollbacks via image pinning.
- Clear separation between host-native services and application logic.
- Predictable networking and dependency boundaries.

### Why other services are not
- **NGINX** remains on the host for TLS termination and lowest-latency ingress.
- **Static client sites** remain on the host filesystem for direct serving.

### Operational model
- One Compose stack per responsibility group.
- Stacks are supervised by systemd units (e.g. `compose-platform.service`).
- Environment templates are committed; secrets are not.

---

## Structure
```text
/srv/compose/platform/
├── README.md
├── .env
├── docker-compose.yml
├── flask-bff/
│   ├── app.py
│   ├── config.py
│   ├── Dockerfile
│   ├── entrypoint.sh
│   ├── gunicorn.conf.py
│   ├── requirements.txt
│   ├── routes/
│   │   ├── admin.py
│   │   ├── auth.py
│   │   ├── tables.py
│   │   ├── tenant.py
│   │   └── user.py
│   ├── utils/
│   │   ├── mss.py
│   │   └── samras.py
│   ├── templates/
│   │   ├── base.html
│   │   └── admin/
│   │       └── index.html
│   └── admin/
│       └── admin.css
├── keycloak/
│   └── (realm exports, if any)
└── platform-schema/
    └── 001_init.sql
```

---

## Services

### Keycloak (Identity Provider)
- Centralized IdP for all users
- Owns credentials, MFA, password resets, and login flows
- Exposed publicly via `auth.<domain>` through NGINX
- Never accessed directly by client sites

### Flask BFF
- Platform-owned Backend-for-Frontend
- Initiates OIDC login flows against Keycloak
- Exchanges authorization codes server-side
- Issues secure, server-managed session cookies
- Enforces authorization and role checks
- Stores tenant context from `/login?tenant=<tenant_id>` and validates `return_to`
- Serves the platform admin UI and future user UI

### Postgres (Platform + Keycloak)
- Keycloak uses its own dedicated database
- Platform uses a **separate** database and schema
- Platform DB stores identity resolution and audit data only

---

## Public Interfaces

- `auth.<domain>` → Keycloak (pure proxy vhost)
- `api.<domain>` → Flask BFF (pure proxy vhost; enabled in later phases)

Client domains:
- Remain static
- Are served directly from the filesystem
- May redirect users to the BFF for authentication

No client domain ever proxies directly to Keycloak.

---

## Trust Boundaries

- NGINX is the only public ingress
- All containers bind to localhost only
- NGINX explicitly proxies to container ports
- Static sites never store tokens or credentials
- All authentication state lives in the BFF session layer

---

## Runtime Authentication Flow

1. User visits a static client site.
2. User selects “Sign in” → redirected to the BFF (`/login?tenant=<tenant_id>&return_to=<url>`).
3. BFF redirects to Keycloak (OIDC).
4. Keycloak authenticates the user.
5. Keycloak redirects back to BFF `/callback`.
6. BFF exchanges the code server-side.
7. BFF establishes a secure session cookie.
8. User is redirected to `/admin` or another UI route.

At no point are access or refresh tokens exposed to the browser.

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
2. User selects “Sign in” → redirected to the BFF login route with tenant context.
3. BFF initiates an OIDC redirect to Keycloak.
4. Keycloak authenticates the user.
5. Keycloak redirects back to the BFF callback endpoint.
6. BFF exchanges the authorization code server-to-server.
7. BFF establishes a secure session and sets a cookie.
8. Static site JavaScript may call `/api/*` endpoints.
9. The BFF authenticates requests using the session cookie.

At no point are tokens exposed to the browser.

---

## Platform Persistence

### `platform.user_profiles`

Platform-owned identity resolution table.

- Primary key: Keycloak UUID (`user_id`)
- Canonical user presence across the platform
- Written on first successful login

Explicitly does **not** store:
- Passwords or credentials
- MFA state
- Tokens or sessions
- Client-specific business data

### Other platform tables
- `platform.audit_log` — security and mutation events
- Future tables for memberships and authorization metadata

All platform tables live under the `platform` schema.

---

## MSS + SAMRAS Features

The platform DB now supports MSS + SAMRAS schema registry and hierarchy management:

- `platform.local_domain` — local domain registry (per-tenant semantic domains).
- `platform.archetype` and `platform.archetype_field` — archetype definitions and field constraints.
- `platform.manifest` — table bindings between local domains and archetypes.
- `platform.samras_layout` and `platform.samras_archetype` — SAMRAS layouts and archetype metadata.
- `platform.mss_profile` — MSS hierarchy mapping of Keycloak user IDs to MSN IDs and roles.

Together these tables power:
- Dynamic tenant tables (`/api/t/<tenant_id>/tables/<table_id>`) based on manifest/archetype definitions.
- SAMRAS validation for reference fields.
- MSS hierarchy lookups attached to sessions (`/me`) and used to resolve dynamic table names.

---

## Flask BFF Modules

The BFF has been split into smaller modules/blueprints:

- `app.py` — app factory, blueprint registration, and lifecycle hooks.
- `config.py` — environment configuration (OIDC + cookie settings).
- `routes/auth.py` — login/callback/logout and session APIs (`/me`).
- `routes/admin.py` — admin UI + schema registry APIs (`/api/admin/*`).
- `routes/user.py` — MSS profile and user hierarchy management APIs.
- `routes/tables.py` — tenant table CRUD + SAMRAS lookup APIs.
- `routes/tenant.py` — tenant console and ping endpoints.
- `utils/samras.py` — SAMRAS parsing and validation helpers.
- `utils/mss.py` — MSS profile lookup helpers.

---

## Testing

Integration tests live under `flask-bff/tests/` and exercise API + DB flows and the mocked OIDC login flow.

### Prerequisites
- A Postgres database for testing.
- Set `PLATFORM_DB_URL` to a test database URL (must be writable).
- OIDC env vars for test startup:
  - `OIDC_ISSUER`
  - `OIDC_CLIENT_ID`
  - `OIDC_CLIENT_SECRET`
  - `SESSION_SECRET`

### Run
```bash
cd /srv/compose/platform/flask-bff
pytest -q tests/
```

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

## Keycloak realm exports

Realm exports (JSON) may be placed here for development or recovery.
Do not commit secrets or credentials.

### Export a realm

From a running Keycloak container, you can export a realm file:
```bash
/opt/keycloak/bin/kc.sh export   --dir /opt/keycloak/data/import   --realm <realm-name>   --users realm_file
```
Copy the exported JSON into this directory (for example,
`my-realm-export.json`).

### Import a realm

Realm JSON files placed in `/opt/keycloak/data/import` will be imported at startup.

### Keep secrets out of Git

- Remove or redact user passwords, client secrets, and external identity
  provider credentials before committing.
- Prefer environment variables or secret management for sensitive values.

 ---
