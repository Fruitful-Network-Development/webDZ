# Mycelial Ontological Schema (MOS): Toward a Datum-Native Semantic Grammar for Interoperable Socio-Technical Systems

## Abstract

Interoperability problems in socio-technical networks are often misidentified as failures of transmission rather than failures of operational meaning. Independent systems can exchange files, messages, and records while still remaining inoperable when recipients cannot interpret structure, preserve meaning under change, or compose foreign data without bespoke adapters. This paper presents a bounded conceptual draft of the Mycelial Ontological Schema (MOS) as a response to that problem. MOS is not presented here as another database model, nor as a replacement for linked data, property graphs, schema registries, or content-addressed systems in general. Instead, it is framed as a datum-native semantic grammar intended for settings in which information form cannot be fully pre-limited by a single centralized schema. The paper argues that the relevant research gap is not the absence of self-description, graph structure, canonicalization, or decentralized identifiers in isolation, but the absence of a unified formal core that treats canonically reproducible abstraction paths, self-describing structure, reversible mapping, and semantic interoperability as coequal requirements. On that basis, MOS is presented as a synthetic proposal: a formalism in which abstractions rather than records or nodes are primary, in which structure is explicitly delimited and addressable, and in which cross-system coordination proceeds through shared grammar, mapping, semantic difference, and provenance rather than through repeated file shipping and ad hoc translation. The result is a more bounded and academically defensible novelty claim: MOS may be distinct not because it introduces any one isolated mechanism, but because it attempts to unify several previously separated concerns into a single abstraction-centered model for interoperable computation.

## 1. Introduction

The central problem addressed in this paper is not whether systems can exchange data, but whether they can remain meaningfully interoperable under conditions of independent evolution. In many multi-party networks, participants can transmit bytes, files, or structured payloads without being able to interpret each other's data natively, preserve meaning when models change, or coordinate actions without recurring integration work. This condition may be described as **inoperability**: the exchange of information without reliable shared operational meaning.

That problem is especially pronounced in socio-technical settings. Software systems, organizations, devices, and human operators evolve on different timelines, adopt local conventions, and create new distinctions as their tasks change. Under those conditions, agreement on a single fixed schema or frozen interface contract becomes increasingly brittle. The issue is not simply that systems use different formats. The deeper issue is that the network cannot fully pre-limit the form of information in advance. New entities, new relationships, new constraints, and new interpretive requirements arise over time, and any rigid standard eventually encounters cases it did not anticipate.

This paper develops a bounded draft of the **Mycelial Ontological Schema (MOS)** as a response to that problem. The paper does not claim that MOS solves interoperability in the absolute, nor that it supersedes established paradigms such as linked data, property graphs, schema registries, or content-addressed systems. Instead, it advances a narrower thesis: **MOS is best understood as a datum-native semantic grammar for interoperable socio-technical systems, intended for domains in which information form cannot be fully pre-limited by a single authoritative schema.** In that framing, the relevant question is not whether related technical ingredients already exist. They do. The relevant question is whether there is an established formal model that unifies structural self-description, path-native abstraction, reversible mapping, explicit semantic difference, and canonical reproducibility as a single formal core. The claim of this paper is that MOS is most plausibly distinct at that point of synthesis.

## 2. The interoperability problem

Many contemporary integration strategies treat interoperability as a problem of transport. Two systems exchange a CSV file, a JSON payload, an API response, or an event stream, and the existence of a parseable artifact is taken as evidence that interoperability has been achieved. In practice, that assumption is weak. A receiving system may be able to parse a file without being able to interpret its structure, reconcile its meanings with local concepts, or incorporate it into ongoing computation without custom glue code.

This distinction can be stated more precisely. A fixed format typically solves **transmission agreement**: it tells participants how a sequence of bits should be segmented and read into a finite set of fields. It does not necessarily solve **operational interoperability**: the capacity of independent systems to query, validate, transform, compose, and evolve those structures without bespoke bilateral work. This gap grows over time because even when syntax remains stable, meaning does not. A field name may persist while the business rule attached to it changes. A status flag may retain its label while its operational threshold shifts. A shared schema may remain nominally standard while its participating implementations drift apart.

Several familiar failure modes follow. The first is **schema drift**, where field names, types, nesting, and invariants change over time across local implementations. The second is **semantic drift**, where similar-looking symbols or fields no longer carry the same operational meaning. The third is **adapter explosion**, in which the number of translators, ETL jobs, and local patches grows faster than the number of systems because each participant must continually reconcile local change with every external dependency. Format-first integration tends to obscure these problems temporarily rather than remove them. It permits exchange while pushing interpretation cost onto every receiver.

