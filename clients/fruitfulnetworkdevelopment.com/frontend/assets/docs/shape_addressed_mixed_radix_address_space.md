# SAMRAS uniqueness and conceptual explanation article

This draft is synthesized from the canonical SAMRAS structural contract, the shape-addressed mixed-radix note, the HOPS contrast material, the SAMRAS history audit, and your uploaded SAMRAS notes.      

## Abstract

A Shape-Addressed Mixed-Radix Address Space, or SAMRAS, is not primarily a storage format, a taxonomy file, a UI navigation device, or a particular implementation artifact. It is a structural concept. More specifically, it is a conceptual model for making a variable-branching hierarchy authoritatively addressable by shape rather than by semantic labeling. In a SAMRAS, the governing authority is not a name, not a row, not a stored full path, and not a visual tree. The governing authority is the reconstructible structure itself.

This matters because most hierarchical systems silently confuse semantic attachment with structural identity. They treat titles, categories, or folders as though those are the hierarchy. They are not. Those things are overlays. A hierarchy only becomes structurally authoritative when valid addresses can be determined from the structure itself. SAMRAS exists to provide that condition. It defines an address space in which each segment is constrained by local structural reality, and in which a node is identified by its ordinal relation within a variable topology rather than by an arbitrary naming convention.

The conceptual significance of SAMRAS is therefore broader than any one implementation. It is a way of thinking about hierarchy, addressability, and structural authority in any domain where local branching may vary and where semantic attachments must remain secondary to structural form.

## 1. The problem of hierarchical identity

A hierarchy is often treated as though its labels are its structure. That is a categorical error.

A folder name is not a hierarchy. A title is not a hierarchy. A row in a table is not a hierarchy. Even a stored path string is not, by itself, a hierarchy. Those things may express or reference structure, but they do not constitute it. The structure of a hierarchy is the ordered relation of containment and branching that makes certain positions valid and others invalid.

When this distinction is not made, systems drift. Titles become mistaken for authorities. A rendered view becomes mistaken for the source of truth. Rows are extracted and rearranged until the view appears coherent, even if the underlying structural logic no longer is. Once that happens, the system may still look organized, but it is no longer structurally authoritative. It has become semantically staged rather than structurally governed.

SAMRAS begins from the refusal of that confusion. It does not ask what the nodes are called first. It asks what structure exists first. Only after that question is settled can the system meaningfully address anything within that structure.

## 2. What SAMRAS is

SAMRAS is a shape-addressed mixed-radix address space represented as a structural value.

Each of those terms matters.

It is shape-addressed because valid addresses are determined by the topology of the structure. The hierarchy is not imposed afterward upon a list of names. The hierarchy is already there in the structural authority, and the addresses emerge from it.

It is mixed-radix because the valid ordinal range of any address segment is not fixed globally. It depends on the local child capacity of the parent under which that segment occurs. The allowed next value is therefore context-sensitive. A segment is valid not because it belongs to a universal base, but because the parent structure authorizes it.

It is an address space because it defines a domain of possible positions. It does not merely list occupied records. It defines what positions can be validly referred to.

It is a structural value because what is stored authoritatively is not the final semantic view but the structure from which that view must be derived. In canonical form, this structural value preserves child-count information in such a way that the topology can be reconstructed and valid addresses can be derived from ordinal relation.

This is the simplest precise statement of the concept: SAMRAS is a structural authority for variable hierarchies.

## 3. Why shape-addressed matters

The phrase shape-addressed is the conceptual center of SAMRAS.

Most systems assume that addressing begins with explicit identifiers. SAMRAS assumes the opposite. Addressing begins with shape. The structure defines the legal positions, and the address is an expression of position within that structure.

That means a node does not need to store its full address as an intrinsic property of itself. Its address is recoverable from the structure because the structure carries the branching logic that makes that address valid. The node is not first named and then placed. It is first positioned and only then may be named.

This reverses a common software habit. The usual habit is to begin from semantic tags and then arrange them. SAMRAS begins from formal position and only afterward permits semantic attachment. That is why the concept remains stable even when names change, when titles are missing, or when overlays are inconsistent. The authority has not moved, because the authority was never the overlay.

