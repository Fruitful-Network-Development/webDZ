# Migration Playbook

This playbook describes a phased migration that stages files first and enables services later. The repository is synchronized into a **ready-to-deploy but inert** state, and every activation step is manual. Nothing auto-runs; services only start when explicitly enabled.

## Phase 0: Ready-to-deploy but inert repo structure

After files are staged, the repo should be complete but not activated. The structure is present, configs are in place, and services are disabled by default.

**Characteristics**
- All required directories and configuration files exist.
   - `/etc/nginx/sites-available/auth.fruitfulnetworkdevelopment.com.conf`
   - `/etc/nginx/sites-available/api.fruitfulnetworkdevelopment.com.conf`
   - `/etc/systemd/system/compose-platform.service`
   - `/srv/compose/platform/docker-compose.yml`
   - `/srv/compose/platform/env.example`
- Docker and Compose are installed.
- Docker is running, but no containers are started for this project.
- NGINX is unchanged from current behavior:
   - no `auth.*` or `api.*` symlinks in `sites-enabled`
   - no certs requested for those domains yet
- systemd is unchanged:
   - compose-platform.service exists but is not enabled or started.

Dry run:
```bash
sudo rsync -av --delete --dry-run --exclude 'webapps/platform/venv' /home/admin/aws-box/srv/ /srv/
```
, and then:
```bash
sudo rsync -av --delete --dry-run --exclude 'sites-available/fruitfulnetworkdevelopment.com.conf' /home/admin/aws-box/etc/nginx/ /etc/nginx/
```
, and then:
```bash
sudo rsync -av --dry-run /home/admin/aws-box/etc/systemd/system/ /etc/systemd/system/
```
This last dry run is to varify only the unit files under /etc/systemd/system/ are updating, and that `/etc/systemd/system/multi-user.target.wants/` is not touched.
No “activation” happens unless you explicitly enable or start.

**Check to make sure the correct files are being updated, then run:**

```bash
sudo rsync -a --delete --exclude 'webapps/platform/venv' /home/admin/aws-box/srv/ /srv/
```
, and then:
```bash
sudo rsync -a --delete --exclude 'sites-available/fruitfulnetworkdevelopment.com.conf' /home/admin/aws-box/etc/nginx/ /etc/nginx/
```
, and then:
```bash
sudo rsync -av /home/admin/aws-box/etc/systemd/system/ /etc/systemd/system/
sudo systemctl daemon-reload
```

#### Set Up Docker

**0.1) Confirm:**
```bash
docker --version || true
docker compose version || true
```

**0.2) Install prerequisites:**
```bash
sudo apt-get update
sudo apt-get install -y \
    ca-certificates \
    curl \
    gnupg \
    lsb-release
```

**0.3) Add Docker’s official GPG key**
```bash
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/debian/gpg \
  | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg
```
, than
```bash
. /etc/os-release
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian $VERSION_CODENAME stable" \
| sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
```

**0.4) Add Docker’s official repository**
```bash
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/debian \
  $VERSION_CODENAME stable" \
| sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
```

**0.5) Install Docker Engine + Compose plugin**
This installs:
- docker
- docker compose (v2 plugin, not the old docker-compose binary)
```bash
sudo apt-get update
sudo apt-get install -y \
  docker-ce \
  docker-ce-cli \
  containerd.io \
  docker-buildx-plugin \
  docker-compose-plugin
```

**0.6) After install:**
```bash
sudo systemctl enable docker
sudo systemctl start docker
```

**0.7) Verify Docker is running**
```bash
docker --version
docker compose version
sudo systemctl status docker --no-pager
docker ps
ss -lntp | grep docker || true
```

#### (Optional, but recommended) Add admin to docker group
This avoids needing sudo for every Docker command.
```bash
sudo usermod -aG docker admin
```
Important: This does not take effect until you log out and log back in.

After re-login, verify:
```bash
groups
docker ps
```
(should work without `sudo`)

---

## Phase 1: Intermediate server state (after sync, before enablement)

Once the repo is synced to the server, the system remains inert. This is a deliberate checkpoint that allows verification before any service activation.

**Expected state**
- Code and configuration are fully synced.
- Services are installed but disabled (not running, not enabled at boot).
- Only existing, pre-migration services remain active.
- Manual validation can be performed safely.

## Phase 2: Low-risk enablement sequence (soft launch planning

Start development, the lowest-risk activation order remains:
  - Start Postgres + Keycloak internally only (no NGINX enablement)
  - Expose auth.* with TLS
  - Introduce Flask BFF authentication endpoints and session model
  - Expose api.* once the BFF is ready to answer something meaningful

Activation follows a conservative, low-risk order. Enable foundational auth first, then downstream services.
> **Reminder:** Activation is manual at every step. Nothing auto-runs.

### 1.1) Start Postgres + Keycloak internally only
- Enable and start Keycloak.
- Validate login, realm configuration, and token issuance.
- Confirm health checks and logs before proceeding.

**Create the .env file (required before containers can start)**
This does not expose anything.
```bash
sudo nano /srv/compose/platform/.env
```
Minimum viable contents (example — choose strong secrets):
```bash
# Keycloak admin bootstrap
KEYCLOAK_ADMIN=admin
KEYCLOAK_ADMIN_PASSWORD=STRONG_ADMIN_PASSWORD

# Keycloak DB
KC_DB_PASSWORD=STRONG_DB_PASSWORD

# Placeholder for later phases
KC_REALM=fruitful
OIDC_CLIENT_ID=placeholder
OIDC_CLIENT_SECRET=placeholder
SESSION_SECRET=placeholder
```
Lock it down:
```bash
sudo chmod 600 /srv/compose/platform/.env
sudo chown root:root /srv/compose/platform/.env
```
Checkpoint
```bash
ls -la /srv/compose/platform/.env
```
Expected: owned by root, readable only by root.

