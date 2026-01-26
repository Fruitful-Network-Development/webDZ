# SAMRAS (Shape-Addressed Mixed-Radix Address Space)

## Purpose and scope

SAMRAS defines a **shape-addressed tree system** in which every node is
addressable by a mixed-radix ordinal path. The system is designed to:

- Preserve hierarchical structure without flattening
- Allow deterministic navigation from a linear representation
- Support sparse materialization of nodes
- Remain agnostic to any single application domain (e.g., taxonomy, geography,
  organizational charts)

SAMRAS is a **structural addressing standard**, not a naming or semantic
authority system.

## Core concepts

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

## Canonical shape representation

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

## Allocation rules

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

## Sparse materialization

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

## Reference semantics

A reference to a SAMRAS address must declare its intent:

- **exact**: refers to the node at that address
- **group**: refers to the set represented by that node
- **existential**: refers to one unknown member below that node

Address syntax alone must not be relied upon to infer semantics.

## Versioning and evolution

**Shape evolution**

The shape may evolve by:

- increasing child counts
- adding deeper layers

Existing addresses remain valid if allocation rules are append-only.

**Versioned layouts**

If reordering or reinterpretation is required, a new layout version must be
published. No silent remapping of addresses is permitted.

## Canonical vs. projected representations

- **Canonical**: count-stream + traversal spec
- **Projected**: any derived table, index, or JSON tree

Projections may be rebuilt; canonical shape may not be silently altered.

## Applicability

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

## Design invariants

1. Shape is authoritative.
2. Addresses are ordinal, not semantic.
3. Meaning is layered, not embedded.
4. Evolution is explicit.
5. Linear representations must reconstruct the hierarchy losslessly.
