# Phase 5 Database Initialization & MSS Integration Report

## 1. Context and Desired Outcome

The **Phase 5 goal** for the BFF stack is to introduce a schema-driven admin and user console without duplicating services. In this phase you added a Manifest-Structured Schema (MSS) discipline and SAMRAS support to a single Flask BFF service. This service is the sole gateway for authentication, data access and UI surfaces `github.com`. The new data model introduces a **MSS profile table** to anchor a hierarchical user authority graph `github.com`, **local domain and manifest tables** to define tenant-local tables `github.com`, and **SAMRAS structures** for hierarchical address spaces `github.com`.

You are now deciding **how to initialise the database on boot** after moving DB hooks from `@app.before_serving` to more portable `before_request` + `teardown_appcontext`. The recent build logs show that the BFF container starts, but requests to `/` error with `Missing required environment variable: PLATFORM_DB_URL`. The health endpoint still returns OK because it doesn’t hit the database. This indicates environment mis-configuration rather than code failure.

## 2. Why the application failed

The runtime error arises because the lazy initialisation code calls `db.get_conn()` on the first request. In your `db.py`, `get_conn()` checks for `PLATFORM_DB_URL` and raises a `RuntimeError` if it is unset. The new `before_request` hook triggers this check on any route (other than `/health`), so the server returns HTTP 500 when the variable is missing. This confirms:

1.  The container does **not have** `PLATFORM_DB_URL` in its environment.
2.  The database tables have likely not been created.

Until the environment is fixed and migrations applied, the BFF will always error on database access.

## 3. Overview of the MSS & SAMRAS requirements

* **MSS profile table:** A single table per database containing one or more `msn_id` values; it defines the primary authority, sub-users and hierarchical relationships `github.com`. Only system administrators can edit this table. BFF uses it to map Keycloak identities to a canonical `msn_id`, determine sub-user scopes and influence UI behaviour.
* **Local domain table:** Contains every `local_id` and its human-readable title `github.com`. All tables reference `local_id` here.
* **Manifest table:** Binds each table (`local_id`) to an archetype (`local_id`) `github.com`, declaring which archetype governs which table.
* **General tables:** Named `<msn_id><local_id>` and store actual data; structure is dictated by the manifest and archetype tables `github.com`. They must not self-define schema semantics.
* **SAMRAS tables:** Store count-streams and traversal rules; used to validate hierarchical addresses `github.com`.

These structures establish authority boundaries and deterministic interpretation of data. They require a dedicated schema (created via migrations) and environment variables for DB connection, plus initial seeding of the MSS profile.

## 4. Best-practice approach to database initialisation

### 4.1 Provide configuration via environment variables

Set all required variables in your Compose file or `.env` so the container has them at runtime. At minimum:

```yaml
services:
  flask_bff:
    environment:
      - PLATFORM_DB_URL=postgresql://platform_user:secret@platform_db:5432/platform
      - KEYCLOAK_BASE_URL=https://auth.<domain>
      - KEYCLOAK_REALM=<realm>
      - KEYCLOAK_CLIENT_ID=<client>
      - KEYCLOAK_CLIENT_SECRET=<secret>
      - SESSION_SECRET=<long_random_string>
    # ... other options
```
`PLATFORM_DB_URL` should point to the platform database (not Keycloak’s DB). Without this, the lazy init hook fails as shown in your logs. Confirm that `platform_db` service exists and that credentials match your Postgres configuration. You may also want `INITIAL_MSN_ID` and `INITIAL_USER_ID` env vars to seed the first row in the MSS profile table.

### 4.2 Apply migrations explicitly
Given the MSS model emphasises strict authority and clear version control, **don’t rely on the application to run migrations automatically**. Instead:
1.  Run migrations manually or via an entrypoint script when the container starts. This ensures that tables exist before requests arrive and avoids race conditions across workers.
2.  Use the provided SQL files (`platform-schema/001_init.sql` and `002_mss_init.sql`) to create the `platform` schema and MSS tables. For example:
```bash
docker compose exec platform_db psql -U platform_user platform -f /srv/compose/platform/platform-schema/001_init.sql
docker compose exec platform_db psql -U platform_user platform -f /srv/compose/platform/platform-schema/002_mss_init.sql
```