This is why the strongest form of the interoperability problem is not “how do we make a file portable?” but rather “how do independently evolving systems remain operable with each other when the network cannot pre-limit the forms of meaningful information?” Once posed in that way, the problem no longer looks like a narrow matter of serialization. It becomes a question of formal representation, mapping, versioning, provenance, and shared interpretive structure.

## 3. Research context and adjacent paradigms

A bounded presentation of MOS requires careful placement among adjacent research traditions. The goal is not to deny prior art, but to identify the exact point at which MOS claims a different center of gravity.

The first relevant lineage is **semistructured data**. That literature established that data can be self-describing without being structureless, and that heterogeneous or incompletely regular data need not be forced into a uniform table-first model. This is a foundational precedent for any schema-agnostic position. It supports the claim that structure may travel with the data rather than exist only as a separate external contract.

The second lineage is **linked data and semantic-web work**, including RDF, JSON-LD, ontologies, and formal semantic vocabularies. These paradigms are essential precedents for machine-readable semantics, globally referenceable identifiers, and extensible meaning across distributed authorship. They show that interoperable semantics require more than syntax. At the same time, they do not by themselves establish a model in which structural order, path identity, and abstraction-centered reproducibility are primitive. Ordered collections and practical structural conventions often remain layered concerns.

The third lineage is **graph and path-centric graph theory**. Property graphs, graph databases, and more recent research on first-class path treatment provide a close academic analogue to the intuition that paths may need to be treated as primary objects rather than as merely derived traversals. This is perhaps the strongest comparative baseline for MOS, because it already pushes beyond node-edge storage toward the treatment of paths as meaningful, reusable structures. Yet even here, the dominant conceptual center remains the graph object rather than the abstraction path as the primary carrier of reproducible meaning.

The fourth lineage is **content-addressed and traversable DAG systems**, especially those that combine serial-format agnosticism with generic pathing, selectors, and content-derived identity. These systems offer a major precedent for decentralized traversal and reproducible addressing without centralized schemas. They show that pathing and identity can be formalized independently of a single application format. However, they are not primarily designed as general semantic grammars for reconciling community-level meaning under heterogeneous evolution. They standardize traversable structure and content identity more directly than they standardize reusable semantic interpretation.

The fifth lineage is **canonicalization and deterministic encoding**. Canonical schema forms, deterministic binary encodings, and dataset canonicalization all matter because MOS makes strong use of reproducibility claims. Here the important precedent is not merely that canonicalization exists, but that the academic landscape already distinguishes several types of sameness: structural sameness, schema-equivalence, content identity, and deterministic serialization. MOS enters this space only if it can show that its own distinction between a canonical full structure and a canonical minimal abstraction identity is both formal and nonredundant.

Finally, there is the lineage of **socio-technical interoperability research**, including schema matching, ontology alignment, conceptual interoperability, and standardization studies. This literature is essential because it demonstrates that interoperability failures are not reducible to syntax. They persist because meaning is contextual, evolving, and governed as much by institutions and incentives as by file formats. That body of work provides the most rigorous basis for MOS's claim that generalized interoperability cannot be secured merely by expanding the number of exchange formats or interface contracts.

Taken together, these lineages establish a clear scholarly posture. MOS does not begin from an empty field. It begins at the intersection of several mature lines of work, each of which solves an adjacent part of the problem. The distinct question is whether these components can be unified around a different primary object: not the table, not the document, not only the node or triple, but the canonically reproducible abstraction.

## 4. Defining MOS

The strongest public definition of MOS is neither “a new database” nor “a graph database with extra features.” Those classifications mislocate the conceptual ambition of the model by making storage the primary category. The more precise description is that **MOS is a datum-native semantic grammar in which abstractions are represented as recursively composable relationships whose structure, boundaries, and references are made reproducible within a shared formal framework.**

This definition matters because it relocates the primary object of the system. In a relational system, the row and its schema are primary. In document stores, the document or object is primary. In graph systems, nodes and edges or triples are primary. In the MOS formulation developed across the project materials, meaning is built from rudimentary datum classes and compounded through reference, ordering, and abstraction operators. The system is therefore better described as **datum-first and abstraction-first** rather than record-first, document-first, or node-first.

