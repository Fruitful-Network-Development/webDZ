# 2 Unified Mental Model of CPSC 421 Thus Far

## The shortest accurate model

The cleanest way to unify the course is to treat it as one long redesign of `srcFacts`, with design vocabulary above it and UML as the language for making the redesign explicit. Early meetings establish design layers, quality characteristics, decomposition, naming, separate compilation, coding rules, and free-function roles; the projects then apply those ideas to move `srcFacts` from a monolithic `main()` to extracted free functions, then a namespace and class wrapper, then full inversion of control with handlers, and then a Template Method plus handler-based architecture. In parallel, the course builds a stable modeling grammar—sequence diagrams for behavior and class diagrams for structure—and repeatedly pairs note sets with same-topic crosswords so terminology and modeling stay coupled. citeturn10view0turn10view1turn31view0turn31view1turn31view2turn32view0turn0view2turn2view2turn28view1

```text
CPSC 421 thus far
├─ Design foundations
│  ├─ layers of design
│  ├─ software design characteristics
│  ├─ cohesion / coupling / dependencies
│  └─ concerns and separation of concerns
├─ Function-level design rules
│  ├─ algorithmic decomposition
│  ├─ parameter direction: IN / OUT / INOUT
│  ├─ free-function stereotypes
│  ├─ naming and method naming standards
│  ├─ separate compilation and header roles
│  └─ coding style and vertical development
├─ srcFacts case-study evolution
│  ├─ Project 1: extract XML free functions
│  ├─ Project 2: namespace + XMLParser + diagrams
│  ├─ Project 3: IoC + lambda handlers
│  └─ Project 4: Template Method + handlers
├─ Modeling grammar
│  ├─ sequence diagrams
│  ├─ UML class diagrams
│  ├─ multiplicity
│  └─ class relationships
├─ OO runtime mechanics
│  ├─ constructors and initialization
│  ├─ encapsulation and scope
│  ├─ callbacks / IoC / lambdas
│  ├─ dispatch / vtables / virtual destructors
│  └─ handlers, APIs, PIMPL
└─ Safety and extensibility layer
   ├─ resource management and RAII
   ├─ errors and exception handling
   ├─ SOLID
   └─ design patterns
      ├─ Template Method
      ├─ Factory Method
      ├─ Command
      ├─ Strategy
      ├─ Composite
      ├─ Adapter
      └─ Facade
```

If you want one sentence for the whole semester, it is this: **separate concerns, expose only the right interfaces, preserve behavior while improving extensibility, and be able to explain the result in UML.** Most topics are either evaluation criteria for that goal, rule sets for implementing it in C++, or modeling tools for expressing it precisely. citeturn12view0turn18view0turn18view1turn18view2turn25view0turn14view1turn13view1turn13view2

## The refactoring backbone

Project 1 defines the original design problem. `srcFacts` already has high scalability and performance, but very low or nonexistent modularity, extensibility, reusability, and maintainability. The assignment is not to invent a new parser; it is to **extract low-level XML parsing into free functions** in `xml_parser.hpp/.cpp` while keeping output behavior unchanged. That project also explicitly says not to solve the problem with classes yet, which makes early course material fundamentally about decomposition, interface boundaries, and free-function design rather than classic class hierarchies. citeturn31view0turn11view0turn11view1

Project 2 formalizes those earlier ideas. First the extracted functions move into a namespace; then an `XMLParser` class is introduced with methods mirroring the free-function interface; then parsing state migrates from `srcfacts.cpp` into private fields; then the free-function calls are inlined into the class implementation. At the same time, the project makes sequence and class diagrams first-class deliverables that must track each design state. The strongest project rule is also conceptually important: parser files may not mention `srcML` concerns, so the parser boundary must remain generic XML-facing rather than application-facing. citeturn31view1turn20view0turn13view2

Project 3 is the hinge point of the semester. Its statement says the main remaining problem is the large `while` loop with nested conditionals around `srcFacts` concerns, and the solution is **full inversion of control**: one public `parse()` plus registered handlers for XML extension points. The parser must now serve `srcfacts`, `xmlstats`, and `identity`, and application-specific concerns are forbidden from remaining in the shared parser. That is the moment when the course stops being mainly about extraction and starts being about extensibility architecture. citeturn31view2turn15view2turn15view1