A structurally authoritative hierarchy must survive semantic incompleteness. SAMRAS is built precisely so that it can.

## 4. Why mixed-radix matters

The phrase mixed-radix identifies the second essential property.

A uniform radix assumes that every position at a given level is governed by the same capacity rule. SAMRAS does not make that assumption. It permits local branching to vary by parent. One node may authorize three children, another eighty-one, another none. The address space is therefore locally constrained rather than globally flattened.

This is not merely a technical encoding detail. It is a conceptual claim about hierarchy itself. Real variable structures are not uniform partitions. They do not behave like a fixed decimal lattice. They behave like shaped topologies whose local possibilities differ according to their position in the whole.

SAMRAS preserves that reality. It does not force variable structure into a homogeneous frame merely for convenience. Instead, it lets the structure remain variable and derives address validity from that variation.

That is why SAMRAS is the correct conceptual class for hierarchies whose local branching is part of their truth.

## 5. Structural authority and semantic overlay

One of the most important distinctions in SAMRAS is the distinction between structure and overlay.

The structure is authoritative. Titles, labels, classifications, and descriptive metadata are not authoritative as structure. They are attachments to structure. They may be useful, necessary, or even indispensable for human interpretation, but they do not define which addresses are valid.

This distinction is what allows SAMRAS to remain domain-agnostic. The same structure can support biological taxonomies, administrative divisions, organizational namespaces, or any other hierarchical domain. The domain changes the semantic overlay, not the structural principle.

Once this is understood, several confusions disappear. A duplicated label is not a structural duplication unless it binds to the same structural position in violation of the namespace. A missing title is not the absence of a node if the position is structurally authorized. A visually rendered hierarchy is not the structural source of truth if it is only an interpretation of node rows or labels detached from the governing structural magnitude.

The structure governs. The overlay interprets. That order must not be reversed.

## 6. Address derivation and the rejection of arbitrary path authorship

A SAMRAS address is not arbitrary text. It is a derived ordinal path.

The root level establishes the first set of valid positions. Each later segment expresses ordinal position among siblings under a parent already authorized by the structure. A valid address is therefore not simply any hyphenated string of integers. It is a path that the structure can justify.

This is why address derivation matters conceptually. It means the system can distinguish between a string that looks like an address and a position that is actually real in the governing structure. Only the latter is authoritative.

The consequence is that SAMRAS rejects silent fabrication. A path is not made valid because a human typed it. It is valid because the structure authorizes it. Conversely, a position may be real even when no human-readable label has yet been attached to it. Structural reality is prior to semantic decoration.

This is a stricter conception of addressability than most systems adopt. That strictness is the source of its value.

## 7. Structural potentiality, ghost positions, and existential reference

SAMRAS does not reduce reality to already materialized records.

A structurally authorized position may exist without a stored title, without a semantic profile, and without a materialized row. Such a position is structurally real even if it is semantically undefined. This is one of the most conceptually distinctive aspects of SAMRAS.

A position can therefore be addressable before it is narratively filled in. The structure makes it available as a valid site of relation. Whether the system has yet attached a name, a description, or a bound object to that site is a separate matter.

This also makes possible more careful reference semantics. A reference may designate an exact node, a grouped set under a node, or an existential but unspecified descendant below a node. These are not the same thing, and SAMRAS is strongest when those distinctions are made explicit rather than inferred carelessly from syntax alone.

What this reveals is that SAMRAS is not only a model of occupied hierarchy. It is a model of structured possibility. It governs not only what is already semantically present, but also what is structurally available for future articulation.

## 8. Mutation, continuity, and versioned change

A structurally authoritative address space must govern mutation as strictly as it governs existence.

In SAMRAS, mutation is not conceptually the editing of a raw magnitude by hand. Mutation is the transformation of a structure under rules that preserve or deliberately revise the authoritative address space. If a change is append-only, existing addresses can remain stable because new positions are added in a way that does not reorder prior ordinal relations. If a change would alter existing ordinal relationships in a non-append manner, then the structure has become a new layout and must be treated as such.

