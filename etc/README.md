# /etc/README.md

## Hoast OS Configuration

Define the host-level responsibility boundary.

### Should answer:
  - What belongs on the host OS
  - Why it is not containerized
### Suggested contents
  - Owned Responsibilities
    - NGINX
    - TLS termination (Certbot)
    - systemd units
  - Explicit Non-Responsibilities
    - Application business logic
    - Identity logic
    - Stateful app data
  - Change Policy
    - Changes require reload/restart
    - Safe to stage without activation

---

## Overview

HERE
