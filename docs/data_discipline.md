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
