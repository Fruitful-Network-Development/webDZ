# CVCC Manifest Build

This frontend now renders static public HTML from `assets/docs/manifest.json` using `python3 scripts/render_manifest.py`.

Workflow:
- `manifest.json` defines shell config, navigation, footer, page registration, and collection references.
- `assets/docs/blogs/*.md` are front-matter markdown source files for newsletter/blog content.
- `assets/docs/board_profiles.json`, `assets/docs/happenings.json`, and `assets/docs/timeline.json` remain layered source datasets.
- `assets/docs/fragments/*.html` hold manual static page bodies for pages that do not need collection-driven rendering.
- `scripts/render_manifest.py` builds the final page HTML files without requiring client-side content fetches.
