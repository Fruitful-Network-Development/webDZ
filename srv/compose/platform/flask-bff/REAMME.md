# FLASK BFF APLICATION

At this aplications core, there is `main.py`. IT employs two secondary principal files, `websites.py` & `portal.py`.

There is not meant to be any JSON in Postgres, therefore there needs to be developed scripts to ingest this demo data. 
Also another script to remove the old data, if context is ever needed merely add a comment inside the script file and include 'beta' in the file name.

The portal aplication is provided the entrypoint, as a core organizing file, by `mss.comendium.<msn_id>`.
Also providing other context.
Deffined via the MSS schema, being the principle scheama of the data enviorment.
It holds the values of a particular dominion's organizing files like `HERE`. 
Addionally, the MSS schema is built to expect 'further standarizations', if any, in a particular positions in the data enviorment (organized and contained by the anthology table).

In this particular use of the mss schema, I am using the 'platform' standardization.
These should subsequently reveal the other linked `platform.<title>.<msn_id>` files, with distinctions for tenants and facilitators. That distinction is important to portal-app.py.
Other platform files like `platform.conspectus.<membership>.<msn_id>` are used by the portal app for user authentication. Noting that a tenant/facilitator profile is merely the organization client, and assigns a platform user to hold the role of a keycloak sign in. Currently the portal-app.py should only be built to assume a single `principle_user`, and thus a singe keycloak user id for signing in.

The `platform.garland.<membership>.<msn_id>` is meant to be the authority that dictates and gets refereed to, in order to materialize the subsequent console UI.

The `platform.florilegium.<membership>.<msn_id>` is more so a part of the data environment, rather than `platform` files which are standardization for the portal console. Its in the florilegium that data tables are tracked, alongside other information. Particularly the `muniment` value is semi platform reliant, as it dictates weather a table is accible as an outside resource, via a verified api, or meta data that shouldn't be changed during runtime, etc. 
This is part of the mss schema as it is important to be able to have the compendium entry points be like the main nodes, where those nodes can either be accessed outside the environment (like api's used on a respective website, whether for updating data or for retrieving data, live reporting, etc.), or inside (like a farmer using the standardized taxonomy data table, etc.).

The data schemas, for mss and platform are still under works and will likely change, however, the flask-bff application code must be solid for core modules and functionalities (like website api calls, console CRUD actions, authentication, UI base, admin console base, tenant console base), however I am really just looking to develop a solid application that doesn't get too specific that it impedes my ability to develop later.

## LAYOUT
```
aws-box/srv/compose/platform/flask-bff/
├── README.md
├── .dockerignore
├── Dockerfile
├── gunicorn.conf.py
├── requirements.txt
├── app.py
├── auth/
|  ├── authz.py
|  ├── entrypoint.sh
|  └── __init__.py
├── webapp/
|  ├── web-app.py
|  └── __init__.py
└── portal/
   ├── portal-app.py
   ├── UI/
   |  ├── tenant/
   |  └── admin/
   └── services/
```

There are no uses of in-memory state (temporary, per worker). Rather, the configuration exists inside Postgres and is treated it as the authoritative source (dictated by the schema).

The webapp directory is for later development of services that involve api calls, that are verified by the portal apllication.

The facilitator is the beneficiary profile that is used as the admin console, and the principle user of which is considered the admin user.

We always find the facilitator information deffined at the beggining of the file, `HERE`.
For the given positions:
   - 


---

## SCHEMA AGNOSTICS

### Portal responsibility boundaries
- [FILL] What is “portal” vs “console” vs “website API”?
- [FILL] What is the canonical entry-point object (“compendium”)?

A2) Environment & entry points
- [FILL] How compendium files are located / addressed (naming pattern, lookup rules).
- [FILL] How linked platform.* files are discovered from compendium.

A3) Multi-tenant assumptions
- For now: assume a single “principal_user” sign-in path.
- [FILL] Future: multiple users, user hierarchy, delegated roles.

