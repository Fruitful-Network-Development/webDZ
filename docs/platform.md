# Unified Server-Stack Environment 

## Architecture

The server stack is composed of **Keycloak**, **Flask BFF**, and **PostgreSQL**, deployed via Docker Compose under the `/srv/compose/platform` directory. NGINX remains on the host to terminate TLS and proxy traffic. Client sites are static and are served directly from the filesystem.
1.  **Keycloak** – The single identity provider (IdP) for all users. It handles login, multi-factor authentication and credential management. The platform never exposes Keycloak tokens directly to browsers.
2.  **Flask BFF** – A platform-owned backend-for-frontend that initiates OpenID Connect (OIDC) flows, exchanges codes with Keycloak on the server side, enforces tenant boundaries, and holds the user's session state in a secure cookie. It serves both the admin console and the user console.
3.  **PostgreSQL** – Holds the platform schema (`platform`), storing identity resolution (`platform.user_profiles`) and audit logs. Keycloak uses its own separate database.

* **BFF** defines how the platform authenticates and authorizes users, routes them to the appropriate tenant context, and exposes the admin and user consoles. It guarantees that client applications remain stateless and never touch sensitive credentials.
* **MSS** specifies how data tables are structured and interpreted. It introduces a discipline of *manifest-driven tables* where identifiers and values are type-scoped and table structure is declared, not implicit. MSS is agnostic to the storage backend and provides a clear separation between *schema*, *data* and *authority*.
* **SAMRAS** defines a domain-independent addressing scheme for hierarchical structures. It supplies a canonical *shape* and a method to navigate mixed-radix addresses such as taxonomic trees or geographic hierarchies without flattening the tree.

### Multi-Tenant Routing and Identity
- All authentication starts at the BFF via an endpoint such as `/login?tenant=<tenant_id>&return_to=<url>`. The BFF determines tenant context from the query parameter, user membership, and platform policies. It then redirects to Keycloak for login and receives an authorization code. After exchanging the code, the BFF sets a session cookie scoped to `api.<domain>`. Clients never receive tokens.
- Each tenant is represented as its own OIDC client in Keycloak. Tenant isolation is logical; there is a single BFF instance and a single Keycloak realm. The BFF uses Keycloak roles together with platform rules to decide which tenants and UI modules a user may access.

**Operational Invariants**
- One BFF service
- One Keycloak realm
- Many tenants
- Static client sites remain static
- All authentication flows through the BFF
- All application data access flows through the BFF
- Infrastructure remains manually operated

---

## 1. BFF Role

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

### 1.1 Multi-Tenant Routing Model (Locked)

**Entry Point**
All authentication begins at the BFF:

```
https://api.fruitfulnetworkdevelopment.com/login?tenant=<tenant_id>&return_to=<url>
```
- Records the requested tenant context
- Stores `tenant_id` and optional `return_to` in the server-side session
- Validates `return_to` against the `RETURN_TO_ALLOWLIST` environment variable
- Performs OIDC login via Keycloak
- Establishes a session cookie scoped to `api.*`
- Resolves tenant access from identity + role information
- Redirects the user into the appropriate UI surface

**Tenant Resolution**
Tenant context is derived from:
- Explicit `tenant` parameter at login
- User membership and roles (from Keycloak)
- Platform-side authorization logic

There is **no separate BFF per tenant**.
Tenant isolation is logical, not infrastructural.

### 1.2 Identity & Authorization Model

**Identity Provider**
- Keycloak remains the single IdP
- Users are global to the platform
- Credentials, MFA, and login UX live in Keycloak

**Authorization**
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

### 1.3 Keycloak Client Strategy

- Each tenant is modeled as **its own OIDC client** in Keycloak
- All clients authenticate against the same realm
- One BFF codebase supports all tenants

This allows:
- Tenant-specific redirect URIs
- Tenant-scoped roles
- Clean separation of access without duplicating services

---

## 2.0 Console Ontology
### 2.1 Structured UI Outline

#### 2.1.1 Admin Console Root
The **admin console** is restricted to platform administrators and tenant administrators. It provides tools for tenant management, membership, and schema definition. The **user console** is available to authenticated users and exposes tenant-specific data according to the schemas defined by tenants. Both consoles use a shared UI but are configured at runtime based on roles and manifests.

