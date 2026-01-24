# /etc

## Host OS configuration

This directory documents the **host-level responsibilities** that must remain
on the OS instead of inside containers.

## Purpose

Define the host boundary and what is managed directly on the EC2 instance.

## Responsibilities

- **Ingress & TLS**: NGINX configuration and TLS termination (Certbot).
- **Service supervision**: systemd unit files for host-native services and
  Compose stacks.
- **Host safety controls**: log rotation, journald limits, and other OS-level
  guardrails.

## Non-responsibilities

- Application business logic (lives under `/srv`).
- Identity logic (managed by the Auth stack under `/srv/compose`).
- Stateful application data (lives in runtime directories or volumes).

## Change policy

- Changes are inert until services are explicitly reloaded or restarted.
- New vhosts are inactive until symlinked into `sites-enabled`.
- New systemd units are inactive until explicitly enabled and started.

## Current initiatives

- Introduce `certbot-renew.service` and `certbot-renew.timer` for scheduled
  certificate management.
- Add `compose-platform.service` to supervise the Auth/BFF Compose stack.

---

## /etc/systemd/system

### Service supervision

systemd is the host-level supervisor for both native services and Compose
stacks. It defines what starts on boot and how services are restarted.

### Purpose

Clarify what systemd manages and why.

### Service categories

- **Host-native services**: NGINX, certbot renewals.
- **Application platform**: `platform.service` for the shared Flask API.
- **Compose orchestration**: `compose-platform.service` for the Auth/BFF stack.

### Lifecycle expectations

- `enable` controls boot-time activation; it does not start a service
  immediately.
- `start` and `stop` are manual operations and part of change control.
- One-shot units may be used for periodic jobs (e.g., Certbot renewal).

### Design rule

systemd supervises process lifecycles and orchestration boundaries, not
application internals or business logic.

# /etc/nginx

## Ingress layer

NGINX is the single ingress point for the host. It terminates TLS, serves
static sites directly, and proxies approved routes to backend services.

## Purpose

Explain NGINX’s role as the edge authority and routing layer.

## Responsibilities

- TLS termination for all domains.
- Static site delivery for client frontends.
- Reverse-proxy routing to localhost-bound backends.
- Maintaining shared snippets (`ssl_params.conf`, `proxy_common.conf`).

## Routing model

- Domain-based separation for each client site.
- Static sites are served directly from `/srv/webapps/clients/<domain>/frontend`.
- API or auth traffic is proxied to backend services that bind only to
  `127.0.0.1`.

## Security posture

- No direct exposure of container ports to the public internet.
- No authentication or business logic inside NGINX.
- Consistent headers and TLS configuration via shared snippets.

---

## /etc/nginx/sites-available

### Vhost patterns

This directory holds **inactive** virtual host definitions. Files here do
nothing until symlinked into `sites-enabled`.

### Purpose

Document how vhosts are structured and how they are activated.

### Naming convention

- `<domain>.conf` for site-specific vhosts.
- `auth.<domain>.conf` for Keycloak/Auth proxy vhosts.
- `api.<domain>.conf` for BFF/API proxy vhosts.

### Common patterns

#### Static site vhost

- Serves `root` from `/srv/webapps/clients/<domain>/frontend`.
- Provides `.well-known/acme-challenge` handling for Certbot.
- Redirects HTTP to HTTPS after certificates are provisioned.

#### Proxy-only vhost

- Proxies all requests to localhost-bound upstreams.
- Uses shared proxy snippets to standardize headers and timeouts.
- Intended for the Auth/BFF stack (auth.* and api.* domains).

### Enablement rule

Vhosts in this directory are inert until symlinked into
`/etc/nginx/sites-enabled` and NGINX is reloaded.

---

## Git-First Minimal Steps to Add a New Client Website

## Decide the client identifiers (no commands yet)
You need only:
    Domain: newclient.com
    Repo directory: srv/webapps/clients/newclient.com/frontend
    Whether it uses the platform backend (most do)

## Add the nginx site config (IN REPO)
Create:
```txt
etc/nginx/sites-available/newclient.com.conf
```
Minimal standard config:
```txt
server {
    listen 80;
    server_name newclient.com www.newclient.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl;
    server_name newclient.com www.newclient.com;

    root /srv/webapps/clients/newclient.com/frontend;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    # Only if this client uses the shared Flask platform
    # location /api/ {
    #     proxy_pass http://127.0.0.1:8000;
    #     include proxy_params;
    # }

    ssl_certificate /etc/letsencrypt/live/newclient.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/newclient.com/privkey.pem;
}
```
Also add the symlink file (IN REPO):
```txt
etc/nginx/sites-enabled/newclient.com.conf
```
This should be a symlink in Git, pointing to:
```txt
../sites-available/newclient.com.conf
```
Commit both.

## Confirm DNS points to this instance (must match)
Run on the server:
```bash
dig +short cuyahogavalleycountrysideconservancy.org
dig +short www.cuyahogavalleycountrysideconservancy.org
curl -s https://checkip.amazonaws.com
```
The dig results must match the IP from checkip.

## Ensure port 80 is reachable
Let’s Encrypt HTTP-01 requires inbound port 80.
        Security Group must allow 0.0.0.0/0 → TCP 80
        Nginx must be listening on 80
Quick check:
```bash
sudo ss -lntp | grep -E ':(80|443)\b'
```

## Run certbot to add the new names
Because you already have an existing cert, the cleanest approach is usually to expand it (certbot will prompt/handle this).
Run:
```txt
sudo certbot --nginx \
  -d fruitfulnetworkdevelopment.com -d www.fruitfulnetworkdevelopment.com \
  -d cuyahogaterravita.com -d www.cuyahogaterravita.com \
  -d cuyahogavalleycountrysideconservancy.org -d www.cuyahogavalleycountrysideconservancy.org
```
This tells certbot exactly which SANs you want on the renewed certificate.

### Reload and verify
```bash
sudo nginx -t
sudo systemctl reload nginx
```
Then re-check certificate SANs:
```bash
echo | openssl s_client -connect cuyahogavalleycountrysideconservancy.org:443 \
  -servername cuyahogavalleycountrysideconservancy.org 2>/dev/null \
  | openssl x509 -noout -ext subjectAltName
```
You should now see DNS:cuyahogavalleycountrysideconservancy.org in the output.

## DNS: point the domain at your server (outside Git)
Create A records:
```txt
newclient.com        → <Elastic IP>
www.newclient.com    → <Elastic IP>
```
Wait for propagation.


## Deploy using only your standard commands (ON SERVER)
```bash
cd /home/admin/aws-box
git fetch origin
git pull --ff-only

sudo rsync -a --delete /home/admin/aws-box/srv/ /srv/
sudo rsync -a --delete /home/admin/aws-box/etc/ /etc/

sudo nginx -t
sudo systemctl reload nginx
```
If nginx -t fails, stop and fix the repo — do not patch /etc.

## Issue TLS certs (runtime action, not in Git)
```txt
sudo certbot --nginx -d newclient.com -d www.newclient.com
```
Test:
```txt
sudo certbot renew --dry-run
```

## Verify
```txt
curl -I https://newclient.com
```
Browser:
    Confirm correct site
    Confirm no default site leakage


