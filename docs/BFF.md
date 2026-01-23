# BFF Scope & Platform

---

### 1.) BFF Mutating Tasks

The BFF **may perform mutating actions** via the admin UI **only when those actions are constrained**:
- narrow scope
- validated inputs
- reversible
- auditable

#### Identity / Access (via Keycloak Admin API)
- Create user
- Disable / enable user
- Assign roles and tenant membership
- Force logout
- Reset credentials

#### Content & Configuration Changes
- Upload and validate client JSON content files
- Toggle feature flags per client
- Publish a new content revision by:
  - promoting validated files from a `staging/` directory to `live/`
  - **or** creating a controlled Git commit / PR

#### Deploy Latest From GitHub
Allowed **only** under strict constraints:
- only approved repositories
- only trusted branches
- fast-forward or verified merges only
- preflight checks (linting, schema validation)
- dry-run → apply workflow
- **no arbitrary shell commands**

#### Database Writes
Allowed if:
- schema is controlled
- writes occur only through validated API calls
- tenant boundaries are enforced
- all mutations are audit-logged

> **Explicitly excluded from the UI**  
> - Editing NGINX configs directly  
> - Arbitrary shell execution  
> - systemd / firewall / kernel changes  
> - TLS issuance and renewal logic  

These remain **infrastructure workflows**, not UI actions.

---

### 2.) Global User Accounts with BFF-Only Auth

#### Auth Model
- **Keycloak** = Identity Provider (users, login, MFA later)
- **BFF** = Only component that interacts with Keycloak
- **Client sites** = Mostly static; never store tokens

#### Browser Authentication Flow (High-Level)
1. User visits a client site and needs authentication  
2. Client links to  
   `https://api.fruitfulnetworkdevelopment.com/login?return_to=...`
3. BFF redirects to Keycloak
4. User authenticates in Keycloak
5. Keycloak redirects back to BFF `/callback`
6. BFF exchanges authorization code server-side
7. BFF:
   - stores session server-side (or minimal signed session)
   - sets `HttpOnly; Secure; SameSite=Lax` cookie
8. Browser accesses BFF endpoints using cookie auth:
   - `/me`
   - `/clients`
   - `/profiles/{id}`

#### Global User Model (Platform-Owned)
This forms the **unified customer profile layer** and **lives in a database**:
- `user_profiles` (keyed by stable `user_id`)
- `user_contact_methods` (optional)
- `client_memberships` (user ↔ client ↔ role)
- `global_preferences`
- `profile_links` (external identities)

This data must be **queryable, consistent, and authoritative**.

---

### 3.) Platform-Owned Identity Resolution

Client systems may store operational data, but **identity resolution belongs to the platform**.

Platform DB owns:
- `user_id` (Keycloak UUID)
- normalized contact identifiers (email hash, phone hash, etc.)

Client systems may reference:
- `user_id` (preferred)
- raw email / phone (resolved to `user_id` by BFF on ingestion)

This avoids identity drift across clients.

---

### 4.) Data Staging Strategy

#### Stage 1 (Now): Minimal Platform Database
A small Postgres database (separate from Keycloak DB).

Tables:
- `user_profiles (user_id, display_name, created_at, updated_at)`
- `user_identifiers (user_id, type, value_normalized, value_hash, verified_at)`
- `client_memberships (client_id, user_id, role)`
- `audit_log (actor_user_id, action, target, metadata, timestamp)`

**No client operational data is stored here yet.**  
Only identity, authorization, and auditing.

---

#### Stage 2: UI-Managed Content Publishing
Admin UI may:
- upload content files to a `staging/` area
- validate against schemas
- show diffs
- promote content to `live/`

This enables safe mutation without infrastructure risk.

---

#### Stage 3: Optional Ingestion Pipelines
Future ingestion of:
- PayPal / Zettle exports
- Newsletter lists

Storage options:
- tenant-local filesystem (with platform identity resolution)
- tenant schemas in DB (stronger guarantees, more complexity)

---

### 5.) Cookie Scope & Multi-Domain Reality

If client sites live on many domains (e.g. `example.com`, `example.org`):
- cookies scoped to `*.fruitfulnetworkdevelopment.com` **will not be sent**

Therefore:
- client sites use JS to call the BFF at  
  `api.fruitfulnetworkdevelopment.com`
- cookies are scoped to the BFF domain
- CORS + `SameSite` policy must be configured correctly

### Seamless Login Across Domains
Possible via:
- centralized login on `fruitfulnetworkdevelopment.com`
- redirect or embed flow to establish BFF session

This is solvable, but **global identity across many TLDs is non-trivial** and must be handled intentionally.

---

### Final Locked-In Decisions

- Mutating tasks are allowed **only via constrained, audited APIs**
- Infrastructure surgery is excluded from the UI
- Global user accounts are platform-level
- Authentication is **BFF-only**
- `user_id` = Keycloak UUID (canonical identity)
- Client-specific operational data may remain filesystem-based initially
- Platform owns identity resolution and authorization logic
- Migration path to richer DB-backed tenant data remains open
