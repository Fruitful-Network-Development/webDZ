# Data Discipline (MSS)

## Overview

MSS (Mycilial Structured Schema) is the platform's data discipline. It defines
table classes, authority boundaries, and an interpretive model where tables are
shaped by manifests and archetypes rather than self-describing schemas.

Core table classes:

- **MSS profile table**: A single table per database containing one or more
  `msn_id` values; it defines primary authority, sub-users, and hierarchical
  relationships. Only system administrators can edit this table. The BFF uses it
  to map Keycloak identities to a canonical `msn_id` and determine UI behavior.
- **Local domain table**: Contains every `local_id` and its human-readable title.
- **Manifest table**: Binds each table (`local_id`) to an archetype (`local_id`),
  declaring which archetype governs which table.
- **General tables**: Named `<msn_id><local_id>` and store actual data; structure
  is dictated by the manifest and archetype tables. They must not self-define
  schema semantics.
- **SAMRAS tables**: Store count-streams and traversal rules; used to validate
  hierarchical addresses.

These structures establish authority boundaries and deterministic interpretation
of data. They require the platform schema (created via migrations) and initial
seeding of the MSS profile.

```mermaid
erDiagram
  %% ============================================================
  %% 7 TABLE TYPES (MSS) — ERD VIEW
  %% Example: legal_entity + natural_entity
  %% ============================================================

  %% ---------------------------
  %% (1) MSS Profile Table
  %% ---------------------------
  MSS_PROFILE {
    uuid user_id PK "Keycloak principal (UUID)"
    text msn_id "SAMRAS/MSN entity id (TEXT)"
    text parent_msn_id "Hierarchy parent (TEXT)"
    text display_name
    text role "legacy string; prefer role_assignment table"
    timestamptz created_at
    timestamptz updated_at
  }

  %% ---------------------------
  %% (2) Local Domain Table
  %% "All local_id titles live here"
  %% ---------------------------
  LOCAL_DOMAIN {
    uuid local_id PK
    text title
  }

  %% ---------------------------
  %% (3) Manifest Table
  %% binds a local table id to an archetype
  %% ---------------------------
  MANIFEST {
    uuid table_id PK "local_id of the table name"
    text tenant_id
    uuid archetype_id FK
  }

  %% ---------------------------
  %% (4) Archetype Tables (lists of row-local_ids)
  %% For each archetype, define which local_ids are valid rows
  %% NOTE: physically this may be a provisioned table per archetype
  %% or a generic table keyed by archetype_id.
  %% ---------------------------
  ARCHETYPE_ROWSET {
    uuid archetype_id FK
    int  position "row ordinal"
    uuid row_local_id FK "local_id that names the row/entity"
  }

  %% ---------------------------
  %% (5) General Tables
  %% provisioned, per tenant: <msn_id><table_local_id>
  %% records store canonical nested JSON as JSONB
  %% ---------------------------
  GENERAL_TABLE_REGISTRY {
    uuid id PK
    text tenant_id
    uuid table_local_id FK "points to LOCAL_DOMAIN local_id"
    text mode "general|samras|..."
    boolean is_enabled
    timestamptz created_at
  }

  GENERAL_RECORD {
    uuid id PK
    text tenant_id
    uuid table_local_id FK
    jsonb data "canonical nested JSON payload"
    timestamptz created_at
    timestamptz updated_at
  }

  %% ---------------------------
  %% (6) SAMRAS Tables
  %% domain layouts/count-streams; validates SAMRAS addresses
  %% ---------------------------
  SAMRAS_LAYOUT {
    text domain PK
    int  version PK
    bytea count_stream
    jsonb traversal_spec
  }

  %% ---------------------------
  %% (7) SAMRAS Archetype Tables
  %% archetypes for SAMRAS domains + allowed modes
  %% ---------------------------
  SAMRAS_ARCHETYPE {
    uuid id PK
    text domain
    text[] allowed_modes
    text description
  }

  %% ---------------------------
  %% Archetype definitions (core registry)
  %% ---------------------------
  ARCHETYPE {
    uuid id PK
    text tenant_id
    text name "e.g. legal_entity | natural_entity"
    int version
    timestamptz created_at
  }

  ARCHETYPE_FIELD {
    uuid archetype_id FK
    int position
    text name
    text type "system_value|system_id|text|json|array[...]"
    text ref_domain "local|msn|taxonomy|samras:msn|..."
    jsonb constraints
  }

  %% ------------------------------------------------------------
  %% RELATIONSHIPS
  %% ------------------------------------------------------------

  %% MSS profile informs which msn_id "owns" the local namespace
  %% and drives table name prefixing + console scoping
  MSS_PROFILE ||--o{ GENERAL_TABLE_REGISTRY : "owner msn_id scopes"
  MSS_PROFILE ||--o{ GENERAL_RECORD : "author/actor via session msn_id"

  %% Local Domain is the naming layer for local identifiers
  LOCAL_DOMAIN ||--o{ MANIFEST : "table_id (local_id)"
  LOCAL_DOMAIN ||--o{ GENERAL_TABLE_REGISTRY : "table_local_id"
  LOCAL_DOMAIN ||--o{ GENERAL_RECORD : "table_local_id"
  LOCAL_DOMAIN ||--o{ ARCHETYPE_ROWSET : "row_local_id"

  %% Archetype registry + fields
  ARCHETYPE ||--o{ ARCHETYPE_FIELD : "defines fields"
  ARCHETYPE ||--o{ ARCHETYPE_ROWSET : "row membership"
  ARCHETYPE ||--o{ MANIFEST : "bound by"

  %% Manifest binds a provisioned general table to an archetype
  MANIFEST }o--|| ARCHETYPE : "archetype_id"

  %% SAMRAS constraints used by archetype fields & validation
  SAMRAS_LAYOUT ||--o{ SAMRAS_ARCHETYPE : "domain policies"

  %% ============================================================
  %% EXAMPLE INSTANTIATION (conceptual notes)
  %% ============================================================
  %% - LOCAL_DOMAIN contains local_ids for:
  %%   "legal_entity" table name, "natural_entity" table name,
  %%   row titles like "Cuyahoga Valley Countryside Conservancy",
  %%   "Marilyn Wotowiec", etc.
  %%
  %% - ARCHETYPE rows:
  %%   ARCHETYPE(name="legal_entity") + fields like:
  %%     msn_id (system_id ref_domain="msn")
  %%     local_id (system_id ref_domain="local")
  %%     aliases (array[text])
  %%     meta (json)
  %%
  %%   ARCHETYPE(name="natural_entity") + similar fields.
  %%
  %% - ARCHETYPE_ROWSET lists which row_local_id values are valid
  %%   entities for each archetype (your "archetype table" concept).
  %%
  %% - MANIFEST binds:
  %%   table_id=<local_id for 'legal_entity_table'> -> archetype_id (legal_entity)
  %%   table_id=<local_id for 'natural_entity_table'> -> archetype_id (natural_entity)
  %%
  %% - GENERAL_TABLE_REGISTRY provisions each table for tenant_id.
  %% - GENERAL_RECORD stores each entity instance as JSONB.
  %%
  %% - SAMRAS_LAYOUT + SAMRAS_ARCHETYPE validate msn_id/taxa_id
  %%   fields when ref_domain is samras-based.
```

