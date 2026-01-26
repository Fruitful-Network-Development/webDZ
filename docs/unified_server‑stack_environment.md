# Unified Server-Stack Environment

* **BFF** defines how the platform authenticates and authorizes users, routes them to the appropriate tenant context, and exposes the admin and user consoles. It guarantees that client applications remain stateless and never touch sensitive credentials.
* **MSS** specifies how data tables are structured and interpreted. It introduces a discipline of *manifest-driven tables* where identifiers and values are type-scoped and table structure is declared, not implicit. MSS is agnostic to the storage backend and provides a clear separation between *schema*, *data* and *authority*.
* **SAMRAS** defines a domain-independent addressing scheme for hierarchical structures. It supplies a canonical *shape* and a method to navigate mixed-radix addresses such as taxonomic trees or geographic hierarchies without flattening the tree.

These components jointly enable a platform that supports multiple tenants, nested JSON as the canonical data source, dynamic schemas authored by tenants, and referential integrity across global and local domains.

## Platform Architecture

The server stack is composed of **Keycloak**, **Flask BFF**, and **PostgreSQL**, deployed via Docker Compose under the `/srv/compose/platform` directory. NGINX remains on the host to terminate TLS and proxy traffic `github.com`. Client sites are static and are served directly from the filesystem `github.com`.
1.  **Keycloak** – The single identity provider (IdP) for all users. It handles login, multi-factor authentication and credential management. The platform never exposes Keycloak tokens directly to browsers `github.com`.
2.  **Flask BFF** – A platform-owned backend-for-frontend that initiates OpenID Connect (OIDC) flows, exchanges codes with Keycloak on the server side, enforces tenant boundaries, and holds the user's session state in a secure cookie `github.com`. It serves both the admin console and the user console `github.com`.
3.  **PostgreSQL** – Holds the platform schema (`platform`), storing identity resolution (`platform.user_profiles`) and audit logs `github.com`. Keycloak uses its own separate database `github.com`.

### Multi-Tenant Routing and Identity
- All authentication starts at the BFF via an endpoint such as `/login?tenant=<tenant_id>&return_to=<url>`. The BFF determines tenant context from the query parameter, user membership, and platform policies. It then redirects to Keycloak for login and receives an authorization code `github.com`. After exchanging the code, the BFF sets a session cookie scoped to `api.<domain>`. Clients never receive tokens.
- Each tenant is represented as its own OIDC client in Keycloak `github.com`. Tenant isolation is logical; there is a single BFF instance and a single Keycloak realm. The BFF uses Keycloak roles together with platform rules to decide which tenants and UI modules a user may access.

### Structured UI Outline

#### Admin Console Root
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

#### Component Hierarchy (Conceptual)
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

## 3. Data Discipline

### Overview of the MSS & SAMRAS requirements
* **MSS profile table:** A single table per database containing one or more `msn_id` values; it defines the primary authority, sub-users and hierarchical relationships `github.com`. Only system administrators can edit this table. BFF uses it to map Keycloak identities to a canonical `msn_id`, determine sub-user scopes and influence UI behaviour.
* **Local domain table:** Contains every `local_id` and its human-readable title `github.com`. All tables reference `local_id` here.
* **Manifest table:** Binds each table (`local_id`) to an archetype (`local_id`) `github.com`, declaring which archetype governs which table.
* **General tables:** Named `<msn_id><local_id>` and store actual data; structure is dictated by the manifest and archetype tables `github.com`. They must not self-define schema semantics.
* **SAMRAS tables:** Store count-streams and traversal rules; used to validate hierarchical addresses `github.com`.

These structures establish authority boundaries and deterministic interpretation of data. They require a dedicated schema (created via migrations) and environment variables for DB connection, plus initial seeding of the MSS profile. 

> The SAMRAS specification is domain-agnostic. In the Fruitful Network context, it is used for the **taxonomic domain**, the **statonomic domain**, and any hierarchical namespaces like geographic divisions. However, the same addressing rules apply whether the domain is biology, geography or organizational structure.

#### Manifest-Structured Schema (MSS)
MSS organizes all tables into seven **table classes** to ensure schema consistency, authority separation, and lossless nested structure.
**system_id vs. system_value**
* **system_id** – An opaque, domain-typed identifier such as `taxonomy_id`, `msn_id` (mixed-space number for people/orgs), or `local_id`. These IDs are authoritative and globally unique within their domain.
* **system_value** – A primitive value (natural number, mass, timestamp, coordinate, currency) that may *reduce* to an identifier via a lookup list. For example, the `dependents` column may store an ordinal whose meaning comes from a dependents list; resolving the ordinal yields the corresponding `msn_id`.
**Table Classes**
1.  **MSS Profile Table** – A single table per database that defines the principal user(s) of the database, their `msn_id`, sub-users, hierarchical relations, and permission scopes. This table anchors governance: only system administrators can modify it. In the unified environment, this table becomes the backbone for managing client UIs and their user hierarchies. It maps Keycloak user identities to the platform's own `msn_id` and defines which sub-users exist and what permissions they have.
2.  **Local Domain Table** – Holds every `local_id` and its title. It functions as the dictionary of tenant-scoped terms. Titles are stored only here; other tables reference `local_id` values to avoid duplication.
3.  **Manifest Table** – Associates a table (`local_id`) with the archetype (`local_id`) that governs it. This table determines how many rows an archetype table has and which archetype applies to each general table.
4.  **Archetype Tables** – Contain one column of `local_id` values; the number of rows is dictated by the manifest. They describe the *structure* (fields, references, constraints) of a data table but store no data themselves.
5.  **General Tables** – Hold actual data values. Their names are formed by concatenating the user's `msn_id` with a `local_id` describing the table. Columns are typed either as `system_value` or `system_id` and may reference lists or SAMRAS addresses. The manifest and archetype tables determine which columns exist and how they should be interpreted.
6.  **SAMRAS Tables** – Specialized tables used when a new namespace employs shape-addressed hierarchy. They store the count-stream, traversal specification and layout version for a SAMRAS domain.
7.  **SAMRAS Archetype Tables** – Define valid reference modes (exact, group, existential descendant) for SAMRAS addresses. These constrain how SAMRAS addresses may be used in general tables.