============================================================
SECTION B — Data Contracts (Schema-Agnostic Interfaces)
============================================================

Implement these as Python interfaces / service modules with stub methods and clear docstrings.
Do NOT bake in table names or columns; add TODOs with “expected fields” placeholders.

B1) Identity & Access contract (Keycloak + internal mapping)
- [HEADER] How data dictates Keycloak user → tenant assignment
- [HEADER] How roles map to console visibility
- Methods (stubs / minimal):
  - resolve_user_context(keycloak_user_id) -> UserContext
  - resolve_tenant_for_request(request) -> TenantContext
  - list_user_roles(user_context) -> list[Role]
  - authorize(user_context, tenant_context, capability) -> bool

B2) Portal configuration contract
- [HEADER] How compendium/conspectus/garland/florilegium are represented in DB
- Methods:
  - get_compendium(msn_id) -> dict
  - get_conspectus(membership, msn_id) -> dict
  - get_garland(membership, msn_id) -> dict
  - get_florilegium(membership, msn_id) -> dict

B3) Console data contract
- [HEADER] How the data informs the UI (module registry, nav, forms)
- Methods:
  - list_console_modules(tenant_context, user_context) -> list[ModuleSpec]
  - get_module_schema(module_id) -> ModuleSchema
  - crud_list(module_id, filters) -> list[Record]
  - crud_get(module_id, record_id) -> Record
  - crud_create(module_id, payload) -> Record
  - crud_update(module_id, record_id, payload) -> Record
  - crud_delete(module_id, record_id) -> None

B4) Muniment / access tier contract (public vs internal vs immutable)
- [HEADER] How muniment affects API exposure & mutability
- Methods:
  - classify_resource(resource_id) -> MunimentPolicy
  - enforce_policy(action, resource_id, user_context) -> None

============================================================
SECTION C — Flask App Structure (Refactor Plan)
============================================================

Refactor /srv/compose/platform/flask-bff to this structure (only create what is needed):
- app.py (thin): app factory, blueprint registration, error handlers, config load
- routes/
  - auth.py
  - admin.py
  - portal.py
  - console.py
  - api_public.py
  - api_internal.py
- services/
  - access_service.py      (Keycloak + user context + authorization)
  - portal_service.py      (compendium/conspectus/garland/florilegium resolution)
  - console_service.py     (module registry + CRUD orchestration)
  - tenancy_service.py     (tenant registry + tenant config loading)
- db/
  - db.py                  (connection pool + helpers)
  - migrations.py          (optional helper to run/check migrations)
- scripts/
  - ingest_demo_data.py or ingest_demo_data.sh (non-destructive)
  - beta_reset_demo_data.py or beta_reset_demo_data.sh (destructive)
- templates/
  - base.html
  - landing.html
  - admin/ (scaffold)
  - tenant/ (scaffold)

Do not remove existing working components unless replaced with equivalent functionality.

============================================================
SECTION D — Core Routes to Implement (Stable Skeleton)
============================================================

D1) Health + root
- GET /health -> {status:"ok"}
- GET / -> landing or redirect depending on auth state

D2) Authentication
- GET /login?tenant=<id>&return_to=<path> (works even if schema changes)
- GET /callback (handles OIDC callback)
- GET /logout

D3) “Me” endpoint (debuggable)
- GET /me -> returns UserContext + TenantContext + roles + provisioning status

D4) Admin console (skeleton)
- GET /admin -> overview
- Additional tabs (skeleton routes + templates):
  - /admin/overview
  - /admin/tenants
  - /admin/users
  - /admin/data (tables/lists/archetypes/manifest placeholders)
  - /admin/services (email/billing placeholders)

D5) Tenant console (skeleton)
- GET /t/<tenant_id>/console
- GET /t/<tenant_id>/console/<module>
- Module list derived from service contract, not hardcoded.

D6) API boundaries
- /api/admin/...  (admin-only)
- /api/t/<tenant_id>/... (tenant-scoped)
- /api/public/... (website-facing APIs; read-only or policy-controlled)



