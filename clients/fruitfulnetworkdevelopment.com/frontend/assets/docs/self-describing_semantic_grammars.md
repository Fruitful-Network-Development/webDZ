# Self-Describing Semantic Grammars

A **self-describing semantic grammar** is a representation framework in which a data stream carries enough **structure**, **boundary rules**, and **semantic cues** for an independent system to identify meaningful units (objects, fields, groups) and interpret how those units relate—without relying on a separate, per-partner contract that predefines the full schema.

The concept is motivated by networks where the **information form cannot be pre-limited**: participating nodes evolve independently, new entities and relationships appear over time, and operational meaning is local unless it is made explicit.

---

## 1. Problem setting: when information form cannot be pre-limited

Many interoperability strategies assume that participants can converge on a fixed schema (or a small family of schemas). That assumption fails in settings with:

- **Independent evolution**: each node updates its internal model on its own schedule.
- **Open-ended structure**: new object types, new nesting, and new relationships appear over time.
- **Context-dependent meaning**: “the same field” can have different operational meaning across organizations.
- **Multi-tenant composition**: data objects must be merged and recombined across sources.

In this setting, a fixed “format contract” often solves only **transmission agreement** (how bytes parse into fields), not **operational interoperability** (how receivers query, validate, compose, and evolve meanings without bespoke glue).

---

## 2. Related approaches and how they differ

### 2.1 The Semantic Web (RDF/OWL/Linked Data)
The **Semantic Web** family (e.g., RDF triples, URIs, ontologies such as OWL, and Linked Data conventions) targets interoperability by:
- expressing statements as graph relations,
- using globally resolvable identifiers (URIs),
- and defining shared vocabularies/ontologies.

This improves cross-system *referencing* and *machine-readable semantics*, but it typically assumes that:
- participants adopt compatible vocabularies (or invest in ontology alignment),
- and graph statements are sufficient to capture the relevant operational structure.

A self-describing semantic grammar is **orthogonal** to this goal. It focuses on:
- making **structural boundaries and composable addressing** explicit,
- allowing nodes to publish interpretable objects without requiring a single, frozen schema,
- and supporting explicit mapping and difference-handling as a first-class mechanism.

A Semantic Web stack can be used *inside* a self-describing grammar (as one semantic layer), but it does not automatically solve the “structure evolves without coordination” problem.

### 2.2 Interface contracts and schema registries (IDLs, JSON Schema, Protobuf, Avro)
Interface definition languages and schema registries provide strong guarantees when schemas are stable and centrally governed. They can support versioning, compatibility rules, and validation.

In constraint-free settings, however, they tend to reintroduce:
- centralized gatekeeping over schema changes, or
- fragmentation into incompatible forks, or
- an accumulation of one-off adapters between “almost the same” versions.

A self-describing grammar aims to reduce reliance on *schema consensus* by carrying a minimal, shared set of primitives for expressing structure and boundaries.

---

## 3. Requirements and assumptions

A self-describing semantic grammar is feasible only if several requirements are met. These can be grouped into **syntax**, **structure**, and **semantics**.

### 3.1 Syntax: self-delimitation and termination
A receiver must be able to determine where a meaningful unit begins and ends without guessing sizes out-of-band.

Common techniques include:
- **length-prefixing** (explicit sizes),
- **delimiter tokens** (explicit end markers),
- **prefix-free / self-terminating encodings** (where no valid unit is a prefix of another).

The grammar does not have to operate at the bit level, but it must define unambiguous **boundary rules** at whatever level it uses.

### 3.2 Structure: hierarchy, grouping, and composable addressing
At minimum, the grammar must support:
- **grouping** (collections, tuples, records),
- **nesting** (hierarchical composition),
- and **composable addressing** (stable paths that refer to parts of a structure deterministically).

Composable addressing is the basis for “database-style referencing”: the ability to refer to a sub-object without shipping a full file snapshot.

### 3.3 Semantics: explicit roles and interpretive cues
Self-description requires that a receiver can identify:
- object roles (e.g., “this is a measurement,” “this is an identifier,” “this is a category assignment”),
- relationship types (e.g., membership, attribution, derivation),
- and any constraints that shape interpretation (units, time scopes, cardinality expectations).

Crucially, the grammar must represent these cues **explicitly**. Reliance on “field name conventions” alone is brittle under semantic drift.

### 3.4 Evolution: versioning without silent remapping
If structure changes over time, the grammar must support:
- **explicit versions** of structural layouts or interpretation policies,
- and a rule that **old references do not silently change meaning**.