## Schema as data

The platform treats **schemas themselves as data**.

This means:

- Users define groupings and fields through the UI.
- Definitions are persisted and versionable.
- Operational data must conform to the active definitions.

The BFF:

- Validates all writes against current definitions.
- Mediates references across domains (e.g., ID-based linkage).
- Does not permit arbitrary or implicit structure changes.

No assumption is made here about:

- Exact storage format
- Relational vs document representation
- Final migration path from filesystem to database

## Mutating operations (strict)

The BFF may perform mutating actions **only when all conditions are met**:

- Explicit scope
- Authorization verified
- Inputs validated
- Operation auditable
- Tenant boundaries enforced

Allowed categories:

- Identity and membership management (via Keycloak APIs)
- Schema definition and update (within tenant scope)
- Data creation and update conforming to schema
- Controlled content promotion workflows

Explicitly excluded:

- Infrastructure modification
- Arbitrary command execution
- Direct filesystem or service manipulation outside defined workflows

## Unifying the data and the BFF

The unified stack harmonizes identity management, schema discipline, and
hierarchical addressing into a consistent architecture:

- **BFF** ensures secure and centralized authentication and serves UI surfaces.
- **MSS** structures data tables declaratively and enforces type and authority
  boundaries.
- **SAMRAS** provides a principled way to address hierarchical data without
  embedding meaning into identifiers.