That principle matters because it prevents silent remapping. Without it, an address may appear to remain the same while secretly changing what it denotes. A structurally serious system cannot permit that. If the layout changes in a way that alters prior meaning, a new structural version is required.

The concept here is deeper than codec behavior. SAMRAS treats structural continuity as something that must be maintained explicitly, not assumed casually. Mutation is therefore a governed act of structural authorship, not an ad hoc revision of labels or rows.

## 9. Domain-agnostic scope

SAMRAS is not inherently geographic. It is not inherently biological. It is not inherently administrative. Those are only domains in which variable hierarchical structure appears.

The same conceptual rules apply wherever there is a need to preserve an authoritative relation between hierarchy and address. If local branching may vary by parent, and if semantic names must not be allowed to become structural substitutes, then the conceptual conditions for SAMRAS are present.

This domain-agnostic quality is essential to its uniqueness. SAMRAS is not a domain schema masquerading as a general theory. It is a general theory of structurally governed variable hierarchy that can later be instantiated in domain-specific ways.

That is why the same addressing logic can apply across taxonomic domains, administrative domains, and other hierarchical namespaces while remaining the same concept.

## 10. Why SAMRAS exists beside HOPS

The distinction between SAMRAS and HOPS clarifies the uniqueness of SAMRAS.

HOPS defines fixed subdivision. SAMRAS reconstructs variable shape.

That contrast should be read carefully. A HOPS is appropriate where every parallel node at a given level shares the same child capacity. The structure then defines a homogeneous partition schema for an ordered continuum. A SAMRAS is appropriate where local branching differs by parent and where the system must preserve that variation as part of the structure itself.

The difference is therefore not cosmetic. It is ontological.

A HOPS says, in effect, that the space is governed by level-homogeneous denotational capacities. A SAMRAS says that the space is governed by variable local topology. One defines subdivision. The other reconstructs shape.

This contrast helps prevent misuse. If one attempts to treat a variable hierarchy as though it were a fixed partition schema, the structure is flattened and local authority is lost. If one attempts to treat a homogeneous partition as though it required variable shape reconstruction, unnecessary complexity is introduced. The two concepts should remain distinct precisely because they solve different structural problems.

## 11. Why SAMRAS is unique

The uniqueness of SAMRAS does not lie merely in its encoding layout. It lies in the conceptual discipline it imposes.

It insists that structural validity precede semantic convenience.

It insists that address be derived from structural relation rather than authored as arbitrary text.

It insists that variable local branching be preserved as structural truth rather than normalized away.

It insists that semantically absent positions may still be structurally real.

It insists that overlays remain overlays and not be confused for the authority they interpret.

It insists that mutation be treated as structural authorship under continuity rules rather than as ungoverned revision.

Taken together, those conditions make SAMRAS more than a notation. They make it a concept for structurally authoritative hierarchy.

## 12. Conclusion

SAMRAS should be understood as a conceptual model for addressability in variable-shape hierarchies. Its purpose is not merely to encode data more compactly or to furnish a novel syntax. Its purpose is to establish a principled relation between structure and reference.

A SAMRAS does this by making shape authoritative. The structure preserves child-capacity relations. Valid addresses are derived from ordinal position within that variable topology. Semantic titles, names, classifications, and domain narratives are then permitted to bind onto those positions without becoming the source of structural truth.

This is what makes SAMRAS both technically rigorous and conceptually important. It provides a way to preserve hierarchy as hierarchy, rather than letting it dissolve into labels, rows, or rendered views. It gives a system the ability to say, with precision, that a position is valid because the structure authorizes it, not because someone happened to name it.

That is the central depiction.

SAMRAS is a structurally authoritative, shape-addressed, mixed-radix address space for variable hierarchy. It is a concept of derived positional identity. It is a separation of structural truth from semantic overlay. And it is, for that reason, not reducible to any particular implementation that happens to express it.

---


# SAMRAS uniqueness and conceptual explanation synthesis

I searched the repo references around SAMRAS and the useful material is concentrated in `Fruitful-Network-Development/mycite-core`. I did not find meaningful SAMRAS material in the other repos. The earliest searchable commit subjects I found are in March 2026, but the clearest formal articulation appears in the later contract, note, and audit files. The most useful sources for a concept-first article are the canonical structural model, the personal-note specification, the HOPS contrast, the SAMRAS history audit, and your supplemental SAMRAS note     

