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

## Phase 2: Low-risk enablement sequence

Activation follows a conservative, low-risk order. Enable foundational auth first, then downstream services.

1. **Keycloak first**
   - Enable and start Keycloak.
   - Validate login, realm configuration, and token issuance.
   - Confirm health checks and logs before proceeding.

2. **BFF second**
   - Enable and start the BFF after Keycloak is stable.
   - Verify authentication flow through Keycloak.
   - Confirm expected responses through the proxy layer.

> **Reminder:** Activation is manual at every step. Nothing auto-runs.

## Phase 3: Localhost-only bindings and NGINX proxy flow

All services bind to **localhost-only** ports. External access flows exclusively through NGINX.

**Binding model**
- Keycloak and BFF listen on `127.0.0.1` only.
- No direct external exposure of service ports.

**Proxy flow**
1. Client requests reach NGINX.
2. NGINX proxies to localhost-bound services.
3. Responses return to NGINX, then to the client.

This setup preserves a controlled, manual activation process and reduces exposure risk during migration.

## Manual activation checklist

- [ ] Sync repo to server (files only).
- [ ] Verify inert state (no services enabled or running).
- [ ] Enable/start Keycloak and validate.
- [ ] Enable/start BFF and validate.
- [ ] Confirm NGINX proxy routes to localhost-bound services.

**Nothing auto-runs; all service activation is manual.**
