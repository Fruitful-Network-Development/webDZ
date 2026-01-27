# aws-box

## Overview

This repository is the **configuration mirror** for a single EC2 host that
serves static client sites and a small shared API layer. It documents how the
host is structured, what belongs where, and how changes are staged safely
before they are activated.

At a high level, the box hosts:

- **Static frontends** per client domain, served directly by NGINX.
- **Optional JSON APIs** provided by a shared Flask-based platform.
- **A planned Auth/BFF stack** (Keycloak + BFF) that will be introduced via
  Docker Compose while keeping NGINX as the only ingress.

## Purpose

Explain what this repository represents, not how any single component works.

## Scope

### In scope
- Host configuration under `/etc` (NGINX, systemd units, TLS tooling).
- Runtime deployment surface under `/srv` (static sites, platform code, compose
  stacks).
- Documentation of operational boundaries and change policies.

### Out of scope
- Application business logic.
- User data and secrets (except template examples).
- Automated deployment or activation steps.

## Architectural philosophy

- **Single-host, explicit activation.** Files can be staged without effect until
  services are explicitly reloaded or enabled.
- **Least-privilege ingress.** NGINX terminates TLS and proxies only to
  localhost-bound services.
- **Static-first.** Static sites do not require the API or any runtime backend
  unless they opt into it.
- **Immutable-ish config mirror.** This repo mirrors the live host layout and
  supports idempotent syncs.

## High-level architecture

```text
DNS → NGINX → (static site OR reverse-proxy) → platform services
```

## Server Deployed layout

```text
├── etc/
│   ├── nginx/
│   │   ├── mime.types
│   │   ├── nginx.conf
│   │   ├── sites-available/
│   │   └── sites-enabled/
│   └── systemd/
│       ├── logrotate.d/
│       └── system/systemd
└── srv/
    ├── webapps/
    │   ├── clients/
    |   │   ├── fruitfulnetworkdevelopment.com/
    |   |   │   ├── data/
    |   |   │   └── frontend/index.html
    |   │   ├── cuyahogavalleycountrysideconservancy.org/
    |   |   │   ├── data/
    |   |   │   └── frontend/index.html
    |   │   ├── trappfamilyfarm.com/
    |   |   │   ├── data/
    |   |   │   └── frontend/index.html
    |   │   └── cuyahogaterravita.com/
    |   |       ├── data/
    |   |       └── frontend/index.html
    │   └── platform/
    |       ├── app.py
    |       └── modules/
    └── compose/
        └── platform/
            ├── .env
            ├── docker-compose.yml
            ├── flask-bff/
            │   ├── .dockerignore
            │   ├── Dockerfile
            │   ├── __pycache__/
            │   │   └── tenant_registry.cpython-313.pyc
            │   ├── app.py
            │   ├── authz.py
            │   ├── config.py
            │   ├── data/
            │   │   └── tenants/
            │   │       ├── cuyahogaterravita/
            │   │       │   └── tenant.json
            │   │       ├── index.json
            │   │       ├── platform/
            │   │       │   └── tenant.json
            │   │       └── tenant.schema.json
            │   ├── db.py
            │   ├── entrypoint.sh
            │   ├── gunicorn.conf.py
            │   ├── requirements.txt
            │   ├── routes/
            │   │   ├── __init__.py
            │   │   ├── admin.py
            │   │   ├── auth.py
            │   │   ├── common.py
            │   │   ├── tables.py
            │   │   ├── tenant.py
            │   │   └── user.py
            │   ├── static/
            │   │   └── admin/
            │   │       └── admin.css
            │   ├── templates/
            │   │   ├── admin/
            │   │   │   ├── archetypes.html
            │   │   │   ├── index.html
            │   │   │   ├── lists.html
            │   │   │   ├── local_domains.html
            │   │   │   ├── manifest.html
            │   │   │   ├── samras_layouts.html
            │   │   │   ├── services.html
            │   │   │   ├── table_records.html
            │   │   │   ├── tables.html
            │   │   │   ├── tenant_detail.html
            │   │   │   ├── tenants.html
            │   │   │   └── user_management.html
            │   │   ├── base.html
            │   │   ├── forbidden.html
            │   │   ├── landing.html
            │   │   ├── not_provisioned.html
            │   │   └── tenant/
            │   │       ├── console.html
            │   │       ├── console_animals.html
            │   │       └── console_network.html
            │   ├── tenant_registry.py
            │   ├── tests/
            │   └── utils/
            │       ├── __init__.py
            │       ├── general_tables.py
            │       ├── mss.py
            │       └── samras.py
            ├── flask-bff.bak.20260125_160340/
            │   ├── Dockerfile
            │   ├── app.py
            │   ├── entrypoint.sh
            │   ├── gunicorn.conf.py
            │   ├── requirements.txt
            │   ├── static/
            │   │   └── admin/
            │   │       └── admin.css
            │   └── templates/
            │       ├── admin/
            │       │   └── index.html
            │       └── base.html
            ├── keycloak/realm/
            ├── platform-schema/
            │   ├── 001_init.sql
            │   ├── 002_mss_init.sql
            │   └── 003_mss_profile_msn_id_text.sql
            ├── platform-schema.bak.20260125_160340/
                └── 001_init.sql

```

## Deployment philosophy

- Files are staged first, activated explicitly later.
- Enabling a vhost or starting a service is a deliberate, manual step.
- No automatic side effects from `rsync` or repo sync.

---

## /srv

`/srv` is the runtime and deployment surface. It is where live web assets,
platform code, and Compose stacks reside.

### Purpose

Define what belongs on the runtime surface and how it should be managed.

### What lives here

- Client static sites under `/srv/webapps/clients/`.
- Shared platform code under `/srv/webapps/platform/`.
- Container stacks under `/srv/compose/`.

### What does not

- Host configuration (belongs under `/etc`).
- Secrets (only templates or examples may live in the repo).
- One-off ad hoc data that should be stored elsewhere.

### Backup expectations

- **Must back up**: client frontends, manifest files, client data files, and
  environment templates that document required variables.
- **Can be rebuilt**: platform virtual environments and container images.
- **External volumes**: container volumes are stored under `/var/lib/docker`
  and should be backed up separately if persistence is required.

---
