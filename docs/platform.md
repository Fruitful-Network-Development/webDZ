# System Conceptual Ontology

## Architecture

flowchart TD
  IdentityAccess[IdentityAccessPlane]
  DataDiscipline[DataDisciplinePlane]
  StructureAddressing[StructureAddressingPlane]
  Experience[ExperiencePlane]
  Operations[OperationsPlane]
  IdentityAccess --> DataDiscipline
  StructureAddressing --> DataDiscipline
  IdentityAccess --> Experience
  DataDiscipline --> Experience
  Operations --> IdentityAccess
  Operations --> DataDiscipline

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

## 2.0 User Interface

### CORE CONSOLE DESIGN
> Core is what must remain stable for every tenant and every module. It is your operating system. Core contract: modules plug into the shell; the shell does not embed business logic.

#### IDENTITY + TENANCY
* Tenant selection and routing (tenant_registry, allowed_return_to, /t/<tenant>/…)
* Session/auth integration (Keycloak/OIDC)
* Authorization primitives (root-admin vs tenant-admin vs tenant-user)
* Provisioning gate (“not provisioned” via MSS profile)
> **Core contract**: every request has a resolved tenant context + user context or a deterministic error/redirect.

#### DATA CONTORL PLANE (MSS)
> Omits serving static client frontends or controlling infrastructure services `github.com`. It is a *control plane* for identity and data access; external business logic must call through the BFF to reach the data.

#### RUN TIME DATA PLANE 

**PLATFORM DATA**
  *shaping the space, not filling it.*
Tables:
  - Registry-backed
  - Archetype-validated
  - Not tenant-scoped unless explicitly bound
Lists:
  - Ordered references (not categories)
  - Used to resolve ordinals and structural linkage

**GENERIC CRUD**

#### UI SHELL

### MODUELS
#### PLATFORM MODUELS
> A platform module is a reusable capability that many tenants might use, but that is not required for the platform to function.
> Platform module contract: it uses core identity + data contracts; it does not redefine them.
#### TENANT MODUELS
> Tenant modules are the use cases for a specific type of tenant. They’re often thin UI + workflows on top of core + platform modules.
> Tenant modules differ from platform modules because they are not universally reusable. They can still be built using the same core + platform components.


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


# Data Discipline

## 1.0  Overview
* **MSS profile table:** A single table per database containing one or more `msn_id` values; it defines the primary authority, sub-users and hierarchical relationships `github.com`. Only system administrators can edit this table. BFF uses it to map Keycloak identities to a canonical `msn_id`, determine sub-user scopes and influence UI behaviour.
* **Local domain table:** Contains every `local_id` and its human-readable title `github.com`. All tables reference `local_id` here.
* **Manifest table:** Binds each table (`local_id`) to an archetype (`local_id`) `github.com`, declaring which archetype governs which table.
* **General tables:** Named `<msn_id><local_id>` and store actual data; structure is dictated by the manifest and archetype tables `github.com`. They must not self-define schema semantics.
* **SAMRAS tables:** Store count-streams and traversal rules; used to validate hierarchical addresses `github.com`.

These structures establish authority boundaries and deterministic interpretation of data. They require a dedicated schema (created via migrations) and environment variables for DB connection, plus initial seeding of the MSS profile. 

> The SAMRAS specification is domain-agnostic. In the Fruitful Network context, it is used for the **taxonomic domain**, the **statonomic domain**, and any hierarchical namespaces like geographic divisions. However, the same addressing rules apply whether the domain is biology, geography or organizational structure.

### 1.1 Manifest-Structured Schema (MSS)

MSS organizes all tables into seven **table classes** to ensure schema consistency, authority separation, and lossless nested structure.
**system_id vs. system_value**
* **system_id** – An opaque, domain-typed identifier such as `taxonomy_id`, `msn_id` (mixed-space number for people/orgs), or `local_id`. These IDs are authoritative and globally unique within their domain.
* **system_value** – A primitive value (natural number, mass, timestamp, coordinate, currency) that may *reduce* to an identifier via a lookup list. For example, the `dependents` column may store an ordinal whose meaning comes from a dependents list; resolving the ordinal yields the corresponding `msn_id`.

