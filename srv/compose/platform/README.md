# Platform Auth & BFF Stack

This stack adds authentication and a backend-for-frontend (BFF) layer while
keeping host static sites unchanged.

## Conceptual ontology

The platform is guided by a small set of conceptual planes. Each plane owns a
distinct responsibility, and the system is designed to keep the planes
orthogonal and composable.

- **Identity & Access Plane**: Keycloak + BFF session model, tenant routing, and
  authorization. Users are global; tenant access is resolved by roles and
  platform rules. Clients never receive tokens.
- **Data Discipline Plane**: MSS table classes, schema-as-data, and authority
  boundaries. Tables are interpreted via manifests and archetypes, not
  self-describing.
- **Structure Addressing Plane**: SAMRAS layouts and reference semantics for
  hierarchical addressing. Shape is authoritative; meaning is layered.
- **Experience Plane**: Admin and tenant consoles, module boundaries, and UI
  shell contracts. Core is stable; modules plug in without redefining identity
  or data contracts.
- **Operations Plane**: Runbooks, migrations, provisioning, and demo workflows.

## Architecture at a glance

- **Services**: Keycloak (IdP), Flask BFF, Postgres (platform schema + Keycloak).
- **Ingress**: NGINX terminates TLS; containers bind to localhost only.
- **Public interfaces**: `auth.<domain>` → Keycloak, `api.<domain>` → Flask BFF.
- **Runtime flow**: static site → BFF login → Keycloak → BFF callback → secure
  cookie → `/api/` requests.
- **Non-goals**: serve static sites; store business data outside the platform
  schema; expose tokens to browsers.

## Doc map

- `docs/architecture.md` — system stack, trust boundaries, runtime flow.
- `docs/identity-access.md` — auth flow, roles, tenant registry, access rules.
- `docs/data-discipline.md` — MSS table classes, schema-as-data, invariants.
- `docs/samras.md` — SAMRAS addressing, reference semantics, versioning.
- `docs/console-experience.md` — admin/tenant console concepts and modules.
- `docs/operations.md` — Phase 5 runbook, migrations, provisioning.
- `docs/demo-cvcc.md` — CVCC demo workflow.
- `keycloak/realm/README.md` — realm export/import guidance.

## Quick pointers

- Login entry point: `/login?tenant=<tenant_id>&return_to=<path>`
- Root admin provisioning script: `scripts/provision_root_admin.sh`
- Migration scripts: `platform-schema/001_init.sql`, `002_mss_init.sql`,
  `003_mss_profile_msn_id_text.sql`