Project 4 then converts that callback architecture into an inheritance-based one. First `XMLParser` is redesigned around the Template Method pattern, where extension points become virtual methods in specialized parser subclasses. Then user-defined processing is split again into an `XMLParserHandler` interface, so the parsing engine and application-specific behavior are decoupled. In one continuous line, the course moves through **free functions → namespace → class wrapper → stateful parser → IoC with handlers → Template Method → extracted handler interface**. That progression is the best single “spine” for your conceptual diagram. citeturn32view0turn22view1turn17view2

The workflow rules support the same interpretation. Vertical development is preferred because each commit should reflect one functional improvement, not one language-layer edit, and the Concerns notes define concern separation as the main tool for reducing complexity, improving modularity, reuse, testing, and maintainability. The March Convert exercises are best understood as repeated practice in marking, isolating, and rearranging concern clusters rather than merely rewriting syntax. citeturn24view0turn12view0turn3view3turn4view0turn4view1

## The modeling grammar

The course’s second trunk is modeling. Sequence diagrams are used to express **one concrete scenario**: participants, activations, calls, returns, and flow of control over time. UML class diagrams express **static structure**: class name, attributes, operations, visibility, parameter directions, multiplicity, static members, and notes. Project 2 makes both diagrams required living artifacts, and Project 4 requires updating them again as the architecture changes, which means the class is treating diagrams as design state, not decorative documentation. citeturn13view1turn13view2turn13view3turn31view1turn32view0

For UML-style exam questions, the most useful translation rules are direct. If a class is used only as a parameter or local variable, that is a **dependency**. If one class stores another as a field, that is an **association**. If the source controls the target’s lifetime, strengthen it to **composition**. If the target is externally created or shared, consider **aggregation**. If one type must be substitutable for another in behavior as well as interface, that is **generalization**. The notes also rank relationship strength and explicitly warn that stronger relationships mean stronger coupling and more rigid design. citeturn20view0turn20view1turn20view2

The parameter-direction rules also map cleanly between code and diagrams. IN usually corresponds to pass-by-value for small scalar data, or `const` reference / `const` pointer for larger or non-scalar inputs. OUT and IN/OUT are typically references, pointers, or returns depending on how data must flow. That mapping appears first in decomposition material and then again in UML operation-parameter syntax, so function signatures and UML signatures are not separate topics in this class; they are two notations for the same design decision. citeturn11view0turn13view3

A subtle but important modeling idea is that the UML model is not the implementation language. The class notes explicitly separate UML types from C++ choices, and the Apr. 2 class reminds students that UML `String` does not force `std::string`; the implementation could use `std::string_view`, an optional string, or some other representation. Multiplicity drives representation decisions more than name matching does: multivalued properties suggest containers, while single-valued optionals suggest optional-like representations. citeturn13view3turn13view2turn5view0

## The implementation rulesets

Most early and mid-semester “rules” exist to defend interface quality. Separate compilation says real programs are split across headers and implementation files; headers serve callers, implementations hide details, include files must be self-sufficient, and `.cpp` files must never be included. The notes repeatedly frame header design as caller-facing interface design, not a convenience layer for the implementer. The Feb. 5 class makes that even more explicit by saying an include file exists for developers who need to call a function and should provide enough to call it correctly, but nothing extra. citeturn25view0turn1view3

The core low-level rules that seem worth memorizing as a **ruleset layer** are these:

- **Parameter-direction discipline.** Algorithmic decomposition ties IN / OUT / INOUT to concrete C++ parameter forms, and the Feb. 26 class imposes zero tolerance on three recurring mistakes: passing `std::string` by value, passing `std::vector<>` by value, and adding `const` to scalar pass-by-value parameters. That is not presented as style; it is presented as a fundamental design error. citeturn11view0turn28view0
- **Naming discipline.** Function names should use a recognizable naming style, grammatical structure, verb phrases for actions, dictionary terms, full words, and standard abbreviations only. The course then overlays stereotype names on top of that vocabulary—free-function `Accessor::predicate`, `Accessor::property`, `Mutator::command`, and method roles like `get`, `set`, `property`, and `command`—so naming and classification work together. The class also explicitly warns not to combine incompatible roles in one function or method. citeturn24view2turn11view1turn15view0turn2view1
- **Scope and encapsulation discipline.** Minimize scope whenever possible, prefer local variables over wider exposure, keep data members private, and do not expose stored versus derived data, implementation details, or internal structure. Encapsulation is defined as bundling data with the methods that operate on it, while information hiding is the act of restricting representation leakage. citeturn29view1turn14view1
- **Process and coding discipline.** Coding style is treated as part of design communication: consistent indentation, logical file order, comments before cohesive code sections, descriptive variable names, initializing locals where declared, using standard-library algorithms when appropriate, and working vertically so each commit reflects a coherent improvement. citeturn25view1turn26view0turn26view1turn24view0

