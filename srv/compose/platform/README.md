# /srv/compose/platform/README.md

## Auth & BFF stack

This is the most important README after root.

### Should answer:
  - What services exist in this stack
  - How they relate
  - What contracts they expose

### Suggested contents
  - Services
    - Keycloak (IdP)
    - Postgres (Keycloak-only)
    - Flask BFF
  - Public Interfaces
    - auth.fruitfulnetworkdevelopment.com
    - api.fruitfulnetworkdevelopment.com
  - Trust Boundaries
    - NGINX is the only ingress
    - Containers bind to localhost
  - Persistence
    - What volumes exist
    - What data loss would mean
  - What This Stack Does NOT Do
    - Serve static sites
    - Store application business data

---

## Overview

HERE
