# /srv/webapps

## Web surface

This directory contains all web-facing assets: static client sites and the
shared platform API.

## Purpose

Explain the split between static clients and the shared platform.

## Clients

- Each client gets a domain-bound directory under `/srv/webapps/clients/`.
- Static assets live in `frontend/` and are served directly by NGINX.
- Client data files live in `data/` and are only exposed through the API if
  whitelisted in a manifest.

## Platform (shared Flask API)

The shared platform exists for two reasons:

1. **Manifest lookup**: determine which client is making a request based on the
   incoming host header and load that client’s manifest file.
2. **Dataset registry**: expose read-only JSON data to the frontend through
   stable API routes. Data files must live under a client’s `data/` directory
   and be explicitly whitelisted in the manifest.

### Data-access helpers

- `multi-tennant-data-access.py`
  - Detects the client slug from `X-Forwarded-Host` or `Host`.
  - Locates client directories under `/srv/webapps/clients/<domain>`.
  - Loads a client manifest (`msn_*.json`) and normalizes key settings.
- `client-data-acess.py`
  - Lists dataset IDs based on the manifest’s `backend_data` list.
  - Resolves dataset IDs to safe paths under a client’s `data/` directory.

Because these filenames contain hyphens, the platform loads them via
`importlib` instead of standard imports.

### Manifest lookup and data access flow

1. **Client detection**: inspect `X-Forwarded-Host` or `Host` and fall back to
   `DEFAULT_CLIENT_SLUG` if needed.
2. **Manifest loading**: discover `msn_*.json` at the client root. The manifest
   can set `frontend_root`, `default_entry`, and `backend_data`.
3. **Dataset registry**:
   - `GET /api/datasets` returns allowed dataset IDs.
   - `GET /api/datasets/<dataset_id>` returns dataset JSON contents.

### Adding endpoints

If new API routes are required, add Flask Blueprints under `modules/` and
register them in `app.py`. Keep these constraints:

- Avoid arbitrary filesystem access; always scope reads to safe directories.
- Use the manifest to toggle per-client behavior.
- Keep the core app minimal; move complex logic to separate services if needed.

### Migration To New Set Up Details
  - Realm: fruitful
  - Client ID: flask-bff
  - Redirect URI (Phase 3): http://localhost:8001/callback
  - Web origin (Phase 3): http://localhost:8001
  - Flows enabled: Standard flow ON, Implicit OFF, Direct grants OFF

- `GET` `/health` returns 200
- `GET` `/me` returns 401 when logged out
- Login sets a session cookie (HttpOnly, SameSite=Lax)
- Login requires `tenant=<tenant_id>` and can accept `return_to=<url>` (validated against `RETURN_TO_ALLOWLIST`)
- `GET` `/me` returns identity after login
- `GET` `/t/<tenant_id>/ping` returns tenant-scoped JSON when authorized
- Logout clears the session