Together, these components enable multi-tenant applications where users define
their own schemas, link to global domains like taxonomies, and interact with
data through dynamic UIs while maintaining strong governance and extensibility.

### Identity resolution and user hierarchy

The **MSS Profile table** provides the bridge between Keycloak and the
platform's own identity model. When a user logs in via the BFF, the BFF uses the
Keycloak user ID to look up or create an entry in `platform.mss_profile`. The
entry records the user's `msn_id`, sub-users, and hierarchical relationships.
This defines a unified user hierarchy that the BFF consults to decide how to
render the UI and what operations are permitted. Because the MSS Profile table
is under administrative control, tenants cannot rearrange identities.

### Dynamic schemas and UIs

Tenants define new tables and fields via the admin console:

1. **Create or select a Local Domain entry**: register a `local_id` and title.
2. **Define an Archetype**: declare fields, types (`system_id` or `system_value`),
   reference domains, and constraints.
3. **Bind via the Manifest Table**: link the table's `local_id` with its
   archetype's `local_id` and declare the archetype row count.

When a user visits the tenant console, the BFF reads the manifest and archetype
tables to build dynamic UI forms. Data values are validated against these
definitions before writes are allowed.

### Linking data across domains

If a field references the `taxonomy` domain, it stores a SAMRAS address rather
than a string. The SAMRAS archetype table ensures reference semantics (exact,
group, existential). The BFF validates the address against the correct layout
version in the SAMRAS table.

For fields that use lists (e.g., `dependents`, `suppliers`), the stored value is
an ordinal (`system_value`) that reduces to an `msn_id` via a local list table.
This pattern ensures references are explicit and type-checked.

### Authority enforcement

Because all data access goes through the BFF, it can enforce MSS authority
rules. Tenants can create and modify their own local domain, manifest,
archetype, and general tables, while only system administrators can modify the
MSS profile, SAMRAS, and SAMRAS archetype tables. Mutations are logged by the
application for auditability.

### Data evolution and migration

When a tenant edits an archetype, the platform increments the archetype version.
Existing data remains tied to its previous archetype version. The BFF may
provide tooling to migrate records explicitly by transforming them to conform to
the new archetype.

If a SAMRAS layout changes beyond append-only growth, the system publishes a new
layout version and general tables reference the appropriate version.

### Extensibility and separation of concerns

This unified stack deliberately separates concerns:

- **Authentication and Authorization**: handled by Keycloak and the BFF.
- **Schema Definition and Interpretation**: handled by MSS tables. The data model
  is declarative and extensible.
- **Hierarchical Structure**: handled by SAMRAS tables. Shape and meaning are
  separate and versioned.
- **Data Storage**: handled by general tables in Postgres. The storage format
  remains nested JSON at the canonical level and can be projected to relational
  tables for indexing or performance.

By adhering to these boundaries, the platform can evolve without disrupting
existing data or clients.

## Manifest-Structured Schema (MSS)

MSS organizes all tables into seven **table classes** to ensure schema
consistency, authority separation, and lossless nested structure.

**system_id vs. system_value**

- **system_id**: An opaque, domain-typed identifier such as `taxonomy_id`,
  `msn_id` (mixed-space number for people/orgs), or `local_id`. These IDs are
  authoritative and globally unique within their domain.
- **system_value**: A primitive value (natural number, mass, timestamp,
  coordinate, currency) that may reduce to an identifier via a lookup list.

### Table classes

1. **MSS Profile Table**: A single table per database that defines the principal
   user(s), their `msn_id`, sub-users, hierarchical relations, and permission
   scopes. This anchors governance; only system administrators can modify it.
2. **Local Domain Table**: Holds every `local_id` and its title. Titles are
   stored only here; other tables reference `local_id` values.
3. **Manifest Table**: Associates a table (`local_id`) with the archetype
   (`local_id`) that governs it. Determines which archetype applies to each
   general table.
4. **Archetype Tables**: Contain one column of `local_id` values. Row count is
   dictated by the manifest. These tables define structure, not data.
5. **General Tables**: Hold actual data values. Names are formed by
   `<msn_id><local_id>`. Columns are typed as `system_value` or `system_id` and
   interpreted by archetype and manifest tables.
