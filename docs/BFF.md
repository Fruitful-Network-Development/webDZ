# BFF Scope & Platform – Phase 5 (Admin & User Console Enablement)

This document supersedes earlier BFF scope notes and reflects the **current operational posture**
and the **next planned phase (Phase 5)**. It incorporates decisions already made and extends them
to cover tenant routing, UI surfaces, and data scope **without assuming a finalized data model**.

This document defines **responsibilities, boundaries, and intent**, not final schemas.

---

## 1. BFF Role (Unchanged, Reinforced)

There is **one deployed BFF service**.

The BFF is the **only application-layer service** that:

- Initiates authentication flows
- Interacts with Keycloak
- Holds authenticated user session state
- Enforces authorization and tenant boundaries
- Serves platform-owned UI surfaces (admin + user consoles)
- Mediates all reads and writes to application data sources

Client sites:
- Remain static
- Never store tokens
- Never communicate with Keycloak directly
- Initiate authentication only by redirecting to the BFF

---

## 2. Multi-Tenant Routing Model (Locked)

### Entry Point
All authentication begins at the BFF:

```
https://api.fruitfulnetworkdevelopment.com/login?tenant=<tenant_id>&return_to=<url>
```

The BFF:
- Records the requested tenant context
- Stores `tenant_id` and optional `return_to` in the server-side session
- Validates `return_to` against the `RETURN_TO_ALLOWLIST` environment variable
- Performs OIDC login via Keycloak
- Establishes a session cookie scoped to `api.*`
- Resolves tenant access from identity + role information
- Redirects the user into the appropriate UI surface

### Tenant Resolution
Tenant context is derived from:
- Explicit `tenant` parameter at login
- User membership and roles (from Keycloak)
- Platform-side authorization logic

There is **no separate BFF per tenant**.
Tenant isolation is logical, not infrastructural.

---

## 3. Identity & Authorization Model

### Identity Provider
- Keycloak remains the single IdP
- Users are global to the platform
- Credentials, MFA, and login UX live in Keycloak

### Authorization
The BFF decides:
- Which tenants a user may access
- Which UI modules are visible
- Which operations are permitted

Authorization inputs:
- Keycloak realm roles
- Keycloak client roles (per-tenant OIDC clients)
- Platform-side authorization rules

Authorization guards (JSON responses only):
- `require_login` returns `401 {"error":"not_authenticated"}` when unauthenticated
- `require_tenant_context` returns `400 {"error":"missing_tenant"}` when tenant context is absent
- `require_realm_role` returns `403 {"error":"forbidden"}` when roles are missing

Tenant access (Phase 5 scaffolding):
- `root_admin` has global access
- `tenant_admin:<tenant_id>` grants access to a specific tenant

Example tenant probe endpoint:
- `GET /t/<tenant_id>/ping` (requires login + tenant access)

---

## 4. Keycloak Client Strategy

- Each tenant is modeled as **its own OIDC client** in Keycloak
- All clients authenticate against the same realm
- One BFF codebase supports all tenants

This allows:
- Tenant-specific redirect URIs
- Tenant-scoped roles
- Clean separation of access without duplicating services

---

## 5. UI Surfaces

### Admin Console
Served by the BFF.

Accessible only to:
- Platform root administrators
- Tenant administrators (within their tenant scope)

Responsibilities:
- Tenant visibility and membership management
- Configuration and data inspection
- Controlled mutation workflows (see Section 8)

### User Console
Also served by the BFF.

Accessible to:
- Authenticated users with tenant membership

Responsibilities:
- Viewing and interacting with tenant-scoped data
- No infrastructure or cross-tenant visibility

Both consoles:
- Use a shared core UI
- Vary behavior and available modules through configuration and authorization
- Do not require separate frontend builds per tenant

---

## 6. Data Scope & Authority (Clarified)

### Principal Data Source
The platform recognizes a **principal data authority** that defines:

- Domains of meaning (namespaces)
- Identifier types
- Structural constraints
- Valid relationships between data

This authority **informs how data is read, written, validated, and interpreted**,
regardless of storage backend.

### Data Scope Categories

#### Global Domains
- Exist outside any single tenant
- Provide shared reference data
- Are read-only for most users

Examples (non-exhaustive):
- Taxonomic domains
- Statonomic domains
- Other MNF-governed namespaces

#### Tenant-Local Domains
- Exist within a tenant boundary
- Govern tenant-created groupings and records
- Are mutable by authorized tenant users

### Platform-Owned Data
The platform owns:
- Identity resolution
- Authorization metadata
- Audit records

This data is **not client business data** and is not exposed directly.

---

## 7. Schema as Data (Intent)

The platform treats **schemas themselves as data**.

This means:
- Users may define groupings and fields through the UI
- Definitions are persisted and versionable
- Operational data must conform to the active definitions

The BFF:
- Validates all writes against current definitions
- Mediates references across domains (e.g., ID-based linkage)
- Does not permit arbitrary or implicit structure changes

No assumption is made here about:
- Exact storage format
- Relational vs document representation
- Final migration path from filesystem to database

---

## 8. Mutating Operations (Strict)

The BFF may perform mutating actions **only when all conditions are met**:

- Explicit scope
- Authorization verified
- Inputs validated
- Operation auditable
- Tenant boundaries enforced

### Allowed Categories
- Identity and membership management (via Keycloak APIs)
- Schema definition and update (within tenant scope)
- Data creation and update conforming to schema
- Controlled content promotion workflows

### Explicitly Excluded
- Infrastructure modification
- Arbitrary command execution
- Direct filesystem or service manipulation outside defined workflows

---

## 9. Operational Invariants

- One BFF service
- One Keycloak realm
- Many tenants
- Static client sites remain static
- All authentication flows through the BFF
- All application data access flows through the BFF
- Infrastructure remains manually operated

---