**Authority Boundaries**
Authority over each table class is enforced to protect system integrity:
* **System administrators** manage the MSS Profile, SAMRAS and SAMRAS archetype tables.
* **Tenants** manage local domains, manifests, archetypes, and general tables within their scope.

**Hierarchical Addressing: SAMRAS**
SAMRAS provides a domain-independent way to address nodes in hierarchical structures using mixed-radix ordinals.

**Shape vs. Meaning**
SAMRAS cleanly separates the *shape* of a hierarchy from any semantic labels attached to nodes. The shape is authoritative and is represented as a count-stream—a list of natural numbers where each number specifies the number of children for a node .

**Address Space**
A SAMRAS address is written as `a1_a2_..._an`, where each `ai` is the ordinal position among siblings. There is no fixed radix; the maximum allowed value of each `ai` is determined by the parent's child count. Parent addresses are obtained by dropping the last segment. Children are allocated sequentially in append-only fashion so existing addresses never change.
Not every address has to be materialized. SAMRAS allows **ghost positions**—addressable slots that lack any attached metadata. References may also include existential placeholders (suffix segments of `0`) to indicate an unknown descendant rather than a specific node. Because SAMRAS is a structural addressing scheme, reference semantics (exact, group, existential descendant) must be declared explicitly when using an address.

**Versioning**
If reordering is needed or if the shape evolves in non-append ways, a new layout version must be published. Existing addresses remain valid under their layout version; no silent remapping is permitted. SAMRAS tables in MSS store these layout versions and the count-streams that define them.

---

### Unifying the Data and BFF

The **Unified Server-Stack Environment** harmonizes identity management, schema discipline and hierarchical addressing into a consistent architecture. **BFF** ensures secure and centralized authentication and serves UI surfaces. **MSS** structures data tables declaratively and enforces type and authority boundaries. **SAMRAS** provides a principled way to address hierarchical data without embedding meaning into identifiers. Together, these components enable multi-tenant applications where users can define their own schemas, link to global domains like taxonomies, and interact with data through dynamic UIs, all while maintaining strong governance and extensibility.

#### Identity Resolution and User Hierarchy
The **MSS Profile table** provides the bridge between Keycloak and the platform's own identity model. When a user logs in via the BFF, the BFF uses Keycloak's user ID to look up or create an entry in the `platform.user_profiles` table and the MSS Profile table. The MSS profile entry records the user's `msn_id`, sub-users, and hierarchical relationships. In effect, this table defines a unified *user hierarchy* that the BFF consults to decide how to render the UI and what operations are permitted. Because the MSS Profile table is under administrative control, tenants cannot impersonate or rearrange identities.

#### Dynamic Schemas and UIs
Tenants define new tables and fields via the admin console. The process is:
1.  **Create or select a Local Domain entry** – The tenant registers a new `local_id` and title for the table.
2.  **Define an Archetype** – The tenant uses a wizard to define fields, their types (`system_id` or `system_value`), reference domains (e.g., `taxonomy`, `msn`, `local`), and constraints. This becomes an archetype table.
3.  **Bind via the Manifest Table** – A manifest record links the table's `local_id` with its archetype's `local_id` and determines how many rows the archetype table should have.
When a user visits the user console, the BFF reads the manifest and archetype tables to build dynamic UI forms. Because the tables themselves do not encode their schema, the BFF can render any general table by consulting the manifest and archetype definitions. Data values are validated against these definitions before writes are allowed.

#### Linking Data Across Domains
If a field references the `taxonomy` domain, it stores a SAMRAS address rather than a string. The SAMRAS archetype table ensures the reference semantics (exact, group, existential descendant) are respected. The BFF validates the address against the correct layout version in the SAMRAS table. For fields that use lists (e.g., `dependents`, `suppliers`), the stored value is an ordinal (`system_value`) that reduces to an `msn_id` via a local list table. This pattern ensures that references are explicit and type-checked.

#### Authority Enforcement
Because all data access goes through the BFF, it can enforce MSS authority rules. The BFF ensures that tenants can create and modify their own local domain, manifest, archetype and general tables, while only system administrators can modify the MSS profile, SAMRAS, and SAMRAS archetype tables. Audit events are recorded in `platform.audit_log` for each mutation.

#### Data Evolution and Migration
When a tenant edits an archetype, the platform increments the archetype version. Existing data remains tied to its previous archetype version. The BFF may provide tooling to migrate records explicitly by transforming them to conform to the new archetype. Similarly, if a SAMRAS layout changes beyond append-only growth, the system publishes a new layout version and general tables reference the appropriate version.

#### Extensibility and Separation of Concerns
This unified stack deliberately separates concerns:
* **Authentication and Authorization** – handled by Keycloak and the BFF.
* **Schema Definition and Interpretation** – handled by MSS tables. The data model is declarative and extensible.
* **Hierarchical Structure** – handled by SAMRAS tables. Shape and meaning are separate and versioned.
* **Data Storage** – handled by general tables in Postgres. The storage format remains nested JSON at the canonical level and can be projected to relational tables for indexing or performance.
By adhering to these boundaries, the platform can evolve without disrupting existing data or clients.

---
