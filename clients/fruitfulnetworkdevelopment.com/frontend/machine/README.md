# Machine Surface Layout

This directory separates machine-targeted outputs into two explicit classes:

- `machine/inpage/`: hidden blocks that are injected into rendered human pages using non-visual data containers (for example, `<script type="application/ld+json">` or `<script type="application/json">`).
- `machine/pages/`: standalone machine pages/endpoints intended for bots, agents, and scrapers.

## Routing policy

- Machine pages must remain routable by direct URL.
- Machine pages are excluded from primary user navigation.
- Discoverability for machine pages should come from `sitemap.xml` and/or `machine/machine-index.json`.

## Ownership boundary

Marketing/editorial teams own and update source documents under `assets/docs/*`.
The renderer owns placement decisions and decides whether each artifact is emitted as:

1. an in-page hidden block under `machine/inpage/`, or
2. a standalone machine page under `machine/pages/`.
