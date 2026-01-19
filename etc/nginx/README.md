# /etc/nginx/README.md

## Ingress Layer

Explain NGINX’s role as the edge authority.

### Should answer:
  - How traffic enters the system
  - How routing decisions are made

### Suggested contents
  - Role
    - TLS termination
    - Static serving
    - Reverse proxy
  - Routing Model
    - Domain-based separation
    - No auth logic here
  - Security Posture
    - Localhost-only upstreams
    - No direct container exposure
  - What NGINX Must Not Do
    - No authentication decisions
    - No business logic
    - No persistence

---

## Overview

HERE
