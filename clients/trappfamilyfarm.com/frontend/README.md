# Trapp Family Farm frontend

This site now renders from `assets/docs/manifest.json`, plus source Markdown documents referenced by the manifest.

Workflow:

```bash
cd /srv/webapps/clients/trappfamilyfarm.com/frontend
python3 scripts/render_manifest.py
```

The manifest is the content source of truth.

- `assets/docs/manifest.json` stores site metadata, navigation, shell settings, footer columns, page registration, template selection, and source references.
- `assets/docs/newsletters/*.md` stores long-form newsletter content with front matter and Markdown body.
- `scripts/render_manifest.py` is the build entrypoint.
- `scripts/render_lib/` contains reusable manifest loading, Markdown parsing, shell rendering, and template-family renderers.
- `js/site-shell.js` is progressive enhancement only for the sticky header and mobile drawer.

The public page body content is compiled into the HTML files, so the site still works when JavaScript is disabled.