#### 1.1.1 Table Classes**
1.  **MSS Profile Table** – A single table per database that defines the principal user(s) of the database, their `msn_id`, sub-users, hierarchical relations, and permission scopes. This table anchors governance: only system administrators can modify it. In the unified environment, this table becomes the backbone for managing client UIs and their user hierarchies. It maps Keycloak user identities to the platform's own `msn_id` and defines which sub-users exist and what permissions they have.
2.  **Local Domain Table** – Holds every `local_id` and its title. It functions as the dictionary of tenant-scoped terms. Titles are stored only here; other tables reference `local_id` values to avoid duplication.
3.  **Manifest Table** – Associates a table (`local_id`) with the archetype (`local_id`) that governs it. This table determines how many rows an archetype table has and which archetype applies to each general table.
4.  **Archetype Tables** – Contain one column of `local_id` values; the number of rows is dictated by the manifest. They describe the *structure* (fields, references, constraints) of a data table but store no data themselves.
5.  **General Tables** – Hold actual data values. Their names are formed by concatenating the user's `msn_id` with a `local_id` describing the table. Columns are typed either as `system_value` or `system_id` and may reference lists or SAMRAS addresses. The manifest and archetype tables determine which columns exist and how they should be interpreted.
6.  **SAMRAS Tables** – Specialized tables used when a new namespace employs shape-addressed hierarchy. They store the count-stream, traversal specification and layout version for a SAMRAS domain.
7.  **SAMRAS Archetype Tables** – Define valid reference modes (exact, group, existential descendant) for SAMRAS addresses. These constrain how SAMRAS addresses may be used in general tables.

### 1.2 Authority Boundaries**
Authority over each table class is enforced to protect system integrity:
* **System administrators** manage the MSS Profile, SAMRAS and SAMRAS archetype tables.
* **Tenants** manage local domains, manifests, archetypes, and general tables within their scope.

### 1.3 Hierarchical Addressing: SAMRAS
SAMRAS provides a domain-independent way to address nodes in hierarchical structures using mixed-radix ordinals.

### 1.4 Shape vs. Meaning
SAMRAS cleanly separates the *shape* of a hierarchy from any semantic labels attached to nodes. The shape is authoritative and is represented as a count-stream—a list of natural numbers where each number specifies the number of children for a node .

### 1.5 Address Space
A SAMRAS address is written as `a1_a2_..._an`, where each `ai` is the ordinal position among siblings. There is no fixed radix; the maximum allowed value of each `ai` is determined by the parent's child count. Parent addresses are obtained by dropping the last segment. Children are allocated sequentially in append-only fashion so existing addresses never change.
Not every address has to be materialized. SAMRAS allows **ghost positions**—addressable slots that lack any attached metadata. References may also include existential placeholders (suffix segments of `0`) to indicate an unknown descendant rather than a specific node. Because SAMRAS is a structural addressing scheme, reference semantics (exact, group, existential descendant) must be declared explicitly when using an address.

### 1.5 Versioning
If reordering is needed or if the shape evolves in non-append ways, a new layout version must be published. Existing addresses remain valid under their layout version; no silent remapping is permitted. SAMRAS tables in MSS store these layout versions and the count-streams that define them.

---

## 2.0 MSS (Mycilial Structured Schema)

MSS defines a **table‑level schema discipline** for systems where:
- nested structure is canonical,
- identifiers are domain‑typed (`system_id`),
- values are reducible (`system_value`),
- and tables derive meaning from manifests rather than intrinsic schemas.
MSS is designed to work with SAMRAS, but does not depend on it.

### 2.1 Core Principles
1. **Tables are interpreted, not self‑describing**
2. **Identifiers are domain‑scoped**
3. **Values reduce to identifiers**
4. **Structure is declared once, reused many times**
5. **Authority boundaries are enforced by table class**

