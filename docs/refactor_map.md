# Refactor Map: Current State

## Entrypoints
- App factory and runtime entry: `app.py` (`create_app()`, `app = create_app()`).
- WSGI/Gunicorn uses `app` in `app.py` via `gunicorn.conf.py`/`entrypoint.sh`.

## Blueprints / Routes
- Auth: `routes/auth.py` (`auth_bp`) OIDC session bootstrap.
- Admin: `routes/admin.py` (`admin_bp`) admin UI + schema registry APIs.
- Tables: `routes/tables.py` (`tables_bp`) tenant table CRUD + SAMRAS lookup.
- Users: `routes/user.py` (`user_bp`) MSS profile admin endpoints.
- Tenant console: `routes/tenant.py` (`tenant_bp`) HTML console pages.
- Common helpers: `routes/common.py` (auth guards, tenant registry calls).

## Data Usage (filesystem)
- Tenant registry JSON files in `data/tenants/**` loaded by `tenant_registry.py`.
- Templates in `templates/**` for admin/tenant console.
- Static assets in `static/**`.

## Data Usage (database)
- DB access via `db.py` (Postgres, env `PLATFORM_DB_URL`).
- MSS profiles in `platform.mss_profile` (read in `utils/mss.py`, `routes/user.py`).
- General tables, local domains, archetypes, manifests, SAMRAS layouts in `routes/admin.py` and `routes/tables.py`.

## Hard-coded Paths / Env Vars
- `PLATFORM_DB_URL` in `db.py`.
- OIDC env vars in `config.py`: `OIDC_ISSUER`, `OIDC_CLIENT_ID`, `OIDC_CLIENT_SECRET`, `SESSION_SECRET`, `PUBLIC_BASE_URL`, `COOKIE_SECURE`.
- Default SAMRAS import path in `utils/statonomy_importer.py`: `/srv/old-data/SAMRAS-statonomy.json`.

## Implicit Coupling / Cross-cutting Concerns
- Admin and tenant table CRUD tightly coupled to DB schema (`platform.*`) and local domain + manifest assumptions.
- OIDC auth flow directly writes `session["user"]` and uses MSS profile lookup for `msn_id` (`utils/mss.py`).
- Table provisioning depends on manifest + local domain entries (`routes/admin.py`, `routes/tables.py`).
- Per-user `msn_id` used to derive physical table names (`utils/general_tables.py`, `routes/admin.py`).

## Platform vs Tenant vs Service Mixing
- Platform admin APIs and schema registry live alongside tenant CRUD under `routes/`.
- Tenant identity and console config are read from filesystem JSON, but data tables are DB-backed.
- Service integration is currently embedded in auth flow (OIDC/Keycloak).