**PRIMARY ELEMENTS**
- **Client Summary Cards**:
  - `tenant_id`
  - status (active / suspended)
  - structural readiness indicators:
    - MSS present
    - archetypes defined
    - tables provisioned
    **Per client card:**
      - `tenant_id` + status
      - Structural readiness panel:
        - MSS profile provisioned
        - Archetype coverage
        - Manifest status (tables bound)
      - Actions:
        - **Enter Client Console**
        - **Inspect MSS readiness** (read-only)
        - **Inspect structural data readiness** (archetypes, manifests, tables)
      > **Explicit exclusion:** No direct access to tenant business records from this view.
- **Primary Actions:**
  - **Add Client** (stub CTA with wiring pending indicator)
  - **Enter Client Console** (context switch)
- **Platform-level sections:**
  - **My Data Tables** (platform-owned)
  - **My Lists** (platform-owned)
  - **System Shape** (MSS + SAMRAS + Registry health)

> **Authority note:** This page is global to the platform and belongs only to the `fruitful-admin` realm.

**NAVIGATION**
- **Overview**: “Where are the worlds and what is their structural state?”
  - Cross-tenant situational awareness.
- **Clients**: “Which client worlds exist and are they structurally valid?”
  - Tenant structure readiness only (not business records).
- **Platform Data**: “Platform-owned tables and lists (registry-backed)”.
  - The admin’s own data space (fruitful realm).
- **System**: “MSS profiles, SAMRAS layouts, and archetype registry health.”
  - anonical shape authority layer: MSS + SAMRAS + registry.

**ADMIN CLIENT PAGE**
**Context switch requirements:**
- Persistent header banner: `CLIENT CONTEXT: <tenant_id>`
- Exit to Admin Overview control
- Audit-friendly breadcrumbs (“Admin → Client → Section”)
  **Client Console Tabs:**
  1. **Data**
     - **MSS Profiles** (tenant-scoped identity anchors)
     - **Archetypes** (shape contracts)
     - **Provisioned Tables** (containers)
  2. **Services** (Scaffold)
     - Billing
     - Email / Notifications
  3. **Identity**
     - Roles
     - Access boundaries
  **Admin CAN:**
  > Provision and validate structural shape (MSS, archetypes, manifests, tables)
  > Observe readiness and access boundaries
  > Enter client console modules to inspect structure and permissions
  **Admin CANNOT (by default):**
  > Modify or browse client business data outside provisioned admin modules
  > Collapse structure with content or bypass shape constraints

$ Component Hierarchy (Conceptual)
```
AdminShell
├─ GlobalHeader
│  ├─ AdminIdentityBadge (fruitful-admin)
│  ├─ ContextIndicator (global vs client)
│  └─ PrimaryActions (Add Client, Enter Client)
├─ AdminNavigation
│  ├─ OverviewTab
│  ├─ ClientsTab
│  ├─ PlatformDataTab
│  └─ SystemTab
└─ MainContent
   ├─ OverviewDashboard
   │  ├─ ClientSummaryGrid
   │  ├─ PlatformDataSummary
   │  └─ SystemShapeSummary
   ├─ ClientsView
   │  ├─ ClientCard
   │  │  ├─ ReadinessPanel
   │  │  └─ ClientActions
   │  └─ StructuralReadinessFilters
   ├─ PlatformDataView
   │  ├─ TableRegistryPanel
   │  └─ ListsPanel
   └─ SystemView
      ├─ MSSProfileInspector
      ├─ ArchetypeRegistryPanel
      ├─ ManifestBindingsPanel
      └─ SamrasLayoutPanel

ClientContextShell
├─ ClientContextHeader (tenant_id, exit control)
├─ ClientConsoleTabs
│  ├─ DataTab
│  ├─ ServicesTab
│  └─ IdentityTab
└─ ClientConsoleContent
   ├─ DataTab
   │  ├─ MSSProfiles
   │  ├─ Archetypes
   │  └─ ProvisionedTables
   ├─ ServicesTab
   │  ├─ BillingScaffold
   │  └─ EmailScaffold
   └─ IdentityTab
      ├─ RolesPanel
      └─ AccessBoundariesPanel
```

---

## 3.0 Data Interplay

### 3.1 Schema as Data (Intent)

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

### 3.2 Mutating Operations (Strict)