This shift allows a second definitional step. MOS can be understood as a model in which a complex structure is not only stored, but **reproducibly derived**. The concern is not merely that a datum exists, but that its formation, reference-paths, and ordered composition remain intelligible across systems. On this view, a structure is not simply a container of facts. It is an abstraction that can be reconstructed, traversed, compared, and mapped because the rules of its composition are explicit.

A related concept in the project materials is the distinction between a canonical full representation and a canonical minimal abstraction identity. The former refers to a fully ordered and reproducible structure; the latter to the minimal abstraction basis needed to regenerate or recognize a datum. The paper does not attempt here to formalize those mechanisms in full. It does, however, take seriously the claim that this **dual canonicality** is central to MOS. If formalized rigorously, it would distinguish MOS from many neighboring systems that canonicalize a schema, a block, or a dataset, but do not separately canonicalize a minimal abstraction identity layered over a full ordered structure.

The most defensible one-sentence formulation is therefore the following:

**MOS is a datum-native semantic grammar in which complex meaning is constructed through recursively composable abstractions, with canonical full-state representation and canonical minimal abstraction identity enabling reproducible structure, reversible mapping, and cross-system coordination without forcing all participants into a single centralized application schema.**

That statement is narrower than a general claim to universal novelty, but stronger in academic terms because it specifies both the object and the intended function.

## 5. Self-describing semantic grammar

The conceptual core of MOS depends on the idea of a **self-describing semantic grammar**. This does not mean that every datum is self-sufficient in the strongest possible sense, nor that no shared convention is required. It means that a representation framework carries enough structural and semantic boundary information for an independent system to identify meaningful units and understand how those units relate without relying on a bespoke contract for every partner.

A self-describing semantic grammar requires at least four conditions.

First, it requires **self-delimitation** or equivalent explicit boundary rules. A receiver must be able to determine where meaningful units begin and end without guessing sizes out of band. Whether this is achieved by delimiters, length-prefixing, or some other parser-level mechanism, the representation must define boundaries unambiguously.

Second, it requires **hierarchy and grouping**. Independent systems do not exchange only flat values. They exchange collections, nested structures, scoped subobjects, and compound constraints. A grammar that cannot represent grouping and nesting without external schemas cannot function as a general interoperability substrate.

Third, it requires **composable addressing**. A receiver must be able to refer not only to whole artifacts, but to deterministically identified substructures. This is what makes the model more like reference-based coordination than file shipping. Stable paths allow systems to point to the relevant abstraction rather than repeatedly re-exporting complete snapshots.

Fourth, it requires **explicit semantic cues**. A receiver must not only see that some values are grouped, but also have machine-readable cues about the roles those values play, the relationships between them, and the constraints under which they are meant to be interpreted. Without explicit semantic cues, a system may be structurally parseable while remaining operationally ambiguous.

These conditions explain why self-description is stronger than ordinary serialization. A conventional payload may be syntactically valid while still depending on surrounding tribal knowledge, documentation, UI behavior, or bilateral assumption in order to be used correctly. A self-describing semantic grammar attempts to reduce that dependence by making structural and semantic interpretability part of the formal representation rather than a separate social layer concealed outside the artifact.

In the MOS framework, this requirement connects directly to the claim that information form cannot always be pre-limited. If the network cannot assume a fixed schema, then structure and meaning must be carried in a way that supports open-ended growth. The point is not to abolish convention, but to relocate convention from countless bespoke interface contracts toward a smaller shared grammar of structurally and semantically meaningful primitives.

## 6. From file shipping to reference-based coordination

A major practical distinction in the project materials is the difference between **file shipping** and **reference-based resolution**. This distinction clarifies what kind of interoperability MOS is trying to support.

In a file-shipping model, one node sends another node a file, export, or payload that is only meaningful in the receiver's context if the receiver already knows how to parse and interpret it. The burden of operability lies with every receiving system. Each participant must recognize the format, infer or import the relevant semantics, map the data into its local structures, and reconcile the incoming artifact with existing records or workflows. Such systems can scale as exchange networks, but they scale poorly as operable networks because each new participant imposes recurring interpretation work on every other participant.

Reference-based coordination aims at a different ideal. Instead of treating the payload as an opaque artifact that must be reverse-engineered, it treats the exchange as a reference into a shared interpretive space. The communicated object is closer to “this abstraction, under this grammar, with this provenance, subject to these policies” than to “this file; infer what it means.” Coordination becomes a matter of resolving meaningful objects and subscribing to interpretable changes rather than repeatedly importing and reinterpreting foreign snapshots.