MSS ensures:
- schema consistency without rigid schemas,
- lossless nesting,
- clear authority separation,
- extensibility without migration cascades,
- and deterministic interpretation of tables.
It is a schema discipline, not a database product.

### 2.2 Invariants
1. Every table must appear in the Manifest Table.
2. Every `local_id` must exist in the Local Domain Table.
3. General Tables cannot redefine structure.
4. Archetype Tables never store data values.
5. SAMRAS Tables define shape, not meaning.

### 2.3 System_id vs system_value
  **system_id**
    A domain‑typed identifier:
    - `taxonomy_id`
    - `msn_id`
    - `local_id`
    Identifiers are opaque, addressable, and authoritative.
  **system_value**
    A reducible value:
    - natural number
    - mass
    - timestamp
    - coordinate
    - currency
    Values may reduce to identifiers through tables or lists.

### 2.4 Ordered Lists and Reduction
Lists are first‑class tables.
A column may store:
- an ordinal (`system_value`)
Which reduces via:
- a list table
- to a `system_id`
This enables:
- families
- dependents
- suppliers
- peer groups
Without embedding identifiers directly.

### 2.5 Table Classes Overview
> MSS recognizes exactly **seven table classes**.

**Authority Boundaries**
| Table Class | Editable By |
|------------|-------------|
| MSS Profile | System Admin |
| Local Domain | Tenant |
| Manifest | Tenant |
| Archetype | Tenant |
| General | Tenant |
| SAMRAS | System Authority |
| SAMRAS Archetype | System Authority |

#### 2.5.1: MSS Profile Table
Defines the principal user and authority graph of the database.
**Characteristics**
- Single table per database.
- Contains one or more `msn_id` values.
- Declares:
  - primary authority
  - sub‑users
  - hierarchical relationships
  - permission scopes
**Access**
- Restricted to administrative actors only.
- Used to inform:
  - identity federation (e.g., Keycloak)
  - BFF/UI behavior
  - realm boundaries
This table anchors the system’s governance model.

#### 2.5.2: Local Domain Table
Defines all `local_id` values and their human‑readable titles.
**Characteristics**
- One row per `local_id`.
- Exactly two columns:
  - `local_id`
  - `title`
**Invariant**
All other tables reference `local_id` here.
Titles are never duplicated elsewhere.

#### 2.5.3: Manifest Table
Defines how tables are interpreted.
**Characteristics**
- Each row binds:
  - a table (`local_id`)
  - an archetype (`local_id`)
**Role**
- Declares which archetype governs which table.
- Controls how many rows an archetype table contains.
- Acts as the schema dispatcher.
No data table is interpreted without a manifest entry.

#### 2.5.4: Archetype Tables
Define structural templates.
**Characteristics**
- One column only.
- Each row contains a `local_id`.
- Row count is dictated by the manifest.
**Meaning**
- Each row corresponds to a position or slot.
- These slots are applied to General Tables.
Archetype tables do not store data; they define structure.

#### 2.5.5: General Tables
Store actual data values.
**Naming Convention**
```
<msn_id><local_id>
```
**Characteristics**
- Columns constrained by `system_value` or `system_id` types.
- Interpretation is entirely driven by:
  - the Archetype Table
  - the Manifest Table
General tables never self‑define their schema semantics.

#### 2.5.6: SAMRAS Tables
Specialized tables that implement a shape‑addressed address space.
**Characteristics**
- Store count‑streams, traversal rules, and layout versions.
- Only required when a new namespace is introduced.
- Currently applicable only to the controlling organization.
These tables are structural authorities, not semantic ones.

#### 2.5.7: SAMRAS Archetype Tables
Archetype tables specific to SAMRAS structures.
**Role**
- Define valid reference modes.
- Constrain how SAMRAS addresses may be used in General Tables.
- Enforce shape‑aware semantics.

---

## 3.0 SAMRAS (Shape-Addressed Mixed‑Radix Address Space)

