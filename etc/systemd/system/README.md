# /etc/systemd/system/README.md

## Service Supervision

Clarify what systemd manages and why.

### Suggested contents
  - Service Categories
    - Host-native services (NGINX)
    - Orchestration services (Docker Compose)
  - Lifecycle Expectations
    - Enable ≠ start
    - One-shot services vs daemons
  - Design Rule
    - systemd supervises platform lifecycles, not application internals

---

## Overview

HERE