The important synthesis is that these rules are not isolated trivia. They are the **implementation-side support beams** for the larger course goals of low coupling, high cohesion, caller-friendly APIs, and separate concerns. citeturn18view0turn18view1turn18view2turn21view0

## The runtime and safety layer

After the midterm, the course leans harder into runtime semantics. Constructors initialize already-allocated object memory; they do not allocate the whole object themselves. Field constructors run before the object constructor body, and member-initialization lists matter because they determine how fields are constructed. That runtime view then connects directly to dispatch: free functions, non-virtual methods, static methods, and calls through non-pointer/non-reference objects are statically dispatched, while virtual calls through pointers or references are dynamically dispatched. Vtables are the indirection mechanism that makes late binding work. citeturn14view0turn16view1turn16view2

That leads directly to destructor design. The virtual-destructor notes show that if a base pointer refers to a derived object and the base destructor is not virtual, the derived cleanup does not run correctly. The course conclusion is blunt: any base class with a virtual method should have a virtual destructor, and if no manual cleanup is needed, the destructor should usually be defaulted. This is a very precise example of how an OO modeling choice becomes a concrete C++ rule. citeturn16view3

Resource safety is framed as a design problem, not just a debugging problem. “Resource” includes memory, file handles, network connections, locks, and database connections, and the class emphasizes leaks, double frees, invalid use, and resource exhaustion as systemic failures. RAII then becomes the central idiom: acquire in the constructor, release in the destructor, tie validity to object lifetime, and prefer smart-pointer or other RAII-based ownership over ad hoc manual cleanup. citeturn19view0turn19view1

The exception-handling material builds directly on that. Error-return codes are shown as tedious and easy to misuse across call chains, while exception handling separates the normal path from the error path and relies on stack unwinding to propagate failure. But the notes also insist that exceptions only work cleanly when local variables and data members already have RAII semantics, because C++ has no `finally` and the destructor of a partially constructed outer object cannot rescue non-RAII fields. That is why RAII, virtual destructors, and exceptions belong in the same conceptual cluster. citeturn21view1turn21view2turn19view2

The same late-semester layer extends upward into API design. APIs are described as the large-scale mechanism for separation of concerns; good APIs trade internal complexity for lower external complexity, and they must avoid leaking client-specific concerns into shared interfaces. PIMPL is the natural continuation of that idea at compile time: the public header stops exposing implementation-field types and their include dependencies, so interface stability improves even when internals change. citeturn21view0turn23view5turn18view1

## The pattern and assessment layer

The late-semester design patterns are best understood as named answers to the extensibility problems the projects create. Template Method varies steps of an algorithm through inheritance and directly produces inversion of control. Handlers refine that design by extracting a smaller, more cohesive interface from a large abstract class. Strategy varies a family of algorithms through delegation rather than inheritance. Command turns a request into an object and is explicitly framed as an OO replacement for callbacks. Composite handles recursive part–whole trees uniformly. Adapter converts a mismatched existing interface into the interface clients need. Facade provides a simpler front door to a more complex subsystem. Factory Method moves object-creation decisions into subclasses. All of that sits under the SOLID umbrella, which gives the principle-level vocabulary for why these patterns improve maintainability and extensibility. citeturn22view1turn17view2turn23view1turn27view0turn23view2turn23view3turn23view4turn22view2turn23view0

The assessment signal is also fairly clear. Before the midterm, the class explicitly says the software-design-characteristics list matters, required definitions matter, naming and parameter passing are on the midterm, and sequence diagrams are on the midterm; the midterm itself is a paper exam. After the midterm, the course explicitly flags Names, Static Dispatch, and Dynamic Dispatch as strong final-exam candidates. Across the semester, meeting after meeting pairs note pages with same-topic crosswords and then follows those with code or diagram work. Taken together, that strongly suggests the exams are selecting for **precise vocabulary plus translation skill**: given a term, identify its rule and represent it in code/UML; given code or a diagram, identify the principle, stereotype, relationship, or pattern it instantiates. citeturn2view0turn28view1turn28view2turn28view3turn28view4turn0view2turn2view2turn5view3turn6view1