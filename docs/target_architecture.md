# Target Architecture

## Goals
- Separate platform core invariants, tenant context, and external service integrations.
- Load the JSON data environment from `DATA_ENV_ROOT` via a repository API.
- Keep existing routes/services working via compatibility imports.

## Layering Overview

### core/
- `core/config/`: centralized config (env var parsing, defaults).
- `core/logging/`: shared logging setup.
- `core/errors/`: domain-specific exceptions.
- `core/auth/`: auth-neutral helpers or interfaces.
- `core/policy/`: read-only policy rules (e.g., MSS exposed resources).
- `core/data_env/`: data environment loader + repository API.

### adapters/
- `adapters/filesystem_json/`: JSON filesystem adapter for `/srv/demo-data`.
- `adapters/keycloak/`: future Keycloak integration boundary.

### platform/
- `platform/admin/`: admin routes (read-only data env views initially).
- `platform/api/`: platform API routes (future).
- `platform/schemas/`: optional schema validators.

### tenant/
- `tenant/api/`: tenant APIs (stubs).
- `tenant/console/`: tenant console scaffolding (stubs).

### services/
- `services/paypal/`: integration placeholder.

## Data Environment (Bootstrap)
- A bootstrap file `platform.profile.json` lives at the data root.
- It maps core resources (mss/local/manifest/fnd) to resource IDs found in JSON files.
- No hard-coded resource IDs in Python.

Example shape:
```json
{
  "platform_mss": "platform.mss",
  "platform_local": "platform.local",
  "platform_manifest": "platform.manifest",
  "platform_fnd": "platform.fnd"
}
```

## Data Env Repository API
- `list_resources()` -> list[str]
- `get_resource(resource_id: str)` -> dict
- `find_by_local_id(local_id: str)` -> optional mapping
- `get_platform_mss()` / `get_platform_manifest()` / `get_platform_local()` / `get_platform_fnd()`

## Wiring into Flask
- Initialize repository on app startup.
- Attach to `app.extensions["data_env"]`.
- Add admin JSON endpoints for read-only access.

