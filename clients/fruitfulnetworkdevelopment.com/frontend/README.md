# Fruitful Network Development Frontend

## Manifest-driven rendering workflow

Developer note: **edit `assets/docs/manifest.json` (and supporting docs in `assets/docs/`), then render**.

```bash
cd clients/fruitfulnetworkdevelopment.com/frontend
python scripts/render_manifest.py
```

This regenerates the primary pages and `subpages/*.html` from the canonical manifest source.

## Manifest schema contract (enforced at build time)

`scripts/render_lib/content_loader.py` validates `assets/docs/manifest.json` before rendering.

Required top-level keys:

- `schema_identifier` (must match `schema` when `schema` is present)
- `site`
- `navigation`
- `pages`
- `machine`

Required page fields:

- Every page: `file`, `template`
- Template pages (`fnd_home`, `fnd_services`, `fnd_research`, `fnd_about`, `fnd_contact`, `fnd_subpage`):
  - `title`
  - `head.stylesheets`
  - `content.main_html`
  - `shell`
- Verbatim templates (`verbatim_document`, `verbatim_fragment`):
  - `source_html`

Required machine-surface declarations:

- `machine.inpage.root`
- `machine.inpage.blocks[*].id`
- `machine.inpage.blocks[*].source`
- `machine.inpage.blocks[*].injection_pattern`
- `machine.inpage.blocks[*].page` (or `page_key`)
- `machine.pages.root`
- `machine.pages.endpoints[*].rel`
- `machine.pages.endpoints[*].href`
- `machine.pages.endpoints[*].format`
- `machine.endpoint_maps.machine_index`
- `machine.endpoint_maps.page_manifest`
- `machine.endpoint_maps.llm_context`

Additional linkage checks:

- `endpoint_maps.machine_index` and `endpoint_maps.page_manifest` must point to an `href` listed in `machine.pages.endpoints`.
- `endpoint_maps.organization_schema_id` (if present) must match an in-page block id in `machine.inpage.blocks`.

Validation failures stop the build and include exact manifest key paths (for example:
`manifest.pages.home.content.hero.heading`) so missing fields can be fixed directly.

## Migration PR checklist (manifest/schema work)

Before opening or approving migration PRs, run:

```bash
python scripts/check_visible_dom_regression.py
python scripts/check_machine_surface_diff.py
```

- [ ] visible DOM unchanged
- [ ] machine endpoints expanded

Schema upgrade enforcement:

- `assets/docs/manifest-schema.lock.json` pins the accepted `schema_identifier`.
- Any manifest schema bump must update the lock file in the same PR after both checks pass.
