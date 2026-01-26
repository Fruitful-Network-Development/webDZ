# Fruitful Admin Console UI Ontology (Design Spec)

## Purpose
Design the admin console for the `fruitful-admin` meta-admin so that authority, ontology, and structure remain explicit and unambiguous. This UI must make it impossible to confuse structure with data or to collapse MSS/SAMRAS concepts into generic CRUD.

---

## 1) Structured UI Outline (Pages, Tabs, Context Switches)

### A. Admin Console Root (`/admin`) — **Overview**
**Goal:** Answer: *“What worlds exist, and where can I act?”*

**Primary elements:**
- **Client Summary Cards** (per tenant):
  - `tenant_id`
  - status (active / suspended)
  - structural readiness indicators:
    - MSS present
    - archetypes defined
    - tables provisioned
- **Primary Actions:**
  - **Add Client** (stub CTA with wiring pending indicator)
  - **Enter Client Console** (context switch)
- **Platform-level sections:**
  - **My Data Tables** (platform-owned)
  - **My Lists** (platform-owned)
  - **System Shape** (MSS + SAMRAS + Registry health)

**Authority note:** This page is global to the platform and belongs only to the `fruitful-admin` realm.

---

### B. Top-Level Admin Navigation (Tabs)
**Objective:** Make authority boundaries explicit by purpose.

- **Overview**
  - “Where are the worlds and what is their structural state?”
- **Clients**
  - “Which client worlds exist and are they structurally valid?”
- **Platform Data**
  - “Platform-owned tables and lists (registry-backed)”.
- **System**
  - “MSS profiles, SAMRAS layouts, and archetype registry health.”

**Why these exist:**
- **Overview** is for cross-tenant situational awareness.
- **Clients** is tenant structure readiness only (not business records).
- **Platform Data** is the admin’s own data space (fruitful realm).
- **System** is the canonical shape authority layer: MSS + SAMRAS + registry.

---

### C. Clients Tab (`/admin/clients`)
**Goal:** Answer: *“Which worlds exist, and are they structurally valid?”*

**Per client card:**
- `tenant_id` + status
- Structural readiness panel:
  - MSS profile provisioned
  - Archetype coverage
  - Manifest status (tables bound)
- Actions:
  - **Enter Client Console**
  - **Inspect MSS readiness** (read-only)
  - **Inspect structural data readiness** (archetypes, manifests, tables)

**Explicit exclusion:** No direct access to tenant business records from this view.

---

### D. Client Console Context (Admin View) (`/admin/client/<tenant_id>`)
**Goal:** Clear context switch into a client’s world with admin lens.

**Context switch requirements:**
- Persistent header banner: `CLIENT CONTEXT: <tenant_id>`
- Exit to Admin Overview control
- Audit-friendly breadcrumbs (“Admin → Client → Section”)

**Client Console Tabs:**
1. **Data**
   - **MSS Profiles** (tenant-scoped identity anchors)
   - **Archetypes** (shape contracts)
   - **Provisioned Tables** (containers)
2. **Services** (Scaffold)
   - Billing
   - Email / Notifications
3. **Identity**
   - Roles
   - Access boundaries

**Admin CAN:**
- Provision and validate structural shape (MSS, archetypes, manifests, tables)
- Observe readiness and access boundaries
- Enter client console modules to inspect structure and permissions

**Admin CANNOT (by default):**
- Modify or browse client business data outside provisioned admin modules
- Collapse structure with content or bypass shape constraints

---

### E. Platform Data (`/admin/platform` or `/admin/data`)
**Goal:** Emphasize platform-owned, registry-backed data space.

**Sections:**
- **Tables**
  - Registry-backed
  - Archetype-validated
  - Not tenant-scoped unless explicitly bound
- **Lists**
  - Ordered references (not categories)
  - Used to resolve ordinals and structural linkage

**Message:** “You are shaping the space, not filling it.”

---

## 2) Component Hierarchy (Conceptual)

```
AdminShell
├─ GlobalHeader
│  ├─ AdminIdentityBadge (fruitful-admin)
│  ├─ ContextIndicator (global vs client)
│  └─ PrimaryActions (Add Client, Enter Client)
├─ AdminNavigation
│  ├─ OverviewTab
│  ├─ ClientsTab
│  ├─ PlatformDataTab
│  └─ SystemTab
└─ MainContent
   ├─ OverviewDashboard
   │  ├─ ClientSummaryGrid
   │  ├─ PlatformDataSummary
   │  └─ SystemShapeSummary
   ├─ ClientsView
   │  ├─ ClientCard
   │  │  ├─ ReadinessPanel
   │  │  └─ ClientActions
   │  └─ StructuralReadinessFilters
   ├─ PlatformDataView
   │  ├─ TableRegistryPanel
   │  └─ ListsPanel
   └─ SystemView
      ├─ MSSProfileInspector
      ├─ ArchetypeRegistryPanel
      ├─ ManifestBindingsPanel
      └─ SamrasLayoutPanel

ClientContextShell
├─ ClientContextHeader (tenant_id, exit control)
├─ ClientConsoleTabs
│  ├─ DataTab
│  ├─ ServicesTab
│  └─ IdentityTab
└─ ClientConsoleContent
   ├─ DataTab
   │  ├─ MSSProfiles
   │  ├─ Archetypes
   │  └─ ProvisionedTables
   ├─ ServicesTab
   │  ├─ BillingScaffold
   │  └─ EmailScaffold
   └─ IdentityTab
      ├─ RolesPanel
      └─ AccessBoundariesPanel
```

---

## 3) Rationale

### A. Preserving Phase‑5 guarantees
- **Shape precedes meaning:** The UI privileges Archetypes, Manifests, and SAMRAS layouts before any data operations. Structure must be explicitly provisioned before containers (Tables/Lists) are created or used.
- **Tables are containers, Lists are references:** The UI labels tables as provisioned containers and lists as ordered references, preventing semantic confusion or “category” misuse.
- **SAMRAS paths as coordinates:** SAMRAS appears in System / Structural tooling, emphasizing navigational coordinates rather than labels or tags.

### B. Authority boundaries enforced by navigation
- **Global vs Client contexts are visibly distinct:** The AdminShell is global; ClientContextShell is explicitly a context switch with a dedicated header and exit control.
- **Clients tab excludes business records:** Only structural readiness and entry actions are available; data content remains out of scope by default.
- **Platform Data is explicitly admin-owned:** This prevents accidental tenant privilege bleed by partitioning the platform data plane.

### C. Scalability to future ontology layers
- **System tab is extensible:** new modules (taxonomy, additional registries, future governance checks) fit under System without altering core authority model.
- **Client console mirrors user console:** Elevating permissions without redesigning layout avoids confusion and reinforces consistent shape boundaries.
- **Component hierarchy is modular:** Structural inspectors (MSS, Archetypes, Manifests, SAMRAS) can evolve independently.

---

## 4) Success Conditions (Explicit UI Guardrails)
The design ensures that it is **impossible** to:
- Confuse **structure** with **data** (shape panels always precede containers).
- Grant tenants unintended authority (client context is isolated and explicit).
- Create tables without explicit provisioning (tables only exist via manifest + archetype linkage).
- Evolve shape silently (System tab surfaces archetype, manifest, and SAMRAS readiness).

---

## 5) Summary
This admin console design preserves MSS/SAMRAS ontology by making structure-first navigation unavoidable, clearly separating global authority from client context, and constraining data access to properly provisioned, validated containers. The result is a scalable, phase‑aligned UI that reflects the Fruitful Network’s strict governance model.
