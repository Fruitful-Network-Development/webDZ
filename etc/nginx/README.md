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
