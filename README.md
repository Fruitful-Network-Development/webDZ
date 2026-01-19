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

## Repository layout

```text
aws-box/
├── README.md                              ← Top-level intent
├── etc/                                   ← Host OS configuration
│   ├── README.md
│   ├── nginx/
│   │   ├── README.md
│   │   └── sites-available/
│   │       └── README.md
│   └── systemd/
│       └── system/
│           └── README.md
└── srv/                                   ← Runtime surface
    ├── README.md
    ├── webapps/
    │   └── README.md
    └── compose/
        ├── README.md
        └── platform/
            └── README.md
```

## Deployment philosophy

- Files are staged first, activated explicitly later.
- Enabling a vhost or starting a service is a deliberate, manual step.
- No automatic side effects from `rsync` or repo sync.
