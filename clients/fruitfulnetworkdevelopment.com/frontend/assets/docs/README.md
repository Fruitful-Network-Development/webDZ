---
title: "Articles Directory — README"
slug: "README"
summary: "This directory contains reference style (Wikipedia like) articles used as “Read More” links across the Fruitful Network Development website."
entity_type: "index"
topics: []
claims: []
source_links: []
last_reviewed: "2026-04-16"
status: "active"
related_docs: []
supports_claims: []
supersedes: []
---
# Articles Directory — README

## Purpose

This directory contains **reference-style (Wikipedia-like)** articles used as “Read More” links across the Fruitful Network Development website.  
Articles should be **topic-bounded**, **precise**, and **non-promotional**.

## Expected location

These files are expected to live under:

- `webapps/clients/fruitfulnetworkdevelopment.com/articles/`

If you relocate them, keep links and build steps consistent with your site’s routing.

## Contents (current)

- `fiscal_sponsorship_programs_taxes.polished.md`  
  Fiscal sponsorship vs. sponsorship agreement; donation restriction/conditionality; bookkeeping implications.

- `modern_models_in_local_agriculture.polished.md`  
  A survey of modern regional/local agriculture operating models with examples.

- `ne_ohio_greenhouse_industry.md`  
  Northeast Ohio greenhouse industry history and its economic/infra implications.

- `ne_ohio_historic_local_food_system.md`  
  Historic local food system infrastructure and mechanisms in Northeast Ohio.

- `cuyahoga_valley_countryside_initiative.md`  
  The Countryside Initiative (CVCC) as a case study: structure, mechanisms, and role in regional food systems.

## House style (non-negotiable)

- **Reference tone:** avoid “we/our/you,” avoid marketing language.
- **Topic purity:** do not introduce unrelated project concepts unless they are the direct subject.
- **Definitions first:** define key terms near first use.
- **Concrete structure:** use headings, short paragraphs, and lists; prefer mechanisms over opinions.
- **Citations:** where factual claims depend on external sources, use a short “References” section.
- **Length target:** generally **1–3 pages** when printed (history/models may exceed).

## Filename rules

- Use lowercase + underscores: `topic_subtopic_region.md`
- Prefer explicit geography/time when relevant: `ne_ohio_…`, `historic_…`, `modern_…`
- If you publish “polished” variants, keep the suffix consistent: `.polished.md`

## Linking guidance (site integration)

- Link using stable slugs derived from filenames (recommended):
  - `/read-more/<filename-without-extension>`
- Keep the first heading as the canonical page title (`# Title`).

## Common operations

### List articles

```bash
# Run from: webapps/clients/fruitfulnetworkdevelopment.com/articles/
cd /srv/webapps/clients/fruitfulnetworkdevelopment.com/articles/
ls -la
```

### Quick spell/format check (lightweight)

```bash
# Run from: webapps/clients/fruitfulnetworkdevelopment.com/articles/
cd /srv/webapps/clients/fruitfulnetworkdevelopment.com/articles/
# If you have markdownlint installed:
markdownlint *.md
```

### Add a new article (template)

```bash
# Run from: webapps/clients/fruitfulnetworkdevelopment.com/articles/
cd /srv/webapps/clients/fruitfulnetworkdevelopment.com/articles/
cat > new_article_name.md <<'EOF'
# Title

## Summary
(2–4 sentences. Define the topic boundary.)

## Definitions
- **Term:** definition

## Main content
(Use headings; keep claims precise.)

## References
- (Optional)
EOF
```

### Rename an article safely

```bash
# Run from: webapps/clients/fruitfulnetworkdevelopment.com/articles/
cd /srv/webapps/clients/fruitfulnetworkdevelopment.com/articles/
git mv old_name.md new_name.md
```

## Maintenance checklist

- [ ] Remove any “SBIR / Phase / proposal” meta language (unless the article is explicitly about SBIR).
- [ ] Ensure examples are labeled as examples (not implied universal truths).
- [ ] Confirm headings reflect an encyclopedia outline (not a sales funnel).
- [ ] Keep internal cross-links minimal and directly relevant.
## Ownership boundary

Marketing/editorial teams maintain source materials in `assets/docs/*`.
Renderer/runtime pipelines decide delivery placement for each artifact:

- in-page hidden machine blocks (`machine/inpage/*`) for non-visual embed patterns, or
- standalone machine pages (`machine/pages/*`) for crawler/agent endpoints.


## Canonical source priority (`docs/` vs `assets/docs/`)

Machine-document generation uses a **synchronized mirror strategy**:

1. **Canonical source of truth:** repository-level `docs/` (authoring + review source).
2. **Frontend mirror:** `clients/fruitfulnetworkdevelopment.com/frontend/assets/docs/` (published machine endpoints).
3. Build/update scripts read from `docs/` first and then overwrite/update the frontend mirror artifacts deterministically.

This keeps editorial provenance in one location while preserving stable public URLs for crawlers and agents.

## LLM Optimization Source Bundle

Canonical source and generated machine artifacts for LLM consumption live in this folder:

- `LLM-optimization-report.md` (canonical machine-ingestion source)
- `llm-optimization-manifest.json` (deterministic extraction map + artifact registry)
- `LLM-optimization-report.machine-brief.md`
- `LLM-optimization-report.citation-graph.json`
- `LLM-optimization-report.entity-profiles.jsonld`

All of the above include explicit `version` and `last_updated` fields for traceable updates.

### Lint check for required sections

```bash
python3 clients/fruitfulnetworkdevelopment.com/frontend/assets/docs/scripts/lint_llm_docs.py \
  clients/fruitfulnetworkdevelopment.com/frontend/assets/docs/LLM-optimization-report.md
```

