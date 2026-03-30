# Trapp Family Farm frontend

This site now renders from `assets/docs/manifest.json`.

Workflow:

```bash
cd /srv/webapps/clients/trappfamilyfarm.com/frontend
python3 scripts/render_manifest.py
```

The manifest is the content source of truth.

- `assets/docs/manifest.json` stores site metadata, navigation, footer data, and page content in explicit fields.
- `scripts/render_manifest.py` is the build-time renderer that materializes the public HTML pages.
- `js/site-shell.js` is progressive enhancement only for the sticky header and mobile drawer.

The public page body content is compiled into the HTML files, so the site still works when JavaScript is disabled.
