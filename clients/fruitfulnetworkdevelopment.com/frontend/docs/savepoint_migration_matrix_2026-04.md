# FND Save-Point Migration Matrix (2026-04)

Scope:
- Source: `refs/remotes/origin/save_point-04-15-2026`
- Target baseline: `origin/main`
- Compared path: `clients/fruitfulnetworkdevelopment.com/frontend`
- Compare command: `git diff --name-status origin/main refs/remotes/origin/save_point-04-15-2026 -- clients/fruitfulnetworkdevelopment.com/frontend`

Delta summary:
- `A`: 40 files
- `M`: 33 files
- `D`: 1 file

Policy keys:
- `keep`: transplant directly from save-point with no structural rewrite in this phase.
- `adapt`: transplant, then normalize for canonical `machine` shape, modular manifest sections, and deterministic local-source pipelines.
- `drop`: do not transplant into active branch.

## Decisions

| Path pattern / file set | Decision | Phase | Rationale |
|---|---|---|---|
| `frontend/scripts/**` | keep | commit 1 | Required parity render/check pipeline for manifest-driven generation and CI-like local validation. |
| `frontend/README.md` | keep | commit 1 | Documents renderer/check contract and migration guardrails used by this rollout. |
| `frontend/assets/docs/manifest.json` (save-point version) | adapt | commit 2 | Keep schema and machine contract, but refactor from monolithic `main_html` pages to modular section schema with stable ids and editor metadata. |
| `frontend/index.html`, `services.html`, `research.html`, `about.html`, `contact.html`, `subpages/*.html` | adapt | commit 2 | Preserve URL/output parity while shifting source-of-truth to modular manifest and template renderer internals. |
| `frontend/js/article-viewer.js` | adapt | commit 2 | Keep behavior while aligning with modular manifest/article source wiring. |
| `frontend/assets/docs/*.md` save-point rewrites | adapt | commit 4 | Fold into deterministic llm/machine pipeline while preserving existing local working-tree docs that pre-date this migration. |
| `frontend/assets/docs/LLM-optimization-report.*` | adapt | commit 4 | Keep machine artifacts but remove hard dependency on `/srv/webapps/docs/LLM-optimization-report.md`; use frontend-local canonical source + optional mirror strategy. |
| `frontend/assets/docs/citations/**` | keep | commit 4 | Required for citation graph and machine reference normalization. |
| `frontend/assets/docs/llm-optimization-manifest.json` | adapt | commit 4 | Retain deterministic extraction map, normalize source-path strategy to existing repo realities. |
| `frontend/assets/docs/manifest-schema.lock.json` | keep | commit 4 | Enforces schema lock gate for controlled manifest evolution. |
| `frontend/assets/seo/structured-data.manifest.json` | keep | commit 4 | Canonical source for page-level JSON-LD and machine hub outputs. |
| `frontend/js/citation-governance.js`, `js/citations-page.js` | keep | commit 4 | Supports machine citation rendering surfaces and reference endpoints. |
| `frontend/machine/**` | keep | commit 4 | Required machine-readable endpoint surfaces (`llms.txt` index path, page manifest, references, citation index). |
| `frontend/llms.md`, `frontend/llms.txt` | adapt | commit 4 | Keep public/context outputs, regenerate deterministically from canonical content sources. |
| `frontend/assets/docs/Information_Technology_Social_Systems.pdf` deletion | drop | n/a | Do not apply save-point deletion during this migration to avoid unintended content retirement. |

## Explicit non-goals in this migration

- No history merge with save-point branch (unrelated histories).
- No destructive cleanup or revert of existing uncommitted local FND documents.
- No API/route breakage in `mycite-core` `FND-DCM`; only additive surface/extensions updates.
