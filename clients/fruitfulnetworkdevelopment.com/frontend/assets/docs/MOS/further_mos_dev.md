# 5. What still remains

The draft is conceptually coherent, but it still lacks the parts that make it read as an academically grounded paper rather than a strong internal position paper.

The main missing piece is observed failure. Right now the paper states the interoperability problem well, but it still needs a short section showing where that problem is actually seen: systems that can exchange data yet remain inoperable because meaning, structure, or evolution are not shared. Your interoperability materials already center that distinction between transmission agreement and operational interoperability, along with schema drift, semantic drift, and adapter explosion

. The paper should pull in 2–4 concrete observed cases, not abstract categories alone.

The second missing piece is a formal statement of the object. The draft says MOS centers abstractions rather than records, documents, or graph facts, but it still does not state, with enough precision, what an abstraction is, what an abstraction path is, and what makes one reproducible. Your novelty and research-foundation notes already point to the right answer: MOS becomes defensible only when it is formalized as a datum-native system with abstraction-centered identity, not merely described rhetorically as more semantic or more decentralized

.

Third, the paper still needs a worked example. Without one, “self-describing semantic grammar,” “reversible mapping,” and “reference-based coordination” remain intelligible only at the level of theory. It needs one small example that walks from local model A and local model B into a shared grammar, shows where the semantic difference is, and shows how a reference or mapping resolves it. That is the quickest way to bring in the “realities of what is observed.” It will also stop the paper from reading like a manifesto.

Fourth, the novelty section still needs a prior-art matrix. The draft says the right things, but an academic reader will still ask: compared to what, exactly? You need a compact comparison table against semistructured data, RDF/JSON-LD, property/path graphs, IPLD, and canonicalization systems. The key columns should be: primary object, what is canonicalized, whether path identity is first-class, whether structure is self-describing, whether mapping/diff is intrinsic, and what remains external. Your own notes already suggest this is the next strengthening step

.

Fifth, the paper still needs to say what would count as proof. At present it says MOS would need future formal specification, but it should be sharper. It should name the exact things that must be demonstrated: parse rules, boundary rules, ordering semantics, canonicalization laws, abstraction identity, and mapping behavior across heterogeneous systems. Your internal material already makes this clear: the claim survives only if the model can justify dual canonicality and a unified abstraction-centered formal core rather than adjacent borrowed features

.

Sixth, the paper needs one section on scope boundary between conceptual layer and implementation layer. Right now the conceptual argument is clean, but the reader still does not know what belongs in MOS proper versus MSS, hyphae, selectors, or database-backed implementations. Your database-mapping note is useful here mainly as evidence that implementation exists downstream, but it should stay out of the main argument except as a short “implementation implication” note

.

So, in practical terms, what remains is this.

You need an “observed reality” section with concrete failure cases.
You need a formal object-definition section for datum, abstraction, abstraction path, and dual canonicality.
You need one worked interoperability example.
You need a prior-art comparison matrix.
You need a short “what would prove this” section.
You need a scope boundary between theory and implementation.

Those six additions would move it from strong conceptual draft to academically serious white paper.

The single most important one is the worked observed case. Without that, the paper still explains why MOS might matter, but not where the reader can actually see the problem.