The consolidated articulation is this:

SAMRAS is best understood not as a file format, not as a UI pattern, and not as a naming convention, but as a way of making hierarchy structurally addressable. Its central claim is that a hierarchy can be governed by shape rather than by labels. The authoritative thing is the structure itself: a variable-branching arrangement whose valid addresses are derived from ordinal position within that shape. In that sense, SAMRAS is a concept for structural authority. A node’s identity comes from where it stands in a reconstructible topology, not from a human title, database row, or stored full path string  

That is the core article thesis:

“SAMRAS is a conceptual model for structurally authoritative addressability in variable-branching hierarchies, where addresses are derived from shape rather than assigned by semantic naming.”

The part that makes SAMRAS distinct is the combination of four ideas.

First, structure precedes naming. The shape is authoritative, while names, titles, classifications, and overlays are secondary attachments. This appears repeatedly in the repo language: the structure defines the valid address space, and later rows or metadata only decorate or bind meaning onto that space  

Second, address is derived, not stored. The concept does not begin from an explicit list of permanent path strings. Instead, a structural value preserves the branching pattern, and valid addresses are recovered from that pattern through ordinal descent. This is the main conceptual move, and it is the cleanest way to describe SAMRAS without tying it to one implementation  

Third, SAMRAS separates structure from semantics. Your supplemental note states this most directly: the specification is domain-agnostic, the same address rules apply across biology, geography, administrative hierarchies, or organization, and the shape is authoritative regardless of which semantic labels are later attached 

Fourth, SAMRAS allows structurally real but semantically unresolved positions. That is one of the more unusual conceptual points. A position can exist in the addressable structure without yet having a materialized record, name, or metadata. Your note calls these ghost positions and also distinguishes existential placeholders from actual nodes. That is important because it makes SAMRAS more than a taxonomy format. It becomes a concept for addressable potentiality within a structure, not just catalogued occupancy 

From the repo history, the cleanest conceptual framing is that SAMRAS emerged as a structural answer to a recurring problem: how to keep hierarchy authoritative when UI views, row overlays, labels, and domain-specific projections keep drifting. The April audit states that the historical authority is clear: the SAMRAS magnitude defines structure, while node rows are overlays. That audit matters because it clarifies the conceptual rule underneath the implementation disputes 

For the article itself, I would compose it with this section structure.

Abstract. State that SAMRAS is a concept for making variable hierarchies structurally addressable without depending on semantic names or implementation-specific storage.

1. The problem of hierarchical identity. Explain the weakness of systems where hierarchy depends on labels, folders, rows, or manually authored paths.

2. What SAMRAS is. Define it as a shape-addressed mixed-radix address space whose governing authority is structural rather than semantic 

3. Why “shape-addressed” matters. Explain that the arrangement of branching is the source of validity, and that addresses are recovered from ordinal relation inside that arrangement 

4. Why “mixed-radix” matters. Keep this broad: each descent is constrained by the parent’s capacity, so the valid range of a segment is contextual rather than globally fixed. This gives SAMRAS its local rather than universal radix character 

5. Structural authority and semantic overlay. Clarify that titles, classes, and labels do not constitute the structure; they only bind onto it afterward 

6. Ghost positions, unknown descendants, and partial reference. This should explain the unusual feature that a structure can contain addressable but semantically unresolved positions, and that references may distinguish exact nodes from sets or unknown descendants 

7. Stability, mutation, and versioning. Keep this conceptual: if the structure changes append-only, addresses remain stable; if shape changes non-append, a new layout version is required. This turns mutation into a governed structural event rather than an informal relabeling  

8. Domain-agnostic scope. State that SAMRAS is not inherently geographic, biological, or administrative. Those are only domains in which a structurally authoritative hierarchy is useful 

9. Contrast with HOPS. This contrast is already very clean in the repo: SAMRAS reconstructs variable shape, while HOPS defines fixed subdivision. That contrast helps explain SAMRAS uniqueness by showing what it is not 

