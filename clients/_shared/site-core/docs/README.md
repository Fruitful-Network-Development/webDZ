# Site Core (Shared)

Shared reusable CSS primitives for hosted frontends.

## Source of truth

- `clients/_shared/site-core/css/core.css`

## Sync command

Run from repo root:

```bash
python3 clients/_shared/site-core/scripts/sync_site_core.py
```

This syncs generated local copies to:

- `clients/fruitfulnetworkdevelopment.com/frontend/css/shared-core.css`
- `clients/trappfamilyfarm.com/frontend/css/shared-core.css`
- `clients/cuyahogavalleycountrysideconservancy.org/frontend/CSS/shared-core.css`

Each site keeps its own local theme tokens and component styles.