This is not equivalent to saying that files disappear. Rather, it says that files cease to be the primary unit of coordination. The important unit becomes the addressable abstraction and the rules by which that abstraction is resolved. In this sense, MOS attempts to bring network communication closer to database-style references: not because all nodes share one physical database, but because they share a grammar within which references, mappings, and transformations become explicit and machine-auditable.

The relevance of this shift is most obvious in heterogeneous multi-party environments. If local systems can project their own internal models into a shared grammar and if receivers can interpret those projections through explicit mappings, then the network can coordinate through references and semantic differences rather than through endless bilateral adapter work. The result is not uniformity. It is structured heterogeneity.

## 7. Mapping, semantic difference, and provenance

Once MOS is defined as a self-describing semantic grammar, interoperability can no longer be imagined as sameness alone. Independent systems will continue to have different local structures, units, vocabularies, and operational assumptions. A workable model therefore requires mechanisms for **mapping**, **semantic difference**, and **provenance**.

Mapping is the bridge between a node's local model and the shared grammar. Every participant retains its own internal representation—tables, documents, graphs, spreadsheets, or application objects—but expresses those structures in the shared semantic grammar through explicit, inspectable mappings. This reduces the cost of integration because the work of translation becomes formalized and reusable rather than improvised afresh for every exchange.

Semantic difference is equally necessary. Even when two nodes refer to closely related concepts, they will often differ in units, nesting, vocabulary, timing, or interpretive rules. A coordination system that assumes away these differences will either collapse into forced standardization or degenerate into hidden divergence. MOS therefore implies a model in which differences are represented explicitly and resolved by policy or mapping logic rather than denied.

Provenance provides the third layer. If structures are mapped, transformed, and recomposed across nodes, other participants need to know where those abstractions came from and how they were produced. Provenance does not create trust by itself, but it makes trust inspectable. It enables systems to reason about source, derivation, timing, policy, and version rather than accepting foreign data as unqualified fact.

Taken together, mapping, semantic difference, and provenance push MOS beyond the claim of a mere serialization format. They locate it instead as a coordination formalism: a way of making structures interoperable not because all parties agree completely, but because disagreement, variation, and derivation become visible and addressable within the model.

## 8. The novelty claim

The strongest novelty claim for MOS is synthetic rather than absolute. It would be academically weak to claim novelty because MOS is relationship-centric, decentralized, canonicalized, self-describing, or path-based in any isolated sense. Each of those features has clear prior art in existing paradigms. The stronger claim is that **MOS attempts to unify these concerns around the abstraction as the primary formal object.**

The novelty claim therefore has four parts.

First, MOS gives **abstraction paths** or canonically reproducible abstraction structures a more central role than neighboring paradigms typically do. Although path-centric graph research and content-addressed traversal offer close precedents, MOS treats ordered abstraction and its reproducibility as a more foundational concern.

Second, MOS appears to rely on **dual canonicality**: one canonical form for full ordered structure and another for minimal abstraction identity. This is a stronger and more unusual claim than conventional canonicalization, which usually concerns schemas, datasets, or content blocks without separately formalizing a minimal reconstructive identity.

Third, MOS combines **self-describing structure** with **explicit mapping and semantic difference**. Many systems either assume a fixed schema, leave semantics largely external, or treat mappings as ancillary integration logic. MOS moves those into the conceptual center of interoperability rather than treating them as downstream patchwork.

Fourth, MOS links technical representation to **structured heterogeneity** rather than to forced schema uniformity. Its aim is not to eliminate local models, but to allow locally governed systems to coordinate through a shared grammar without collapsing them into one platform-owned ontology.

These claims remain bounded. They do not assert that MOS has already been proven as a mature general standard, nor that it fully resolves ontology alignment, governance, or semantic change. They assert something narrower: that there is a plausible research contribution in treating abstraction-centered reproducibility, structural self-description, reversible mapping, and semantic interoperability as one unified formal problem.

This is the proper academic posture for the project. It avoids rhetorical overreach while still identifying a real potential contribution.

## 9. Implications for interoperable socio-technical systems

If the MOS formulation holds, its implications are practical as well as conceptual.

The first implication is a reduction in integration friction. When nodes can express their local structures within a shared grammar and attach explicit mappings, the cost of onboarding new participants no longer grows as a purely pairwise burden. Translation work remains necessary, but it becomes explicit, inspectable, and reusable.