The BFF may perform mutating actions **only when all conditions are met**:

- Explicit scope
- Authorization verified
- Inputs validated
- Operation auditable
- Tenant boundaries enforced

### 3.3 Allowed Categories
- Identity and membership management (via Keycloak APIs)
- Schema definition and update (within tenant scope)
- Data creation and update conforming to schema
- Controlled content promotion workflows

### 3.5 Explicitly Excluded
- Infrastructure modification
- Arbitrary command execution
- Direct filesystem or service manipulation outside defined workflows

### 3.6 Unifying the Data and BFF

The **Unified Server-Stack Environment** harmonizes identity management, schema discipline and hierarchical addressing into a consistent architecture. **BFF** ensures secure and centralized authentication and serves UI surfaces. **MSS** structures data tables declaratively and enforces type and authority boundaries. **SAMRAS** provides a principled way to address hierarchical data without embedding meaning into identifiers. Together, these components enable multi-tenant applications where users can define their own schemas, link to global domains like taxonomies, and interact with data through dynamic UIs, all while maintaining strong governance and extensibility.

#### 3.6.1 Identity Resolution and User Hierarchy
The **MSS Profile table** provides the bridge between Keycloak and the platform's own identity model. When a user logs in via the BFF, the BFF uses Keycloak's user ID to look up or create an entry in the `platform.user_profiles` table and the MSS Profile table. The MSS profile entry records the user's `msn_id`, sub-users, and hierarchical relationships. In effect, this table defines a unified *user hierarchy* that the BFF consults to decide how to render the UI and what operations are permitted. Because the MSS Profile table is under administrative control, tenants cannot impersonate or rearrange identities.

#### 3.6.2 Dynamic Schemas and UIs
Tenants define new tables and fields via the admin console. The process is:
1.  **Create or select a Local Domain entry** – The tenant registers a new `local_id` and title for the table.
2.  **Define an Archetype** – The tenant uses a wizard to define fields, their types (`system_id` or `system_value`), reference domains (e.g., `taxonomy`, `msn`, `local`), and constraints. This becomes an archetype table.
3.  **Bind via the Manifest Table** – A manifest record links the table's `local_id` with its archetype's `local_id` and determines how many rows the archetype table should have.
When a user visits the user console, the BFF reads the manifest and archetype tables to build dynamic UI forms. Because the tables themselves do not encode their schema, the BFF can render any general table by consulting the manifest and archetype definitions. Data values are validated against these definitions before writes are allowed.

#### 3.6.3 Linking Data Across Domains
If a field references the `taxonomy` domain, it stores a SAMRAS address rather than a string. The SAMRAS archetype table ensures the reference semantics (exact, group, existential descendant) are respected. The BFF validates the address against the correct layout version in the SAMRAS table. For fields that use lists (e.g., `dependents`, `suppliers`), the stored value is an ordinal (`system_value`) that reduces to an `msn_id` via a local list table. This pattern ensures that references are explicit and type-checked.

#### 3.6.4 Authority Enforcement
Because all data access goes through the BFF, it can enforce MSS authority rules. The BFF ensures that tenants can create and modify their own local domain, manifest, archetype and general tables, while only system administrators can modify the MSS profile, SAMRAS, and SAMRAS archetype tables. Audit events are recorded in `platform.audit_log` for each mutation.

#### 3.6.5 Data Evolution and Migration
When a tenant edits an archetype, the platform increments the archetype version. Existing data remains tied to its previous archetype version. The BFF may provide tooling to migrate records explicitly by transforming them to conform to the new archetype. Similarly, if a SAMRAS layout changes beyond append-only growth, the system publishes a new layout version and general tables reference the appropriate version.

#### 3.6.5 Extensibility and Separation of Concerns
This unified stack deliberately separates concerns:
* **Authentication and Authorization** – handled by Keycloak and the BFF.
* **Schema Definition and Interpretation** – handled by MSS tables. The data model is declarative and extensible.
* **Hierarchical Structure** – handled by SAMRAS tables. Shape and meaning are separate and versioned.
* **Data Storage** – handled by general tables in Postgres. The storage format remains nested JSON at the canonical level and can be projected to relational tables for indexing or performance.
By adhering to these boundaries, the platform can evolve without disrupting existing data or clients.

---
