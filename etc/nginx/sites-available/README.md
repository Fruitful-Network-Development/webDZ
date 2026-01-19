# /etc/nginx/sites-available

## Vhost patterns

This directory holds **inactive** virtual host definitions. Files here do
nothing until symlinked into `sites-enabled`.

## Purpose

Document how vhosts are structured and how they are activated.

## Naming convention

- `<domain>.conf` for site-specific vhosts.
- `auth.<domain>.conf` for Keycloak/Auth proxy vhosts.
- `api.<domain>.conf` for BFF/API proxy vhosts.

## Common patterns

### Static site vhost

- Serves `root` from `/srv/webapps/clients/<domain>/frontend`.
- Provides `.well-known/acme-challenge` handling for Certbot.
- Redirects HTTP to HTTPS after certificates are provisioned.

### Proxy-only vhost

- Proxies all requests to localhost-bound upstreams.
- Uses shared proxy snippets to standardize headers and timeouts.
- Intended for the Auth/BFF stack (auth.* and api.* domains).

## Enablement rule

Vhosts in this directory are inert until symlinked into
`/etc/nginx/sites-enabled` and NGINX is reloaded.
