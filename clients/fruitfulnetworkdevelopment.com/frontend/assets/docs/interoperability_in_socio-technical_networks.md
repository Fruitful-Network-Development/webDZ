# Interoperability in Socio-Technical Networks

## Overview
**Interoperability** is the ability of independently developed systems (software, organizations, devices, and their human operators) to exchange information and use it meaningfully without bespoke, case-by-case integration for every interaction. In socio-technical settings, interoperability is constrained not only by technical interfaces, but also by governance, incentives, and the fact that meaning is contextual and evolves.

A recurring failure pattern in large networks is that **syntactic agreement** (shared file formats, APIs, or schemas) is achievable, while **semantic agreement** (shared meaning under change) is not guaranteed.

---

## Definitions

### Interoperability
A property of a networked setting in which:
- participants can **communicate** data,
- recipients can **interpret** the data’s meaning as intended (within declared scope),
- and both parties can **adapt** as models evolve, without requiring a complete rewrite of integration paths.

### Inoperability
A network condition in which systems can exchange bytes, files, or messages, but cannot reliably:
- interpret each other’s structures,
- preserve meaning under local changes,
- or coordinate actions without manual reconciliation.

### Schema drift
The gradual divergence of a data schema over time (field names, types, nesting, invariants, units, constraints). Drift occurs even when a schema is “standardized,” because local requirements and operational contexts evolve.

### Semantic drift
The gradual divergence of **meaning** attached to symbols, fields, labels, categories, or states (e.g., “active customer,” “available inventory,” “delivered,” “verified”). Semantic drift can occur even when the schema stays stable, because policies, measurement practices, and business rules change.

### Adapter explosion
A scaling failure where the number of required translators (mappers, converters, ETL jobs, integration glue) grows faster than the number of systems:
- pairwise adapters grow as **O(n²)** in the worst case,
- and each adapter must be maintained as schemas and semantics drift.

---

## Core constraint: networks cannot pre-limit information form
In many socio-technical networks, it is not feasible to restrict all participants to a fixed, finite set of “allowed forms” of information, because:
- new operational states appear (products, regulations, workflows, exceptions),
- local contexts introduce new dimensions (units, identifiers, policies),
- and meaning depends on process, not just structure.

As a result, “universal formats” tend to shift the problem rather than solve it:
- they standardize *packaging*,
- but do not ensure interoperable *interpretation* under evolution.

---

## Communication models

### File shipping
A model where interoperability is approximated by exchanging complete artifacts:
- files, JSON payloads, spreadsheets, exports, snapshots, reports.

**Strengths**
- easy to bootstrap and audit as a static artifact,
- low initial coordination cost.

**Weaknesses**
- recipients must guess or reverse-engineer intent,
- updates require repeated re-export and re-import,
- semantics often live outside the file (documentation, tribal knowledge, UI behavior),
- drift accumulates and breaks downstream consumers.

### Reference-based resolution
A model closer to “database-style references,” where a message carries:
- **references** (identifiers/pointers),
- **declared meaning** (semantics, units, constraints, provenance),
- and a resolution path for retrieving the authoritative context.

**Strengths**
- supports incremental updates (diffs, partial retrieval),
- reduces redundant duplication of large artifacts,
- makes provenance and policy explicit,
- enables coordination across heterogeneous internal models.

**Weaknesses**
- requires shared conventions for identity, meaning, and trust,
- requires governance for versioning, compatibility, and access control,
- harder to bootstrap than file shipping.

---

## Failure modes of format-first integration
Format-first integration treats interoperability primarily as a problem of agreeing on:
- a file format,
- a canonical schema,
- or a standardized API surface.

Common failure modes:
1. **Standard captures assumptions that do not generalize.** Edge cases become “out of scope,” so systems reintroduce side-channels and exceptions.
2. **Schema compliance hides semantic disagreement.** Two systems may both emit “status=delivered” while meaning different completion criteria.
3. **Integration becomes adapter maintenance.** Each participant evolves locally; the network pays continuous translation cost.
4. **Frozen formats inhibit legitimate evolution.** When standards cannot change quickly, participants fork or tunnel new meaning into old fields.
5. **Meaning remains local to internal logic.** External formats are used at the boundary, while internal interpretation stays idiosyncratic; interoperability is superficial.

---

## Practical implications for interoperable network design
Systems that remain interoperable under change typically incorporate:
- **explicit versioning** (schema versions, compatibility policies),
- **mapping layers** (local model ↔ shared representation),
- **declared semantics** (units, invariants, state machines, policy rules),
- **provenance** (where the datum came from, how it was produced),
- **auditability** (what changed, why, and under which interpretation),
- and governance for **identity**, **access**, and **conflict resolution**.

A socio-technical network tends to fail when it assumes that a single frozen format can carry all future meaning without:
- a mechanism to represent new distinctions,
- and a way to reconcile differences across nodes.

---

## See also
- Semantic interoperability
- Data governance
- Ontologies and controlled vocabularies
- Event-driven architectures and schema registries
- Versioned APIs and compatibility contracts

---

## References (project sources)
- *Information Technology & Social Systems — Interoperability Notes (ULI / MSS Focus)* (internal draft).
- *mss_novility.txt* (internal draft excerpts on semantic internet / interoperability constraints).
