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
