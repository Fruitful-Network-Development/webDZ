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
