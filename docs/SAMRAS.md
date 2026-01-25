
# SAMRAS — Shape-Addressed Mixed‑Radix Address Space

## 1. Purpose and Scope
SAMRAS defines a **shape‑addressed tree system** in which every node is addressable by a mixed‑radix, ordinal path.
The system is designed to:
- Preserve hierarchical structure without flattening.
- Allow deterministic navigation from a linear representation.
- Support sparse materialization of nodes.
- Remain agnostic to any single application domain (e.g., taxonomy, geography, organizational charts).

SAMRAS is a **structural addressing standard**, not a naming or semantic authority system.

---

## 2. Core Concepts

### 2.1 Shape vs. Meaning
SAMRAS separates:
- **Shape**: the branching structure of a hierarchy.
- **Meaning**: any labels, semantics, or interpretations attached to positions in that structure.

The shape is authoritative; meaning is layered on top.

### 2.2 Address Space
A SAMRAS address is a sequence of natural numbers:

```
a₁_a₂_a₃_…_aₙ
```

Each segment `aᵢ` is the **ordinal position** of a node among its siblings.

The radix at each position is **not fixed**; it is determined by the number of children of the parent node.
Hence, the system is **mixed‑radix**.

### 2.3 Parent–Child Relationship
Given an address:
```
A = a₁_a₂_…_aₙ
```
- Parent: `a₁_a₂_…_aₙ₋₁`
- Depth: `n`
- Sibling index: `aₙ`

No global lookup table is required to compute ancestry.

---

## 3. Canonical Shape Representation

### 3.1 Count‑Stream Encoding
The canonical representation of a SAMRAS hierarchy is a **count‑stream**:
- A linear list of natural numbers.
- Each number represents the number of children for a node.
- The traversal order is fixed and declared (e.g., breadth‑first, layer‑group‑iteration).

The count‑stream defines the entire valid address space.

### 3.2 Determinism
Given:
- a count‑stream,
- a traversal specification,
- and an ordinal allocation rule,

the validity of any address can be determined algorithmically.

---

## 4. Allocation Rules

### 4.1 Append‑Only Ordinal Allocation
Children are assigned ordinals sequentially:
```
1, 2, 3, …, k
```

Adding a new child increments the parent’s child count and assigns `k+1`.
Existing addresses remain stable.

### 4.2 Structural Validity
An address is valid if and only if:
```
1 ≤ aᵢ ≤ child_count(prefixᵢ₋₁)
```

No semantic metadata is required to evaluate validity.

---

## 5. Sparse Materialization

### 5.1 Ghost Positions
SAMRAS allows **addressable positions** that have:
- no stored metadata,
- no name,
- no materialized record.

These positions are structurally real but semantically undefined.

### 5.2 Existential Placeholders
Addresses may include suffix markers (e.g., `0`) to represent:
- an **existential but unidentified descendant**,
- without asserting group membership or semantic identity.

These are reference semantics, not nodes.

---

## 6. Reference Semantics

A reference to a SAMRAS address must declare its intent:
- **exact** — refers to the node at that address.
- **group** — refers to the set represented by that node.
- **existential_descendant** — refers to one unknown member below that node.

Address syntax alone must not be relied upon to infer semantics.

---

## 7. Versioning and Evolution

### 7.1 Shape Evolution
The shape may evolve by:
- increasing child counts,
- adding deeper layers.

Existing addresses remain valid if allocation rules are append‑only.

### 7.2 Versioned Layouts
If reordering or reinterpretation is required, a new **layout version** must be published.
No silent remapping of addresses is permitted.

---

## 8. Canonical vs. Projected Representations

- **Canonical**: count‑stream + traversal spec.
- **Projected**: any derived table, index, or JSON tree.

Projections may be rebuilt; canonical shape may not be silently altered.

---

## 9. Applicability
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

---

## 10. Design Invariants
1. Shape is authoritative.
2. Addresses are ordinal, not semantic.
3. Meaning is layered, not embedded.
4. Evolution is explicit.
5. Linear representations must reconstruct the hierarchy losslessly.