3.  If you adopt a Python migration tool (e.g. Alembic), ensure migrations are idempotent and versioned.
4.  Seed the `mss_profile` table with at least one row containing the master `msn_id` and the Keycloak `user_id` of your platform admin (usually your own user). This allows the BFF to map the first login to a canonical `msn_id` and assign the `root_admin` role.

1.  The container does **not have** `PLATFORM_DB_URL` in its environment.
2.  The database tables have likely not been created.

### 4.3 Use lazy initialisation judiciously
Your updated Flask hooks (`before_request` + run‑once flag and `teardown_appcontext`) are correct for Gunicorn’s worker model, where `before_serving` and `after_serving` are not guaranteed to run in every worker. However, ensure:
* The initialisation function (`_init_once`) checks a thread‑safe `initialized` flag to run only once per worker. It should:
  * Call `db.get_conn()` to prime the connection pool.
  * Optionally seed demo data (e.g. local domains and archetypes) if not already present.
* `teardown_appcontext` closes the DB connection gracefully. It runs when the application context ends after each request, which is reliable across Gunicorn workers.
* Avoid seeding data on every worker; use a separate admin script or run migrations to insert data. You can keep a small hook for reading environment variables (`INITIAL_SEED`) to optionally insert sample rows on first boot.

### 4.4 Consider separating concerns via modules
Since the updated BFF now uses MSS and SAMRAS extensively, splitting responsibilities improves maintainability:
* **db.py** – houses connection management (already present).
* **routes/** – group admin routes, table routes and user routes into blueprints; this helps to isolate initialisation logic and reduces the chance of circular imports.
* **utils/samras.py** – centralise SAMRAS parsing and validation functions.
* **migrations/** – store SQL migration files or Alembic versions.
This modular structure aligns with Flask best practices and simplifies testing.

### 4.5 Keep operations explicit
The Phase 5 docs emphasize that no migrations or schema changes should run silently. Platform administrators remain in control of:
* When to run migrations
* When to seed data
* Which tenant is created and which archetypes and tables are bound
Even though the code supports lazy init, **avoid putting destructive or heavy operations in the request lifecycle**. Use separate operational scripts or admin console workflows for schema definition and data creation.

## 5. Recommended step‑by‑step procedure to complete Phase 5

1.  Update your `.env` or `docker-compose.yml` to include `PLATFORM_DB_URL` and other secrets. Rebuild and redeploy the BFF container.
2.  Apply migrations manually to create the `platform` schema and MSS tables. Use `docker compose exec platform_db psql` commands to run `001_init.sql` and `002_mss_init.sql` before starting the app.
3.  Seed the MSS profile table with a row linking your Keycloak admin user to an initial msn_id. For example:
```sql
INSERT INTO platform.mss_profile (msn_id, user_id, parent_msn_id, display_name, role)
VALUES ('00000000-0000-0000-0000-000000000001', '<keycloak-admin-id>', NULL, 'Platform Admin', 'root_admin');
```
4.  Launch the BFF via Compose. Ensure that `before_request` no longer raises a missing env var. Use `/health` to verify service health.
5. Log in through the BFF and visit `/admin`. Use the admin console to create local domains, archetypes and manifest entries, rather than seeding them in application code. This ensures data discipline and auditability. You can still keep a small run‑once seed for a default tenant if needed.
6.  Run the integration tests (as implemented in Task 8) to verify schema registry, data CRUD and user hierarchy. They should pass now that the DB is configured and seeded.
7.  Review logs. Make sure there are no errors when accessing routes that hit the database. The lazy init plus teardown should handle DB connections gracefully across worker threads.
8.  Document your setup in `/srv/compose/platform/README.md` to include instructions on environment variables, migration steps and initial seeding so future operators know how to bring up the stack.

## 6. Conclusion

Completing Phase 5 requires careful coordination between deployment configuration, database migrations and lazy initialisation hooks. Ensure that `PLATFORM_DB_URL` and related environment variables are set, apply migrations before serving, and avoid seeding data implicitly in request hooks. By following these steps you align with MSS and SAMRAS design principles—clear authority boundaries, deterministic structure and explicit mutations—while maintaining the operational posture defined in the BFF scope document











