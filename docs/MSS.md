
# BFF
## CORE CONSOLE DESIGN
> Core is what must remain stable for every tenant and every module. It is your operating system. Core contract: modules plug into the shell; the shell does not embed business logic.

### IDENTITY + TENANCY
* Tenant selection and routing (tenant_registry, allowed_return_to, /t/<tenant>/…)
* Session/auth integration (Keycloak/OIDC)
* Authorization primitives (root-admin vs tenant-admin vs tenant-user)
* Provisioning gate (“not provisioned” via MSS profile)
> **Core contract**: every request has a resolved tenant context + user context or a deterministic error/redirect.

### DATA CONTORL PLANE (MSS)
> Omits serving static client frontends or controlling infrastructure services `github.com`. It is a *control plane* for identity and data access; external business logic must call through the BFF to reach the data.

### RUN TIME DATA PLANE 

#### PLATFORM DATA
  *shaping the space, not filling it.*
Tables:
  - Registry-backed
  - Archetype-validated
  - Not tenant-scoped unless explicitly bound
Lists:
  - Ordered references (not categories)
  - Used to resolve ordinals and structural linkage

#### GENERIC CRUD

### UI SHELL

## MODUELS
### PLATFORM MODUELS
> A platform module is a reusable capability that many tenants might use, but that is not required for the platform to function.
> Platform module contract: it uses core identity + data contracts; it does not redefine them.
### TENANT MODUELS
> Tenant modules are the use cases for a specific type of tenant. They’re often thin UI + workflows on top of core + platform modules.
> Tenant modules differ from platform modules because they are not universally reusable. They can still be built using the same core + platform components.

# MSS

MSS defines a **table‑level schema discipline** for systems where:
- nested structure is canonical,
- identifiers are domain‑typed (`system_id`),
- values are reducible (`system_value`),
- and tables derive meaning from manifests rather than intrinsic schemas.
MSS is designed to work with SAMRAS, but does not depend on it.

**Core Principles**
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

**Invariants**
1. Every table must appear in the Manifest Table.
2. Every `local_id` must exist in the Local Domain Table.
3. General Tables cannot redefine structure.
4. Archetype Tables never store data values.
5. SAMRAS Tables define shape, not meaning.

**System_id vs system_value**
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

**Ordered Lists and Reduction**
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

## Table Classes Overview
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

### 1.TABLE-TYPE: MSS Profile Table
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

### 2.TABLE-TYPE: Local Domain Table
Defines all `local_id` values and their human‑readable titles.
**Characteristics**
- One row per `local_id`.
- Exactly two columns:
  - `local_id`
  - `title`
**Invariant**
All other tables reference `local_id` here.
Titles are never duplicated elsewhere.

### 3.TABLE-TYPE: Manifest Table
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

### 4.TABLE-TYPE: Archetype Tables
Define structural templates.
**Characteristics**
- One column only.
- Each row contains a `local_id`.
- Row count is dictated by the manifest.
**Meaning**
- Each row corresponds to a position or slot.
- These slots are applied to General Tables.
Archetype tables do not store data; they define structure.

### 5.TABLE-TYPE: General Tables
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

### 6.TABLE-TYPE: SAMRAS Tables
Specialized tables that implement a shape‑addressed address space.
**Characteristics**
- Store count‑streams, traversal rules, and layout versions.
- Only required when a new namespace is introduced.
- Currently applicable only to the controlling organization.
These tables are structural authorities, not semantic ones.

### 7.TABLE-TYPE: SAMRAS Archetype Tables
Archetype tables specific to SAMRAS structures.
**Role**
- Define valid reference modes.
- Constrain how SAMRAS addresses may be used in General Tables.
- Enforce shape‑aware semantics.

---