10. Conclusion. Reassert that SAMRAS is a concept of structural addressability, not merely a serialization method.

The article should keep four claims in the foreground.

SAMRAS is not primarily about encoding; encoding is only how the structure is preserved.

SAMRAS is not primarily about names; names are overlays on structural positions.

SAMRAS is not primarily about currently materialized records; it can govern positions that are only structurally present.

SAMRAS is not tied to one domain or one interface; it is a general concept for variable-shape address spaces.

A concise opening paragraph for the article would be:

“SAMRAS names a way of understanding hierarchy in which structure itself becomes the authority for address. Rather than treating labels, folders, or stored path strings as the basis of identity, it treats the shape of a hierarchy as the governing source from which valid addresses are derived. In this view, an address is not merely assigned to a node; it is produced by the node’s ordinal relation within a reconstructible topology. What matters first is structural position, and only secondarily the semantic overlays that later bind names, classifications, or meanings onto that position.”

A concise uniqueness paragraph would be:

“The uniqueness of SAMRAS lies in its refusal to collapse structure into labeling. It allows a hierarchy to remain authoritative even when semantic overlays change, remain incomplete, or are absent altogether. Because its addresses arise from variable branching shape rather than a fixed global radix or a human-authored naming scheme, it can preserve both structural rigor and semantic openness.”

One important finding from the repo search is that the strongest article should not be written from the later CTS-GIS implementation language outward. It should instead begin from the conceptual throughline that appears across the notes and contracts: structure governs addressability; semantics bind later; mutation must preserve authority; and domain meaning is contextual, not built into the structure itself   

If you want the next step, the correct one is to turn this into a full article draft using these exact sections and keeping the language intentionally concept-first rather than implementation-first.


# Shape-Addressed Mixed-Radix Address Space

## Purpose

This document defines the logical and algorithmic process for representing a **Shape-Addressed Mixed-Radix Address Space (SAMRAS)** as a structural value.

The purpose of this model is:

- to treat a SAMRAS datum as a **structural value**, not a free-form human-authored magnitude,
- to derive valid address spaces from a canonical structure,
- to allow address-based editing of nodes,
- to recompile the governing structural magnitude deterministically after edits,
- to make every SAMRAS structure either **valid** or **invalid** under explicit rules.

This document is written as a pseudo-code specification and implementation guide.

---

## Core idea

A SAMRAS structure defines a **tree or forest of nodes**.

Each node does **not** store its address explicitly inside the structure value.
Instead:

1. the structure stores a sequence of **child counts**,
2. the system interprets those child counts in **breadth-first order**,
3. addresses are then derived from **ordinal child position**.

So:

- the **structure value** defines the valid address space,
- the **address magnitudes** reference positions inside that defined space.

This means:

- addresses are **derived from structure**,
- but sandbox/resource editing should allow users to **edit the structure through addresses**,
- then the engine must **rebuild the structure value** automatically.

---

## Governing datum rule

A SAMRAS structure datum is a layer-1 datum created in reference to:

- `0-0-5` = nominal ordinal position

In this model, any datum created there is understood as a **SAMRAS structural value**.

---

## High-level model

A SAMRAS structural value is encoded as five parts:

1. `address_width_field`
2. `stop_count_width_field`
3. `stop_count_field`
4. `stop_address_array`
5. `value_stream`

The value stream encodes a sequence of variable-width binary values.
The stop-address array tells the decoder how to slice that stream into individual values.

---

## Canonical interpretation of the value sequence

Let the decoded values be:

- `v0, v1, v2, ..., vn`

Interpret them like this:

- `v0` = number of root nodes in the forest
- every later `vi` = number of children under the next node in breadth-first order

Then addresses are assigned by ordinal position:

- root nodes: `1`, `2`, ..., `v0`
- if node `a` has `k` children, then its children are:
  - `a-1`, `a-2`, ..., `a-k`

Example:

If the child-count sequence is:

- `3, 1, 2, 0, 0, 1, 0`

Then:

- `3` roots exist: `1`, `2`, `3`
- node `1` has 1 child: `1-1`
- node `2` has 2 children: `2-1`, `2-2`
- node `3` has 0 children
- node `1-1` has 0 children
- node `2-1` has 1 child: `2-1-1`
- node `2-2` has 0 children

