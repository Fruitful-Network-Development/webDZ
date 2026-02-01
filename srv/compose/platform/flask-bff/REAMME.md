# FLASK BFF APLICATION

At this aplications core, there is `main.py`. IT employs two secondary principal files, `websites.py` & `portal.py`.

There is not meant to be any JSON in Postgres, therefore there needs to be developed scripts to ingest this demo data. 
Also another script to remove the old data, if context is ever needed merely add a comment inside the script file and include 'beta' in the file name.

### table naming convention:
There are tables that have the leading `mss.` in their names. These are pertanent to the core mss schema and have an expected structure that is deffined by the schema itsself.

### column naming convention:
Informative sections are seperated by a peroid, `.`, where the first section notates weather it is a system id, `@`, (Aplicable for msn_id, local_id, or other sub-domain namespace ID's like taxonomy: `@.<ID Namespace>.<Namespace Value Type>.<Namespace Max Depth>.<Column Title>`) or a system value, `#` (`#.<Value Class>.<Value Type>.<Max size of Value>.<Column Title>`).
Value Classes are not yet relivant on how they influence anything but they include: nominal, ordinal, natural, and cardinal.
Value types include: Text (`txt`), Initgers (`int`), Mass (`mass`), Time Stamp (`tmstp`), Coordinates (`crds`), Length (`lgth`), and Currency (`fiat`).

## Data, Console, & Portal Aplication Interplay

The portal aplication is provided the entrypoint, as a core organizing file, by `mss.comendium.<msn_id>`, and also providing other context. The form and content to be expeceted are deffined via the MSS schema. Additional expectation are in play for `mss.anthology.<msn_id>`.
Additionally the MSS schema is built to expect 'further standarizations', if any, under the anthology's local node `1_2_0`. Currently there is only the use of one additional standarization, called `platfrom` and as it relates to an additional schmea. This `platfrom` schema and subsequent tables are used to inform how the portal aplication determines the principal facilitating party. In this case, it is my company, and I am noted as the indevidual assigned to the principal user role of my companies benficiary entry. Since my company is noted as the facilitator in the `platform.conspectus.3_2_3_17_77_6_32_1_4_2_2`, then the principle user that is identified, me, is considered the keycloak sign in that is the admin.

These should subsequently reveal the other linked `platform.<title>.<msn_id>` files, with distinctions for tenants and facilitators. That distinction is important to portal-app.py. Note that a tenant/facilitator profile is merely the organization benficiary, and it assigns a platform user to hold the role of a keycloak sign in. Currently the portal-app.py should only be built to assume a single `principle_user`, and thus a singe keycloak user id for signing in.
In the future, I may adapt the platform schema to expect to be informed about the console spesifcs, however, for now it only uses two console builds: the admin, and tenant consoles.

The `mss.muniment.<msn_id>` is a data enviorment structure file, however, is semi platform reliant, as it dictates weather a table is accible as an outside resource. This is where a data enviorment deffines soruces of which may be accessed by anyone. So for my data system, it allows for users to refference my msn subdomain namespcae file called `here`. Also identified here are tables in a given `msn_id` namespace that can be acessed via authorized/authenticated API operations.

The data schemas, for mss and platform are still under works and will likely change, however, the flask-bff application code must be solid for core modules and functionalities (like website api calls, console CRUD actions, authentication, UI base, admin console base, tenant console base), however I am really just looking to develop a solid application that doesn't get too specific that it impedes my ability to develop later.


## SCHEMA AGNOSTICS

### Portal responsibility boundaries
What is “portal” vs “console” vs “website API”?
What is the canonical entry-point object (“compendium”)?

### Environment & entry points
How compendium files are located / addressed (naming pattern, lookup rules).
How linked platform.* files are discovered from compendium.

### Multi-tenant assumptions
For now: assume a single “principal_user” sign-in path.
Future: multiple users, user hierarchy, delegated roles.

---

## Data Contracts (Schema-Agnostic Interfaces)

Implement these as Python interfaces / service modules with stub methods and clear docstrings. Do NOT bake in table names or columns; add TODOs with “expected fields” placeholders.

### Identity & Access contract (Keycloak + internal mapping)
How data dictates Keycloak user → tenant assignment
How roles map to console visibility

### Portal configuration contract
How compendium/conspectus/garland/florilegium are represented in DB

###Console data contract
How the data informs the UI (module registry, nav, forms)

### Muniment / access tier contract (public vs internal vs immutable)
How muniment affects API exposure & mutability

---

## Flask App Structure (Refactor Plan)

---

## Core Routes to Implement (Stable Skeleton)

---

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

---