**Start the Compose stack manually (NOT via systemd)**
We deliberately avoid `compose-platform.service` for now so you stay in full control.
```bash
cd /srv/compose/platform
sudo docker compose up -d
```
This will:
- pull images if needed
- start Postgres
- start Keycloak
- NOT start Flask BFF yet (it may start but is inert)- 

**Verify containers are running**
```bash
docker ps
```
Expected:
- `platform_postgres`
- `platform_keycloak`
(Flask BFF may be running but unreachable and unused)

**Verify ports are bound only to localhost**
```bash
ss -lntp | egrep ':8081|:5432'
```
Expected:
- `127.0.0.1:8081` → Keycloak
- Postgres bound internally only (likely no host port)
If you see `0.0.0.0:8081`, stop immediately — that would be a misconfiguration.

**Verify Keycloak health locally (no browser yet)**
From the server:
```bash
curl -I http://127.0.0.1:8081
```
Expected:
- `HTTP 200` or `302`
Checkpoint
- Containers running
- No public exposure
- Data persistence established



### 1.2) Expose auth.fruitfulnetworkdevelopment.com with TLS
> **Goal:** Make Keycloak publicly reachable only through NGINX + HTTPS.
This phase answers: “Can the IdP exist independently and safely?”

**Enable the NGINX vhost (still no cert yet)**
```bash
sudo ln -s /etc/nginx/sites-available/auth.fruitfulnetworkdevelopment.com.conf \
           /etc/nginx/sites-enabled/auth.fruitfulnetworkdevelopment.com.conf
```
Validate:
```bash
sudo nginx -t
```
Reload:
```bash
sudo systemctl reload nginx
```
At this moment:
- HTTP (port 80) should respond
- HTTPS will fail until cert is issued

**Obtain TLS certificate (Certbot)**
```bash
sudo certbot --nginx -d auth.fruitfulnetworkdevelopment.com
```
Certbot will:
- perform ACME challenge
- update the vhost
- install cert paths

**Verify Keycloak via browser**
Visit:
```bash
https://auth.fruitfulnetworkdevelopment.com
```
You should see:
  - Keycloak welcome or login screen

Admin console:
```bash
https://auth.fruitfulnetworkdevelopment.com/admin
```
Login with:
- `KEYCLOAK_ADMIN`
- `KEYCLOAK_ADMIN_PASSWORD`

**Verify reverse proxy correctness**
Inside Keycloak admin:
- Server info → should show correct hostname
- No mixed-content warnings
- Redirects remain HTTPS

Checkpoint: Phase 2 complete
- Keycloak publicly reachable
- TLS enforced
- Still no dependency on Flask BFF



### 1.3) Introduce Flask BFF authentication endpoints (DO NOT expose yet)
> **Goal:** Flask understands Keycloak, but is not public.
**This phase is design-sensitive**, so we only outline actions.
What you will do later:
 1. Create Keycloak realm (`fruitful`)
 2. Create OIDC client for Flask
 3. Implement in Flask:
   - `/login`
   - `/callback`
   - `/logout`
   - session cookie
 4. Test locally only via:
   - SSH port-forward to `127.0.0.1:8001`
   - or curl-based flow testing

**You will not enable `api.*` yet.**

### 1.4) Expose api.fruitfulnetworkdevelopment.com
> **Goal:** Only expose API when it answers something meaningful.
Later activation steps:
 1. Enable NGINX vhost for api.*
 2. Obtain TLS cert
 3. Validate:
   - `/health`
   - `/me`
   - authenticated response paths

---

## Phase 3: Introduce the Flask BFF (still internal-only)
> **Goal:** Bring up a minimal Flask BFF that can authenticate users via Keycloak using OIDC, manage a server-side session cookie, and expose internal-only test endpoints — without any public API exposure or client-site coupling.

**Constraints (locked):**
- Keycloak already live at auth.fruitfulnetworkdevelopment.com
- Flask BFF bound to 127.0.0.1:8001 only
- No NGINX vhost for api.* enabled yet
- Testing via SSH port forwarding to localhost:8001
- No client-site JavaScript changes
(after its stable expose: api.fruitfulnetworkdevelopment.com - Phase 4)

 *See `~bffScrope.md` for more details.*

### 3.1 Keycloak: create realm + OIDC client for internal test
You’re going to test via SSH port forwarding, so Keycloak needs redirect URIs for `http://localhost:8001`.

#### Create a realm
In Keycloak admin console:
  - Create realm: `fruitful` (or match whatever you set as `KC_REALM`).

#### Create OIDC client for BFF
Create client with these settings:
- Client ID: flask-bff
- Client type: OpenID Connect
- Client authentication: ON (confidential client)
- Standard flow: ON
- Implicit flow: OFF
- Direct access grants: OFF
**Valid redirect URIs:**
`http://localhost:8001/callback`

Web origins:

http://localhost:8001

Root URL / Home URL (optional):

http://localhost:8001

Then copy:

Client Secret (you will put it into .env)

Why HTTP not HTTPS here? Because your Phase 3 access path is your laptop → SSH tunnel → localhost, so HTTPS is not involved yet.













### 3.2 Server: finalize .env for BFF


### 3.3 Implement the minimal Flask BFF service


### 3.4 Bring up the BFF container (still internal-only)

### 3.5 Test from your laptop via SSH port forwarding

---

## Manual activation checklist

- [ ] Sync repo to server (files only).
- [ ] Verify inert state (no services enabled or running).
- [ ] Enable/start Keycloak and validate.
- [ ] Enable/start BFF and validate.
- [ ] Confirm NGINX proxy routes to localhost-bound services.

**Nothing auto-runs; all service activation is manual.**