6. **SAMRAS Tables**: Specialized tables used when a new namespace employs
   shape-addressed hierarchy. They store count-streams, traversal specifications,
   and layout versions.
7. **SAMRAS Archetype Tables**: Define valid reference modes (exact, group,
   existential) for SAMRAS addresses.

### Authority boundaries

- **System administrators** manage the MSS Profile, SAMRAS, and SAMRAS
  archetype tables.
- **Tenants** manage local domains, manifests, archetypes, and general tables
  within their scope.

### Invariants

1. Every table must appear in the Manifest Table.
2. Every `local_id` must exist in the Local Domain Table.
3. General tables cannot redefine structure.
4. Archetype tables never store data values.
5. SAMRAS tables define shape, not meaning.

## Ordered lists and reduction

Lists are first-class tables. A column may store an ordinal (`system_value`)
which reduces via a list table to a `system_id`. This enables families,
dependents, suppliers, and peer groups without embedding identifiers directly.

## SAMRAS (Shape-Addressed Mixed-Radix Address Space)

### Purpose and scope

SAMRAS defines a **shape-addressed tree system** in which every node is
addressable by a mixed-radix ordinal path. The system is designed to:

- Preserve hierarchical structure without flattening
- Allow deterministic navigation from a linear representation
- Support sparse materialization of nodes
- Remain agnostic to any single application domain (e.g., taxonomy, geography,
  organizational charts)

SAMRAS is a **structural addressing standard**, not a naming or semantic
authority system.

### Core concepts

**Shape vs. meaning**

SAMRAS separates:

- **Shape**: the branching structure of a hierarchy
- **Meaning**: labels, semantics, or interpretations attached to positions

The shape is authoritative; meaning is layered on top.

**Address space**

A SAMRAS address is a sequence of natural numbers:

```
a1_a2_a3_..._an
```

Each segment `ai` is the ordinal position of a node among its siblings. The
radix at each position is not fixed; it is determined by the number of children
of the parent node. Hence, the system is mixed-radix.

**Parent-child relationship**

Given an address:

```
A = a1_a2_..._an
```

- Parent: `a1_a2_..._a(n-1)`
- Depth: `n`
- Sibling index: `an`

No global lookup table is required to compute ancestry.

### Canonical shape representation

**Count-stream encoding**

The canonical representation of a SAMRAS hierarchy is a **count-stream**:

- A linear list of natural numbers
- Each number represents the number of children for a node
- The traversal order is fixed and declared (e.g., breadth-first,
  layer-group-iteration)

The count-stream defines the entire valid address space.

**Determinism**

Given:

- a count-stream,
- a traversal specification,
- and an ordinal allocation rule,

the validity of any address can be determined algorithmically.

### Allocation rules

**Append-only ordinal allocation**

Children are assigned ordinals sequentially:

```
1, 2, 3, ..., k
```

Adding a new child increments the parent's child count and assigns `k+1`.
Existing addresses remain stable.

**Structural validity**

An address is valid if and only if:

```
1 <= ai <= child_count(prefix(i-1))
```

No semantic metadata is required to evaluate validity.

### Sparse materialization

**Ghost positions**

SAMRAS allows addressable positions that have:

- no stored metadata
- no name
- no materialized record

These positions are structurally real but semantically undefined.

**Existential placeholders**

Addresses may include suffix markers (e.g., `0`) to represent:

- an existential but unidentified descendant

These are reference semantics, not nodes.

### Reference semantics

A reference to a SAMRAS address must declare its intent:

- **exact**: refers to the node at that address
- **group**: refers to the set represented by that node
- **existential**: refers to one unknown member below that node

Address syntax alone must not be relied upon to infer semantics.

### Versioning and evolution

**Shape evolution**

The shape may evolve by:

- increasing child counts
- adding deeper layers

Existing addresses remain valid if allocation rules are append-only.

**Versioned layouts**

If reordering or reinterpretation is required, a new layout version must be
published. No silent remapping of addresses is permitted.

### Canonical vs. projected representations

- **Canonical**: count-stream + traversal spec
- **Projected**: any derived table, index, or JSON tree

Projections may be rebuilt; canonical shape may not be silently altered.

### Applicability

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

### Design invariants

1. Shape is authoritative.
2. Addresses are ordinal, not semantic.
3. Meaning is layered, not embedded.
4. Evolution is explicit.
5. Linear representations must reconstruct the hierarchy losslessly.