In practice, this means that reordering, refactoring, or redefining a structure requires publishing a new version while preserving older references under their original version.

---

## 4. Mechanisms used in self-describing grammar systems

### 4.1 Mapping: local model ↔ shared grammar
Each node maintains an internal model (tables, JSON shapes, documents, or application objects). Interoperability requires a **mapping layer** that:
- projects local structures into the shared grammar,
- and (where needed) reconstructs local form from the shared representation.

Mappings should be explicit, inspectable, and reusable—so the cost of onboarding a new node is not repeated from scratch.

### 4.2 Semantic diff: coordinating through explicit differences
Even with a shared grammar, nodes will encode similar concepts differently:
- alternative nesting choices,
- different units or measurement bases,
- differing category systems,
- partial overlap in fields.

A **semantic diff** mechanism represents these differences explicitly and resolves conflicts by policy (or by negotiated rules), rather than forcing uniformity. The system remains interoperable because differences are *machine-visible*.

### 4.3 Provenance and trust signals
When objects are composed across nodes, receivers often need to know:
- where an object came from,
- how it was transformed,
- and what assumptions or policies governed those transformations.

Common provenance elements include:
- source identifiers,
- transformation descriptions,
- timestamps and version identifiers,
- and (optionally) cryptographic integrity checks (hashes/signatures).

These signals do not create trust by themselves; they make trust *auditable* and enable dispute resolution.

---

## 5. Boundaries and limits (what self-description does not solve)

A self-describing semantic grammar reduces integration friction, but it does not eliminate core problems:

- **Semantic agreement is still required somewhere.**  
  Self-description can expose meaning and differences, but it cannot guarantee that two parties interpret a concept identically.

- **Mappings are unavoidable.**  
  If local models differ, translation is required; the grammar’s goal is to make translation systematic rather than bespoke and opaque.

- **Incentives and governance remain external.**  
  A grammar cannot force participants to publish high-quality data, maintain stable identifiers, or accept shared policies.

- **“Universal expressiveness” is not the same as “universal understanding.”**  
  A system can represent arbitrary structure without guaranteeing that receivers can operationalize it without domain knowledge.

---

## 6. Example design pattern: shape-addressed hierarchical spaces (SAMRAS-style)

One family of approaches separates the **shape** of a hierarchy from the **semantic labels** attached to nodes. The shape is treated as authoritative and is described independently (for example, as a stream of child-counts for each node in a traversal order).

### 6.1 Mixed-radix path addresses
A node address can be written as a path of ordinal positions among siblings:

- `a1_a2_..._an` where each `ai` is an ordinal index among siblings,
- the allowable range of each `ai` is determined by the parent’s declared child count (no fixed radix).

This yields a **mixed-radix** address space: each level’s “base” depends on its parent.

### 6.2 Append-only allocation and stability
If child positions are allocated sequentially in an append-only fashion:
- existing addresses never change,
- and growth occurs by extending the shape description rather than rewriting old paths.

If reordering or non-append evolution is necessary, a new **layout version** is published. Existing addresses remain valid under their original layout version; silent remapping is disallowed.

### 6.3 Ghost positions and existential references
A structural address space may include addressable positions that:
- have no stored metadata,
- have no name,
- and may never be materialized.

References can also include **existential placeholders** (e.g., a suffix marker such as `0`) to indicate “an unknown descendant under this branch” rather than a specific node. Because path syntax alone can be ambiguous, reference intent should be declared explicitly, for example:
- **exact** (the node at that address),
- **group** (the set represented by that node),
- **existential descendant** (one unspecified member below that node).

This explicit intent avoids overloading address syntax with semantics.

### 6.4 Why this pattern is relevant
A shape-addressed space provides:
- stable, composable references into evolving hierarchies,
- a way to separate “structural identity” from “semantic naming,”
- and a basis for attaching provenance and mappings without requiring every node to share a full ontology.

This pattern can be used as a component inside broader self-describing grammar systems (for taxonomies, geographic subdivisions, organizational charts, or other hierarchical namespaces).

---

## 7. Glossary (selected)

- **Adapter explosion**: combinatorial growth of one-off integrations as participants and schema variants proliferate.  
- **Schema drift**: gradual divergence of data structure over time across systems.  
- **Semantic drift**: gradual divergence of meaning attached to similar-looking fields or labels.  
- **Self-delimiting**: a representation that carries enough information to determine unit boundaries without external size assumptions.  
- **Composable addressing**: stable path-based references to substructures that remain meaningful under controlled evolution rules.