### 3.1 Purpose and Scope
SAMRAS defines a **shape‑addressed tree system** in which every node is addressable by a mixed‑radix, ordinal path.
The system is designed to:
- Preserve hierarchical structure without flattening.
- Allow deterministic navigation from a linear representation.
- Support sparse materialization of nodes.
- Remain agnostic to any single application domain (e.g., taxonomy, geography, organizational charts).
SAMRAS is a **structural addressing standard**, not a naming or semantic authority system.

### 3.2 Core Concepts

**Shape vs. Meaning**
SAMRAS separates:
- **Shape**: the branching structure of a hierarchy.
- **Meaning**: any labels, semantics, or interpretations attached to positions in that structure.
The shape is authoritative; meaning is layered on top.

**Address Space**
A SAMRAS address is a sequence of natural numbers:

```
a₁_a₂_a₃_…_aₙ
```
Each segment `aᵢ` is the **ordinal position** of a node among its siblings.
The radix at each position is **not fixed**; it is determined by the number of children of the parent node.
Hence, the system is **mixed‑radix**.

**Parent–Child Relationship**
Given an address:
```
A = a₁_a₂_…_aₙ
```
- Parent: `a₁_a₂_…_aₙ₋₁`
- Depth: `n`
- Sibling index: `aₙ`
No global lookup table is required to compute ancestry.

---
### 3.3 Canonical Shape Representation
**Count‑Stream Encoding**
The canonical representation of a SAMRAS hierarchy is a **count‑stream**:
- A linear list of natural numbers.
- Each number represents the number of children for a node.
- The traversal order is fixed and declared (e.g., breadth‑first, layer‑group‑iteration).
The count‑stream defines the entire valid address space.

**Determinism**
Given:
- a count‑stream,
- a traversal specification,
- and an ordinal allocation rule,

the validity of any address can be determined algorithmically.

### 3.4Allocation Rules
**Append‑Only Ordinal Allocation**
Children are assigned ordinals sequentially:
```
1, 2, 3, …, k
```
Adding a new child increments the parent’s child count and assigns `k+1`.
Existing addresses remain stable.

**Structural Validity**
An address is valid if and only if:
```
1 ≤ aᵢ ≤ child_count(prefixᵢ₋₁)
```
No semantic metadata is required to evaluate validity.

---
### 3.5 Sparse Materialization
**Ghost Positions**
SAMRAS allows **addressable positions** that have:
- no stored metadata,
- no name,
- no materialized record.
These positions are structurally real but semantically undefined.

**Existential Placeholders**
Addresses may include suffix markers (e.g., `0`) to represent:
- an **existential but unidentified descendant**,
- without asserting group membership or semantic identity.
These are reference semantics, not nodes.

### 3.6 Reference Semantics
A reference to a SAMRAS address must declare its intent:
- **exact** — refers to the node at that address.
- **group** — refers to the set represented by that node.
- **existential_descendant** — refers to one unknown member below that node.
Address syntax alone must not be relied upon to infer semantics.

### 3.7 Versioning and Evolution

**Shape Evolution**
The shape may evolve by:
- increasing child counts,
- adding deeper layers.
Existing addresses remain valid if allocation rules are append‑only.

**Versioned Layouts**
If reordering or reinterpretation is required, a new **layout version** must be published.
No silent remapping of addresses is permitted.

### 3.8 Canonical vs. Projected Representations
- **Canonical**: count‑stream + traversal spec.
- **Projected**: any derived table, index, or JSON tree.
Projections may be rebuilt; canonical shape may not be silently altered.

### 3.9 pplicability
SAMRAS is suitable for:
- biological classification
- geographic or administrative hierarchies
- organizational structures
- standard catalogs
- any system requiring stable, navigable hierarchical addresses

It is explicitly **not**:
- a naming system
- a semantic ontology
- a permissions model

### 3.10 Design Invariants
1. Shape is authoritative.
2. Addresses are ordinal, not semantic.
3. Meaning is layered, not embedded.
4. Evolution is explicit.
5. Linear representations must reconstruct the hierarchy losslessly.

---

