# Identity & Access

## BFF role

There is **one deployed BFF service**. The BFF is the only application-layer
service that:

- Initiates authentication flows
- Interacts with Keycloak
- Holds authenticated user session state
- Enforces authorization and tenant boundaries
- Serves platform-owned UI surfaces (admin + tenant consoles)
- Mediates all reads and writes to application data sources

Client sites:

- Remain static
- Never store tokens
- Never communicate with Keycloak directly
- Initiate authentication only by redirecting to the BFF

## Multi-tenant routing model

**Entry point**

All authentication begins at the BFF:

```
https://api.fruitfulnetworkdevelopment.com/login?tenant=<tenant_id>&return_to=<url>
```

- Records the requested tenant context.
- Stores `tenant_id` and optional `return_to` in the server-side session.
- Validates `return_to` against the tenant's `allowed_return_to` list.
- Performs OIDC login via Keycloak.
- Establishes a session cookie scoped to `api.*`.
- Resolves tenant access from identity and role information.
- Redirects the user into the appropriate UI surface.

**Tenant resolution**

Tenant context is derived from:

- Explicit `tenant` parameter at login
- User membership and roles (from Keycloak)
- Platform-side authorization logic

There is **no separate BFF per tenant**. Tenant isolation is logical, not
infrastructural.

## Identity & authorization model

**Identity provider**

- Keycloak remains the single IdP.
- Users are global to the platform.
- Credentials, MFA, and login UX live in Keycloak.

**Authorization**

The BFF decides:

- Which tenants a user may access
- Which UI modules are visible
- Which operations are permitted

Authorization inputs:

- Keycloak realm roles
- Keycloak client roles (per-tenant OIDC clients)
- Platform-side authorization rules

Authorization guards (JSON responses):

- `require_login` returns `401 {"error":"not_authenticated"}` when unauthenticated
- `require_tenant_context` returns `400 {"error":"missing_tenant"}` when tenant context is absent
- `require_realm_role` returns `403 {"error":"forbidden"}` when roles are missing

Tenant access (Phase 5 scaffolding):

- `root_admin` has global access
- `tenant_admin:<tenant_id>` grants access to a specific tenant

Example tenant probe endpoint:

- `GET /t/<tenant_id>/ping` (requires login + tenant access)

## Keycloak client strategy

- Each tenant is modeled as its own OIDC client in Keycloak.
- All clients authenticate against the same realm.
- One BFF codebase supports all tenants.

This allows:

- Tenant-specific redirect URIs
- Tenant-scoped roles
- Clean separation of access without duplicating services

## Tenant registry (file-backed)

Admin API endpoints (root-admin only):

- `POST /api/admin/tenants` creates a tenant folder + `tenant.json` and updates `index.json`.
- `GET /api/admin/tenants/<tenant_id>` returns the sanitized tenant config.
- `PUT /api/admin/tenants/<tenant_id>` updates `tenant.json` after schema validation.
- `DELETE /api/admin/tenants/<tenant_id>` performs a soft delete by default.

Soft delete behavior:

- Removes the tenant id from `index.json`.
- Marks the tenant as disabled by writing `"disabled": true` in `tenant.json`.

Hard delete behavior:

- Use `DELETE /api/admin/tenants/<tenant_id>?hard=1`.
- Removes the tenant id from `index.json` and deletes the tenant folder.

## Auth behaviors and errors

- HTML routes redirect to `/login?tenant=platform&return_to=<path>` when unauthenticated.
- JSON API routes return `401` with `{ "error": "not_authenticated" }`.
- Unauthorized or not provisioned returns `403` with a consistent message.

Troubleshooting:

- `401 not_authenticated`: session missing or expired → sign in again.
- `403 forbidden`: authenticated but missing admin/tenant role.
- `403 not_provisioned`: authenticated but missing MSS profile.
