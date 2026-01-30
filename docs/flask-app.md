# Flask BFF architecture (Phase 5 alignment)

## Responsibility map (current dependencies and coupling)

**MSS profile + role checks**
- Session enrichment on login pulls MSS profile hierarchy (`msn_id`, `parent_msn_id`, `role`).【F:srv/compose/platform/flask-bff/routes/auth.py†L1-L210】
- Root/admin decisions and provisioning gates are centralized in platform policy helpers; tenant-console access logs decisions and checks MSS provisioning state.【F:srv/compose/platform/flask-bff/core/policy.py†L1-L181】【F:srv/compose/platform/flask-bff/tenants/access.py†L1-L69】
- Admin schema provisioning (`general_table`) depends on the MSS `msn_id` to derive table names.【F:srv/compose/platform/flask-bff/admin/routes.py†L23-L26】【F:srv/compose/platform/flask-bff/admin/routes.py†L699-L823】

**Tenant registry + tenant runtime**
- Tenant registry is file-backed (`data/tenants`) and used by login validation, tenant console, and admin tenant CRUD endpoints.【F:srv/compose/platform/flask-bff/tenants/registry.py†L1-L217】【F:srv/compose/platform/flask-bff/routes/auth.py†L1-L210】【F:srv/compose/platform/flask-bff/admin/routes.py†L23-L207】
- Tenant console uses registry data and console module configuration to render the tenant UI.【F:srv/compose/platform/flask-bff/routes/tenant.py†L1-L57】【F:srv/compose/platform/flask-bff/tenants/console_modules.py†L1-L11】

**Manifest + archetypes + admin flows**
- Admin API endpoints are responsible for archetypes, manifest bindings, and general table provisioning (DB-backed).【F:srv/compose/platform/flask-bff/admin/routes.py†L118-L987】
- SAMRAS validation is treated as a platform domain helper used during archetype creation.【F:srv/compose/platform/flask-bff/core/domains/samras.py†L1-L25】【F:srv/compose/platform/flask-bff/admin/routes.py†L23-L27】

**Coupling points addressed by refactor**
- Access checks, provisioning gates, and MSS role interpretation now run through `core.policy` and `core.mss_profile` instead of being scattered in route files, reducing duplication in admin/tenant flows.【F:srv/compose/platform/flask-bff/core/policy.py†L1-L181】【F:srv/compose/platform/flask-bff/core/mss_profile.py†L1-L35】【F:srv/compose/platform/flask-bff/tenants/access.py†L1-L69】
- Tenant-specific console access and module selection are isolated in `tenants/` helpers, keeping admin routes focused on admin responsibilities.【F:srv/compose/platform/flask-bff/tenants/access.py†L1-L69】【F:srv/compose/platform/flask-bff/tenants/console_modules.py†L1-L11】

## Target module layout (implemented)

```
flask-bff/
  admin/
    routes.py            # Admin HTML + JSON endpoints (existing behavior)
  core/
    mss_profile.py       # Single MSS profile source of truth (msn_id/user hierarchy)
    policy.py            # Role checks, guard helpers, forbidden/not-provisioned responses
    domains/
      samras.py          # Global SAMRAS helpers
  tenants/
    registry.py          # Tenant registry + validation (file-backed)
    access.py            # Tenant access rules (Keycloak + MSS)
    console_modules.py   # Console module enablement
  services/
    email/               # Placeholder email integration boundary
    payments/            # Placeholder billing integration boundary
```

## MSS profile centralization

- **Single owned module:** `core.mss_profile` is the only module that queries `platform.mss_profile` for session enrichment or table provisioning decisions. Update MSS profile schema access here when policies change.【F:srv/compose/platform/flask-bff/core/mss_profile.py†L1-L35】
- **Policy usage:** Any “is user provisioned”, “is root admin”, or “is tenant admin” decision is routed through `core.policy`, which is consumed by tenant access helpers and admin decorators.【F:srv/compose/platform/flask-bff/core/policy.py†L1-L181】【F:srv/compose/platform/flask-bff/tenants/access.py†L1-L69】

## Tenant registry and console rendering

- `tenants.registry` owns validation for tenant IDs, schema checks, and CRUD operations. Admin tenant endpoints and login validation consume it directly to keep registry concerns isolated.【F:srv/compose/platform/flask-bff/tenants/registry.py†L1-L217】【F:srv/compose/platform/flask-bff/admin/routes.py†L23-L207】【F:srv/compose/platform/flask-bff/routes/auth.py†L1-L210】
- `tenants.console_modules` drives which tenant console modules render, allowing menu updates without touching route logic.【F:srv/compose/platform/flask-bff/tenants/console_modules.py†L1-L11】【F:srv/compose/platform/flask-bff/routes/tenant.py†L1-L57】

## Service integration boundary (future)

- `services.email` and `services.payments` provide protocol-style interfaces so future integrations can plug in without changing admin or tenant modules.【F:srv/compose/platform/flask-bff/services/email/__init__.py†L1-L11】【F:srv/compose/platform/flask-bff/services/payments/__init__.py†L1-L11】

