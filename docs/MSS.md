
# MSS — Manifest‑Structured Schema

## 1. Purpose
MSS defines a **table‑level schema discipline** for systems where:
- nested structure is canonical,
- identifiers are domain‑typed (`system_id`),
- values are reducible (`system_value`),
- and tables derive meaning from manifests rather than intrinsic schemas.

MSS is designed to work with SAMRAS, but does not depend on it.

---

## 2. Core Principles

1. **Tables are interpreted, not self‑describing**
2. **Identifiers are domain‑scoped**
3. **Values reduce to identifiers**
4. **Structure is declared once, reused many times**
5. **Authority boundaries are enforced by table class**

---

## 3. Table Classes Overview

MSS recognizes exactly **seven table classes**.

### 3.1 MSS Profile Table
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

---

### 3.2 Local Domain Table
Defines all `local_id` values and their human‑readable titles.

**Characteristics**
- One row per `local_id`.
- Exactly two columns:
  - `local_id`
  - `title`

**Invariant**
All other tables reference `local_id` here.
Titles are never duplicated elsewhere.

---

### 3.3 Manifest Table
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

---

### 3.4 Archetype Tables
Define structural templates.

**Characteristics**
- One column only.
- Each row contains a `local_id`.
- Row count is dictated by the manifest.

**Meaning**
- Each row corresponds to a position or slot.
- These slots are applied to General Tables.

Archetype tables do not store data; they define structure.

---

### 3.5 General Tables
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

---

### 3.6 SAMRAS Tables
Specialized tables that implement a shape‑addressed address space.

**Characteristics**
- Store count‑streams, traversal rules, and layout versions.
- Only required when a new namespace is introduced.
- Currently applicable only to the controlling organization.

These tables are structural authorities, not semantic ones.

---

### 3.7 SAMRAS Archetype Tables
Archetype tables specific to SAMRAS structures.

**Role**
- Define valid reference modes.
- Constrain how SAMRAS addresses may be used in General Tables.
- Enforce shape‑aware semantics.

---

## 4. system_id vs system_value

### system_id
A domain‑typed identifier:
- `taxonomy_id`
- `msn_id`
- `local_id`

Identifiers are opaque, addressable, and authoritative.

### system_value
A reducible value:
- natural number
- mass
- timestamp
- coordinate
- currency

Values may reduce to identifiers through tables or lists.

---

## 5. Ordered Lists and Reduction

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

---

## 6. Authority Boundaries

| Table Class | Editable By |
|------------|-------------|
| MSS Profile | System Admin |
| Local Domain | Tenant |
| Manifest | Tenant |
| Archetype | Tenant |
| General | Tenant |
| SAMRAS | System Authority |
| SAMRAS Archetype | System Authority |

---

## 7. Invariants

1. Every table must appear in the Manifest Table.
2. Every `local_id` must exist in the Local Domain Table.
3. General Tables cannot redefine structure.
4. Archetype Tables never store data values.
5. SAMRAS Tables define shape, not meaning.

---

## 8. Intended Outcomes
MSS ensures:
- schema consistency without rigid schemas,
- lossless nesting,
- clear authority separation,
- extensibility without migration cascades,
- and deterministic interpretation of tables.

It is a schema discipline, not a database product.
