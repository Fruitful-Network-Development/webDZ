# BFF Scope & Platform (Updated)

This document reflects the **current, consolidated state** of the platform after successful
Phase 3 completion and partial Phase 4 readiness.

It supersedes earlier drafts by **removing the platform Postgres database** and clarifying that
the BFF currently operates with **Keycloak as the sole stateful dependency**, using **server-side
sessions only**.

This document describes **what exists now**, not the historical migration process.
(Migration steps remain documented separately.)

---

## 1. Role of the BFF (Authoritative)

The Backend-for-Frontend (BFF) is the **only application-layer service** that:

- Initiates authentication flows
- Interacts with Keycloak
- Holds authenticated user state
- Enforces authorization
- Serves platform-owned UI surfaces (admin + future user UI)

Client sites:
- Remain static
- Never store tokens
- Never communicate with Keycloak directly
- Communicate only with the BFF over HTTPS (Phase 4)

---

## 2. Authentication Model (Locked In)

### Identity Provider
- **Keycloak** is the single Identity Provider (IdP)
- Owns:
  - Credentials
  - Login UI
  - Password resets
  - MFA (future)
  - Realm roles

### BFF Responsibilities
- Redirects users to Keycloak
- Exchanges authorization codes server-side
- Establishes a **server-managed session**
- Issues a cookie:
  - `HttpOnly`
  - `SameSite=Lax`
  - `Secure` (when served over HTTPS)

### Explicit Exclusions
- No access tokens in browser storage
- No refresh tokens in browser storage
- No direct Keycloak access from client sites

---

## 3. Session Model (Current)

- Session data is held **by the BFF**
- Implemented using Flask sessions
- Cookie contains only a session identifier / signed payload
- Identity claims stored server-side:
  - `user_id` (Keycloak `sub`)
  - `display_name` (best-effort)
  - `realm_roles`

There is **no application database** at this stage.

---

## 4. Authorization Model

### Roles
Authorization is driven by **Keycloak realm roles**, for example:

- `root_admin`
- `tenant_admin`
- `user`

The BFF:
- Extracts roles from the OIDC access token
- Enforces authorization at route boundaries

Example (conceptual):
```python
@require_realm_role("root_admin")
def admin_route():
    ...
```

---

## 5. Mutating Actions (Constrained by Design)

The BFF **may perform mutating actions only if all conditions are met**:

- Narrow, explicit scope
- Validated inputs
- Reversible operation
- Audit-capable

### Allowed (Future, Explicit)
- Upload validated JSON content files
- Promote content from `staging/` → `live/`
- Toggle feature flags
- Trigger controlled deploy actions (Git pull / fast-forward only)

### Explicitly Excluded
- Editing NGINX configs
- systemd manipulation
- Firewall or kernel changes
- TLS issuance or renewal
- Arbitrary shell execution

These remain **infrastructure workflows**.

---

## 6. Runtime Architecture (Current)

```
Browser
  ↓
NGINX (host)
  ↓
Flask BFF (container, localhost-only in Phase 3)
  ↓
Keycloak (container, proxied via NGINX)
```

Keycloak is exposed publicly at:

```
https://auth.fruitfulnetworkdevelopment.com
```

The BFF is currently accessed via:
- SSH port forwarding (`localhost:8001`) in Phase 3
- `https://api.fruitfulnetworkdevelopment.com` in Phase 4

---

## 7. Operational Commands (Reference)

### BFF lifecycle
```bash
cd /srv/compose/platform
docker compose up -d flask_bff
docker compose restart flask_bff
docker compose logs -f flask_bff
```

### Keycloak lifecycle
```bash
docker compose logs -f keycloak
```

### Local testing (Phase 3)
```bash
ssh -L 8001:127.0.0.1:8001 admin@<ec2-ip>
```

Then browse:
```
http://localhost:8001/login
http://localhost:8001/me
```

---

## 8. Public Exposure Rules

- **auth.*** is public and TLS-terminated
- **api.*** remains disabled until:
  - `/health` responds
  - `/me` works reliably
  - Session cookies are `Secure`
  - NGINX proxy is validated

No service becomes public by accident.

---

## 9. Future Extensions (Non-Binding)

The following remain optional and deferred:

- Platform-owned database for identity resolution
- Audit persistence beyond logs
- Admin UI for content publishing
- Tenant-level authorization models

Their absence does **not** block current operation.

---

## 10. Final Invariants

- Authentication is **BFF-only**
- Keycloak is the only IdP
- Client sites remain static
- Infrastructure remains manually operated
- Activation is always explicit
- Security boundaries are preserved

This document defines the **current operating contract** of the BFF.