---

## Address derivation rule

Addresses are not stored explicitly in the structure value.
They are derived from the breadth-first child-count interpretation.

Pseudo-code:

```text
function derive_addresses_from_child_counts(values):
    root_count = values[0]

    queue = []
    addresses = []
    next_value_index = 1

    for i from 1 to root_count:
        root_address = str(i)
        queue.push(root_address)
        addresses.append(root_address)

    while queue is not empty:
        parent = queue.pop_front()

        if next_value_index >= length(values):
            raise InvalidStructure("not enough child-count values")

        child_count = values[next_value_index]
        next_value_index += 1

        for child_ordinal from 1 to child_count:
            child_address = parent + "-" + str(child_ordinal)
            queue.push(child_address)
            addresses.append(child_address)

    if next_value_index != length(values):
        raise InvalidStructure("unused values remain after queue is exhausted")

    return addresses
```

---

## Structural encoding layout

### 1. Address width field

This field encodes how many bits are used to store each stop address.

Rule:

- a run of `0`s terminated by `1`
- the number of leading `0`s is the width

Example:

- `00001` means width = 4
- `00000000001` means width = 10

Pseudo-code:

```text
function encode_unary_width(width):
    return repeat("0", width) + "1"

function decode_unary_width(bitstream, start_index):
    count = 0
    i = start_index

    while i < length(bitstream) and bitstream[i] == "0":
        count += 1
        i += 1

    if i >= length(bitstream) or bitstream[i] != "1":
        raise InvalidStructure("unterminated unary width field")

    return (count, i + 1)
```

---

### 2. Stop-count width field

This field encodes how many bits are used to store the `stop_count`.

It uses the same unary-width rule.

---

### 3. Stop-count field

This field encodes how many stop addresses exist.

Important:

- if `stop_count = N`
- then there are `N + 1` decoded values in the value stream

Because the stop addresses denote slices:

- `[:s1]`
- `[s1:s2]`
- ...
- `[sN:]`

So the stop count is **not** the number of final values.
It is the number of stop boundaries.

Pseudo-code:

```text
function encode_fixed_width_binary(value, width):
    bits = binary(value)
    if length(bits) > width:
        raise InvalidStructure("value does not fit in fixed width")
    return left_pad(bits, width, "0")
```

---

### 4. Stop-address array

The stop-address array contains cumulative **exclusive** end positions into the value stream.

If the value stream is sliced by:

- `[:2]`
- `[2:4]`
- `[4:6]`

then the stop-address array is:

- `[2, 4, 6]`

Rules:

- strictly increasing
- each stop address must fit within `address_width_bits`
- the final stop address must be less than or equal to the length of the value stream
- if there are `N` stop addresses, they yield `N + 1` decoded values

Pseudo-code:

```text
function validate_stop_addresses(stops, value_stream_length):
    if length(stops) == 0:
        return

    prev = None
    for s in stops:
        if s < 0:
            raise InvalidStructure("negative stop address")
        if prev is not None and s <= prev:
            raise InvalidStructure("stop addresses must be strictly increasing")
        if s > value_stream_length:
            raise InvalidStructure("stop address exceeds value stream length")
        prev = s
```

---

### 5. Value stream

The value stream is a continuous bit string formed by concatenating variable-width binary values.

Example values:

- `1`
- `10`
- `10`
- `1`
- `100`
- `0`

become:

- `1101011000`

The stop-address array defines how to split it back into those tokens.

Pseudo-code:

```text
function slice_value_stream(value_stream, stops):
    values = []
    start = 0

    for stop in stops:
        values.append(value_stream[start:stop])
        start = stop

    values.append(value_stream[start:])

    return values
```

---

## Full decode algorithm

