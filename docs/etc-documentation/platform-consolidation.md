# Platform Consolidation and NGINX Role

This note documents how the consolidated platform under `/srv/compose/platform`
relies on host-level NGINX. It complements
`/home/admin/aws-box/docs/etc-documentation/etc.md`.

## Why NGINX remains necessary

NGINX is still the public ingress and TLS terminator. The platform stack runs in
containers bound to localhost, so NGINX is required to:

- Serve static client sites from `/srv/webapps/clients/<domain>/frontend`.
- Proxy `auth.<domain>` to the Keycloak container.
- Proxy `api.<domain>` to the Flask BFF container.

This keeps static sites and application logic separated while enforcing that no
container ports are directly exposed to the public internet.

## Operational expectations

- NGINX configuration remains host-managed under `/etc/nginx`.
- Compose services bind to `127.0.0.1` only.
- Static sites remain static; no application logic is served from NGINX.

## When to change NGINX

Update NGINX vhosts only when:

- A new client domain is added or removed.
- An `auth.*` or `api.*` subdomain changes.
- TLS certificates need to be issued or renewed.
