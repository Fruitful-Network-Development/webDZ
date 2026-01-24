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