```text
function decode_samras(bitstream):
    cursor = 0

    (address_width_bits, cursor) = decode_unary_width(bitstream, cursor)
    (stop_count_width_bits, cursor) = decode_unary_width(bitstream, cursor)

    stop_count_bits = bitstream[cursor : cursor + stop_count_width_bits]
    if length(stop_count_bits) != stop_count_width_bits:
        raise InvalidStructure("truncated stop-count field")
    stop_count = binary_to_int(stop_count_bits)
    cursor += stop_count_width_bits

    stops = []
    for i from 1 to stop_count:
        stop_bits = bitstream[cursor : cursor + address_width_bits]
        if length(stop_bits) != address_width_bits:
            raise InvalidStructure("truncated stop-address array")
        stops.append(binary_to_int(stop_bits))
        cursor += address_width_bits

    value_stream = bitstream[cursor:]

    validate_stop_addresses(stops, length(value_stream))

    raw_value_tokens = slice_value_stream(value_stream, stops)

    if any(token == "" for token in raw_value_tokens):
        raise InvalidStructure("empty value token")

    values = []
    for token in raw_value_tokens:
        values.append(binary_to_int(token))

    addresses = derive_addresses_from_child_counts(values)

    return {
        "address_width_bits": address_width_bits,
        "stop_count_width_bits": stop_count_width_bits,
        "stop_count": stop_count,
        "stop_addresses": stops,
        "value_tokens": raw_value_tokens,
        "values": values,
        "addresses": addresses,
    }
```

---

## Full encode algorithm from an address set

This is the reverse process.

### Step 1: validate address set

The addresses must satisfy:

- each segment is a positive integer,
- root ordinals are contiguous from `1`,
- each node's child ordinals are contiguous from `1`,
- every non-root address has an existing parent.

Pseudo-code:

```text
function validate_address_set(addresses):
    normalized = sort_addresses(addresses)

    parent_to_children = {}
    roots = []

    for address in normalized:
        segments = parse_address(address)

        if length(segments) == 1:
            roots.append(segments[0])
        else:
            parent = join_segments(segments[:-1])
            child_ordinal = segments[-1]

            if parent not in normalized:
                raise InvalidStructure("missing parent for address " + address)

            parent_to_children[parent].append(child_ordinal)

    if roots != [1, 2, ..., length(roots)]:
        raise InvalidStructure("roots must be contiguous from 1")

    for parent, ordinals in parent_to_children.items():
        sorted_ordinals = sort(ordinals)
        expected = [1, 2, ..., length(sorted_ordinals)]
        if sorted_ordinals != expected:
            raise InvalidStructure("child ordinals must be contiguous for " + parent)
```

---

### Step 2: compute child counts in breadth-first order

```text
function child_counts_from_addresses(addresses):
    validate_address_set(addresses)

    parent_to_children = build_parent_child_map(addresses)
    root_count = count_roots(addresses)

    values = [root_count]
    queue = []

    for i from 1 to root_count:
        queue.push(str(i))

    while queue is not empty:
        node = queue.pop_front()
        children = sorted_children_of(node, parent_to_children)
        values.append(length(children))

        for child in children:
            queue.push(child)

    return values
```

---

### Step 3: encode value tokens as minimal binary

```text
function minimal_binary(value):
    if value == 0:
        return "0"
    return binary(value)
```

---

### Step 4: compute stop addresses

If the token binaries are:

- `t0, t1, ..., tn`

then stop addresses are cumulative exclusive endpoints for every token except the last.

```text
function compute_stop_addresses(value_tokens):
    stops = []
    total = 0

    for i from 0 to length(value_tokens) - 2:
        total += length(value_tokens[i])
        stops.append(total)

    return stops
```

---

### Step 5: compute widths and final bitstream

```text
function width_bits_for_integer(value):
    if value == 0:
        return 1
    return length(binary(value))

function encode_samras_from_addresses(addresses):
    values = child_counts_from_addresses(addresses)

    value_tokens = []
    for v in values:
        value_tokens.append(minimal_binary(v))

    stop_addresses = compute_stop_addresses(value_tokens)

    value_stream = concatenate(value_tokens)

    max_stop = max(stop_addresses) if length(stop_addresses) > 0 else 0
    address_width_bits = width_bits_for_integer(max_stop)

    stop_count = length(stop_addresses)
    stop_count_width_bits = width_bits_for_integer(stop_count)

    out = ""
    out += encode_unary_width(address_width_bits)
    out += encode_unary_width(stop_count_width_bits)
    out += encode_fixed_width_binary(stop_count, stop_count_width_bits)

    for stop in stop_addresses:
        out += encode_fixed_width_binary(stop, address_width_bits)

    out += value_stream

    return {
        "bitstream": out,
        "values": values,
        "value_tokens": value_tokens,
        "stop_addresses": stop_addresses,
        "address_width_bits": address_width_bits,
        "stop_count_width_bits": stop_count_width_bits,
        "stop_count": stop_count,
    }
```

