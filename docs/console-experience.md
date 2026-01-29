# Console Experience

## Core console design

Core is what must remain stable for every tenant and every module. It is the
operating system of the platform.

Core contract: modules plug into the shell; the shell does not embed business
logic.

### Identity and tenancy

- Tenant selection and routing (`tenant_registry`, `/t/<tenant>/...`)
- Session/auth integration (Keycloak/OIDC)
- Authorization primitives (root-admin vs tenant-admin vs tenant-user)
- Provisioning gate ("not provisioned" via MSS profile)

Core contract: every request has a resolved tenant context + user context, or a
deterministic error/redirect.

### Data control plane (MSS)

The platform is a control plane for identity and data access; external business
logic must call through the BFF to reach data. Static client frontends and
infrastructure services remain outside the console boundary.

### Runtime data plane

**Platform data**: shaping the space, not filling it.

Tables:

- Registry-backed
- Archetype-validated
- Not tenant-scoped unless explicitly bound

Lists:

- Ordered references (not categories)
- Used to resolve ordinals and structural linkage

### Data runtime plane (generic CRUD)

- General table provisioning and JSONB storage.
- Generic tenant data endpoints:
  - validate against archetype
  - store JSONB data
  - resolve ordinals via lists/local domain
  - enforce ref domains (taxonomy/SAMRAS/local)

Core contract: any module can store and query domain data through the same
validated CRUD mechanism.

### UI shell

- Admin console shell (navigation, tenant selection, status cards)
- Tenant console shell (module menu, consistent layout, `/me`)

Core contract: modules plug into the shell; the shell does not embed business
logic.

## Module taxonomy

**Platform modules**

A platform module is a reusable capability that many tenants might use, but
that is not required for the platform to function. Platform module contract: it
uses core identity + data contracts; it does not redefine them.

**Tenant modules**

Tenant modules are use cases for a specific type of tenant. They are often thin
UI + workflows on top of core and platform modules. They are not universally
reusable but are built using the same core and platform components.

## Core vs module classifier

When deciding "core vs module," ask:

1. Does every tenant require it to exist at all? If yes → core. If no → module.
2. Does it change the meaning of the canonical data model? If yes → core. If it
   just adds new archetypes/tables/workflows → module.
3. Would breaking it take down the platform? If yes → core. If it only disables
   one capability → module.
4. Is it reusable across different tenant types? If yes → platform module. If
   specific to one tenant type → tenant module.
5. Does it require privileged infrastructure actions (AWS, DNS, SES)? Usually
   module (integration), but the authz + audit primitives it needs belong in
   core.

## Example platform modules

**Email management**

- Manages email domains, mailboxes/aliases, forwarding rules, mailing lists, and
  role-based access.
- Depends on:
  - MSS profile hierarchy (board member vs farm contact)
  - Tenant context and authz
  - Local domain/list primitives for groups and subscriptions
  - Generic data CRUD for configuration state
- Should not:
  - be baked into tenant routing or base admin pages
  - change how archetypes or general tables work

**Billing**

- Tracks subscriptions, invoices, and entitlements (modules enabled often driven
  by billing state).
- Often admin-only with minimal tenant user exposure.

**Integrations (Square/Zettle/PayPal)**

- Stores API credentials, webhooks, device inventories.
- Publishes events to other modules (orders, payments).

Platform module contract: it uses core identity + data contracts; it does not
redefine them.

## Example tenant modules (business apps)

Tenant modules are tenant-type specific:

- Industry network (participant farms, board members, programs)
- Email domains + board mailing lists
- Donor/contact CRM
- Customer subscriptions + newsletter
- POS device inventory
- Payment integration dashboards

Tenant modules differ from platform modules because they are not universally
reusable. They can still be built using the same core + platform components.

## Structured modules pattern (intended)

Core:

- `routes/common.py` (tenant context, current user, error responses)
- `routes/auth.py` (login/callback)
- `routes/admin.py` (core admin: tenants, MSS profiles, archetypes, manifest, SAMRAS)
- `routes/tables.py` (generic CRUD)
- `tenant_registry.py`, `db.py`, `authz.py`

Platform modules:

- `routes/modules/email.py`
- `routes/modules/billing.py`
- `routes/modules/integrations_paypal.py` (or `routes/integrations/paypal/...`)
- `templates/modules/email/*.html`
- `templates/modules/billing/*.html`
- `static/modules/email/*.js`

Tenant console routing:

- `/t/<tenant_id>/console/<module>` loads the module template + API endpoints.

Prefer module data in archetypes/manifests wherever possible so the module is
mostly UI + orchestration.

## Admin console root

The **admin console** is restricted to platform administrators and tenant
administrators. It provides tools for tenant management, membership, and schema
definition. The **tenant console** is available to authenticated users and
exposes tenant-specific data according to schemas defined by tenants. Both
consoles use a shared UI, configured at runtime based on roles and manifests.

**Primary elements**

- **Client summary cards**:
  - `tenant_id`
  - status (active / suspended)
  - structural readiness indicators:
    - MSS present
    - archetypes defined
    - tables provisioned
  - Per client card:
    - `tenant_id` + status
    - Structural readiness panel:
      - MSS profile provisioned
      - Archetype coverage
      - Manifest status (tables bound)
    - Actions:
      - **Enter Client Console**
      - **Inspect MSS readiness** (read-only)
      - **Inspect structural data readiness** (archetypes, manifests, tables)
  - Explicit exclusion: no direct access to tenant business records from this
    view.
- **Primary actions**:
  - **Add Client** (stub CTA with wiring pending indicator)
  - **Enter Client Console** (context switch)
- **Platform-level sections**:
  - **My Data Tables** (platform-owned)
  - **My Lists** (platform-owned)
  - **System Shape** (MSS + SAMRAS + Registry health)

Authority note: this page is global to the platform and belongs only to the
`fruitful-admin` realm.

**Navigation**

- **Overview**: Where are the worlds and what is their structural state?
  - Cross-tenant situational awareness.
- **Clients**: Which client worlds exist and are they structurally valid?
  - Tenant structure readiness only (not business records).
- **Platform Data**: Platform-owned tables and lists (registry-backed).
  - The admin's own data space (fruitful realm).
- **System**: MSS profiles, SAMRAS layouts, and archetype registry health.
  - Canonical shape authority layer: MSS + SAMRAS + registry.

## Admin client page

Context switch requirements:

- Persistent header banner: `CLIENT CONTEXT: <tenant_id>`
- Exit to Admin Overview control
- Audit-friendly breadcrumbs ("Admin → Client → Section")

Client Console Tabs:

1. **Data**
   - **MSS Profiles** (tenant-scoped identity anchors)
   - **Archetypes** (shape contracts)
   - **Provisioned Tables** (containers)
2. **Services** (scaffold)
   - Billing
   - Email / Notifications
3. **Identity**
   - Roles
   - Access boundaries

Admin can:

- Provision and validate structural shape (MSS, archetypes, manifests, tables)
- Observe readiness and access boundaries
- Enter client console modules to inspect structure and permissions

Admin cannot (by default):

- Modify or browse client business data outside provisioned admin modules
- Collapse structure with content or bypass shape constraints

## Component hierarchy (conceptual)

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