The second implication is a change in how coordination is organized. Systems can coordinate through references to meaningful abstractions rather than through repeated shipment of opaque files. This supports more incremental, composable, and auditable forms of cooperation.

The third implication is better handling of evolution. Because the grammar is designed for settings in which information form cannot be fully pre-limited, the system can tolerate new distinctions, new substructures, and new local variants without immediately treating them as schema violations. Growth in meaning becomes an expected condition rather than a breakdown of the model.

The fourth implication is organizational rather than purely technical. A grammar-centered approach offers a way to preserve local autonomy while still enabling network-level coordination. Participants need not abandon their internal models in order to join a broader interoperable network. Instead, they expose the relevant structures through shared grammar, mapping, provenance, and policy.

For socio-technical systems, this matters because interoperability failures are rarely just software failures. They are failures of coordination under change. A model that reduces the need for hidden conventions and ad hoc translators could therefore improve not only data exchange, but also the ability of organizations to coordinate action across heterogeneous tools and institutions.

## 10. Limits and non-claims

A paper of this kind requires explicit boundaries.

First, self-describing structure does not eliminate the need for **semantic agreement**. Systems may still interpret similar abstractions differently, and no grammar alone can abolish the need for domain knowledge, negotiated meaning, or institutional governance.

Second, explicit mappings do not eliminate **translation work**. They simply make that work more systematic, inspectable, and reusable. MOS should not be presented as a system in which difference disappears. It is a system in which difference is formalized.

Third, provenance and policy do not create **trust** by themselves. They create the conditions under which trust can be audited, challenged, and reasoned about. Social legitimacy remains partly external to the representation.

Fourth, the paper does not claim that MOS is already a completed formal standard. The exact force of its novelty depends on future specification work: parse rules, ordering semantics, canonicalization proofs, abstraction laws, and demonstrable mapping behavior. Without that formal layer, MOS remains a strong conceptual proposal rather than a settled technical theory.

Fifth, the paper does not claim universality in the metaphysical sense. It claims a bounded relevance for heterogeneous, evolving systems in which information form cannot be completely pre-limited and in which interoperability must survive local autonomy and change.

These non-claims are not weaknesses. They are what make the argument durable.

## 11. Conclusion

The problem that motivates MOS is not the absence of data exchange. It is the persistence of inoperability in systems that already exchange data. Format-first integration solves transmission more easily than it solves meaning, and as socio-technical networks evolve, that gap widens. Existing research traditions provide many necessary ingredients—semistructured data, linked data, path-centric graphs, content-addressed traversal, deterministic encoding, canonicalization, schema matching, and ontology alignment—but no single dominant model has made abstraction-centered reproducibility, self-describing structure, reversible mapping, and semantic interoperability the shared core of one formal system.

MOS is most defensibly understood as a response to that gap. It is not best described as another database, nor primarily as a graph store. It is better described as a datum-native semantic grammar and abstraction calculus for interoperable systems. Its potential distinctness lies in centering the reproducible abstraction rather than the record, the document, or only the graph fact; in requiring structure, boundaries, and semantic cues to be explicit; and in treating mapping, semantic difference, provenance, and canonical reproducibility as coequal parts of interoperability.

Whether MOS ultimately succeeds as a formal contribution depends on future proof, not on rhetoric. It must demonstrate that its abstractions can be parsed, addressed, canonicalized, mapped, and resolved across heterogeneous systems in ways that existing paradigms do not already provide in combination. But framed in that bounded way, MOS has a credible and academically serious position: it is a proposal for how independently evolving systems might remain interoperable when the form of meaningful information cannot be frozen in advance.

## Working reference base

The present draft is synthesized from the project's internal research and conceptual manuscripts:

- *Research Foundations for a Schema-Agnostic Abstraction-Path Data Model*
- *Defining MOS as Novel and Distinct*
- *Information Technology & Social Systems — Interoperability Notes (ULI / MSS Focus)*
- *Self-Describing Semantic Grammars*
- *Interoperability in Socio-Technical Networks*
- *Mycelial Ontological Schema*
- *drr-schema_agnostic_abstraction_path_data_model.md*

## Note for the next revision

The next academically stronger revision should add a formal prior-art matrix and an external bibliography comparing MOS directly against semistructured data models, RDF/JSON-LD, property/path graphs, IPLD, deterministic binary encodings, and canonicalization frameworks.