---

## Canonical mutation rule

When a user adds or edits a SAMRAS node, the engine must not edit the raw magnitude directly.

The correct mutation process is:

1. decode current SAMRAS structure
2. reconstruct the canonical address tree
3. apply address-level mutation
4. revalidate address continuity
5. regenerate breadth-first child counts
6. regenerate stop-address table
7. regenerate final bitstream
8. write that new canonical structural magnitude

Pseudo-code:

```text
function add_child_to_address(existing_addresses, parent_address):
    if parent_address not in existing_addresses:
        raise InvalidStructure("parent address does not exist")

    child_ordinals = children_of(parent_address, existing_addresses)
    next_child_ordinal = length(child_ordinals) + 1

    new_address = parent_address + "-" + str(next_child_ordinal)

    updated = copy(existing_addresses)
    updated.add(new_address)

    validate_address_set(updated)

    return {
        "new_addresses": updated,
        "new_address": new_address,
        "new_samras": encode_samras_from_addresses(updated),
    }
```

---

## Example mutation

If:

- `1-1-3-3-5-6-7-2-1-1` exists
- and it currently has only one child:
  - `1-1-3-3-5-6-7-2-1-1-1`

then adding another cultivar gives:

- new child = `1-1-3-3-5-6-7-2-1-1-2`

The engine must then:

- increment that parent's child count,
- regenerate the breadth-first value stream,
- recompute stop addresses,
- rewrite the final SAMRAS magnitude.

The new address is valid only after the structural value is rebuilt.

---

## Formal validity conditions

A SAMRAS structure is valid if and only if all are true:

1. it is created in reference to `0-0-5`
2. width fields decode correctly
3. stop count decodes correctly
4. stop-address array length matches stop count
5. stop-address array is strictly increasing
6. stop-address array does not exceed value-stream length
7. value stream yields no empty slices
8. first decoded value is a valid root count
9. breadth-first child-count decode consumes all tokens exactly
10. every derived address is unique
11. every later SAMRAS-space reference points to an address that actually exists in the decoded structure

---

## Formal invalidity conditions

A SAMRAS structure is invalid if any of the following occur:

- width field is unterminated
- stop-count field is truncated
- stop-address array is truncated
- a stop address decreases or repeats
- a stop address exceeds the value stream
- a slice is empty
- the breadth-first queue underflows or overflows relative to the token count
- unused tokens remain after the queue empties
- a referenced address uses a child ordinal that exceeds what the structure allows
- roots or children are non-contiguous

---

## Practical implementation notes

### Engine ownership
These semantics should be owned by the data engine / shared core.

### UI role
The UI should edit:

- address tree
- node additions
- node removals
- node inspection

The UI should not be responsible for raw SAMRAS bit manipulation.

### Canonical write rule
Canonical save should write the structural bitstream only.
Legacy hyphenated human-authored SAMRAS magnitudes should be migration-only inputs.

---

## Recommended module split

Suggested shared-core modules:

- `samras_codec.py`
  - encode/decode bitstream
- `samras_structure.py`
  - internal structure model
- `samras_validation.py`
  - validity predicates
- `samras_mutation.py`
  - add/remove/rebuild operations
- `samras_workspace_adapter.py`
  - shape for sandbox/resource editor use

---

## Final summary

A SAMRAS structural datum should be understood as:

- a serialized breadth-first child-count forest,
- with variable-width binary values,
- parsed by a stop-address array,
- from which addresses are derived by ordinal child position.

The correct human-facing model is:

- **edit addresses / nodes**
- **engine regenerates structure**
- **engine rewrites canonical magnitude**

That is the logical basis required for flawless validation and mutation.
