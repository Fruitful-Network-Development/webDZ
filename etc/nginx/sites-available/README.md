# /etc/nginx/sites-available/README.md

## Vhost Patterns

Document how vhosts are structured, not their content.

### Suggested contents
  - Naming Convention
    - <domain>.conf
  - Common Patterns
    - Static site vhosts
    - Proxy-only vhosts
  - Certbot Expectations
    - 80 → 443 redirect
    - .well-known/acme-challenge
  - Enablement Rule
    - Files here are inert until symlinked

This README prevents drift in how new domains are added.

---

## Overview

HERE
