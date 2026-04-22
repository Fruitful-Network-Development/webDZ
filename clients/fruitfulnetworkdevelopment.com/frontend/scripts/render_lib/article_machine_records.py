from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ENTITY_PATTERN = re.compile(r"entity(\[[^\]]+\])")
URL_PATTERN = re.compile(r"https?://[^\s)>\"']+")
HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.*)$")
BULLET_PATTERN = re.compile(r"^\s*(?:[-*]|\d+[.)])\s+(.*)$")

SECTION_KEYWORDS = {
    "claims": ("claim", "replace/correct"),
    "accolades": ("accolade", "proof point", "award", "recognition"),
    "roadmap_items": ("roadmap", "milestone", "future"),
}

SERVICE_PAGE_MAP = {
    "default": [
        "/services.html",
        "/subpages/payment-processing.html",
        "/subpages/pos.html",
        "/subpages/email-management.html",
    ],
    "fiscal": ["/services.html", "/subpages/payment-processing.html"],
    "market": ["/services.html", "/subpages/pos.html"],
    "regenerative": ["/services.html"],
    "opensource": ["/services.html", "/subpages/email-management.html"],
}

RESEARCH_PAGE_MAP = {
    "default": ["/research.html", "/subpages/articles.html"],
    "historic": ["/research.html", "/subpages/articles.html"],
    "market": ["/research.html", "/subpages/articles.html?doc=market_transparency.md"],
    "regenerative": ["/research.html", "/subpages/articles.html?doc=regenerative_farming.md"],
}


def _load_json_file(path: Path, *, default: dict[str, Any]) -> dict[str, Any]:
    if not path.exists():
        return dict(default)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return dict(default)
    return payload if isinstance(payload, dict) else dict(default)


def _parse_scalar(raw_value: str) -> Any:
    value = raw_value.strip()
    if value.startswith('"') and value.endswith('"') and len(value) >= 2:
        return value[1:-1]
    if value in {"[]", "[ ]"}:
        return []
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        if not inner:
            return []
        return [part.strip().strip('"') for part in inner.split(",")]
    return value


def _parse_frontmatter(markdown_text: str) -> tuple[dict[str, Any], str]:
    if not markdown_text.startswith("---\n"):
        return {}, markdown_text

    end = markdown_text.find("\n---\n", 4)
    if end < 0:
        return {}, markdown_text

    header = markdown_text[4:end]
    body = markdown_text[end + 5 :]
    frontmatter: dict[str, Any] = {}
    for line in header.splitlines():
        if not line.strip() or ":" not in line:
            continue
        key, raw = line.split(":", 1)
        frontmatter[key.strip()] = _parse_scalar(raw)
    return frontmatter, body


def _collect_section_items(markdown_body: str, keywords: tuple[str, ...]) -> list[str]:
    current_heading = ""
    capture = False
    items: list[str] = []

    for line in markdown_body.splitlines():
        heading_match = HEADING_PATTERN.match(line)
        if heading_match:
            current_heading = heading_match.group(2).strip().lower()
            capture = any(keyword in current_heading for keyword in keywords)
            continue

        if not capture:
            continue

        bullet_match = BULLET_PATTERN.match(line)
        if bullet_match:
            items.append(bullet_match.group(1).strip())

    return items


def _extract_entities(markdown_body: str) -> list[dict[str, str]]:
    entities: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for match in ENTITY_PATTERN.findall(markdown_body):
        try:
            payload = json.loads(match)
        except json.JSONDecodeError:
            continue
        if not isinstance(payload, list) or len(payload) < 2:
            continue
        entity_type = str(payload[0]).strip()
        entity_name = str(payload[1]).strip()
        if not entity_name:
            continue
        key = (entity_type, entity_name)
        if key in seen:
            continue
        seen.add(key)
        entities.append(
            {
                "name": entity_name,
                "entity_type": entity_type or "unknown",
            }
        )
    return entities


def _extract_summary(frontmatter: dict[str, Any], markdown_body: str) -> str:
    summary = str(frontmatter.get("summary", "")).strip()
    if summary:
        return summary

    for line in markdown_body.splitlines():
        cleaned = line.strip()
        if cleaned and not cleaned.startswith("#"):
            return cleaned
    return ""


def _extract_urls(markdown_body: str) -> list[str]:
    urls: list[str] = []
    seen: set[str] = set()
    for url in URL_PATTERN.findall(markdown_body):
        cleaned = url.rstrip(".,;)")
        if cleaned not in seen:
            seen.add(cleaned)
            urls.append(cleaned)
    return urls


def _choose_cross_links(doc_name: str) -> dict[str, list[str]]:
    lowered = doc_name.lower()

    service_links = SERVICE_PAGE_MAP["default"]
    research_links = RESEARCH_PAGE_MAP["default"]

    if "fiscal" in lowered:
        service_links = SERVICE_PAGE_MAP["fiscal"]
    elif "market" in lowered:
        service_links = SERVICE_PAGE_MAP["market"]
        research_links = RESEARCH_PAGE_MAP["market"]
    elif "regenerative" in lowered:
        service_links = SERVICE_PAGE_MAP["regenerative"]
        research_links = RESEARCH_PAGE_MAP["regenerative"]
    elif "opensource" in lowered:
        service_links = SERVICE_PAGE_MAP["opensource"]

    if "historic" in lowered:
        research_links = RESEARCH_PAGE_MAP["historic"]

    return {
        "related_service_pages": service_links,
        "related_research_pages": research_links,
    }


def generate_machine_records(frontend_root: Path, manifest: dict[str, Any]) -> None:
    docs_cfg = manifest.get("collections", {}).get("article_docs", {})
    docs_root = frontend_root / docs_cfg.get("root", "assets/docs")
    docs = docs_cfg.get("docs", [])

    references_path = docs_root / "citations" / "references.json"
    article_refs_path = docs_root / "citations" / "article-references.json"

    references_payload = _load_json_file(references_path, default={"sources": []})
    article_refs_payload = _load_json_file(article_refs_path, default={"articles": {}})

    source_by_id = {item["id"]: item for item in references_payload.get("sources", [])}
    article_ref_ids: dict[str, list[str]] = article_refs_payload.get("articles", {})

    records: list[dict[str, Any]] = []

    for doc_name in docs:
        markdown_path = docs_root / doc_name
        if not markdown_path.exists() or markdown_path.suffix.lower() != ".md":
            continue

        markdown_text = markdown_path.read_text(encoding="utf-8")
        frontmatter, body = _parse_frontmatter(markdown_text)

        claim_items = _collect_section_items(body, SECTION_KEYWORDS["claims"])
        accolade_items = _collect_section_items(body, SECTION_KEYWORDS["accolades"])
        roadmap_items = _collect_section_items(body, SECTION_KEYWORDS["roadmap_items"])

        if not claim_items and isinstance(frontmatter.get("claims"), list):
            claim_items = [str(item) for item in frontmatter["claims"]]

        external_refs: list[dict[str, Any]] = []
        seen_urls: set[str] = set()

        for ref_id in article_ref_ids.get(doc_name, []):
            source = source_by_id.get(ref_id)
            if not source:
                continue
            source_copy = {
                "id": source.get("id"),
                "title": source.get("title"),
                "url": source.get("url"),
                "publisher": source.get("publisher"),
                "date_accessed": source.get("date_accessed"),
            }
            url = str(source_copy.get("url", ""))
            if url and url not in seen_urls:
                external_refs.append(source_copy)
                seen_urls.add(url)

        for url in _extract_urls(body):
            if url in seen_urls:
                continue
            external_refs.append({"url": url})
            seen_urls.add(url)

        last_updated = str(
            frontmatter.get("last_reviewed")
            or datetime.fromtimestamp(markdown_path.stat().st_mtime, tz=UTC).date().isoformat()
        )

        title = str(frontmatter.get("title") or doc_name)
        slug = str(frontmatter.get("slug") or markdown_path.stem)

        cross_links = _choose_cross_links(doc_name)

        record = {
            "@context": "https://schema.org",
            "@type": "Article",
            "id": f"fnd-article-{slug}",
            "slug": slug,
            "path": f"/assets/docs/{doc_name}",
            "title": title,
            "summary": _extract_summary(frontmatter, body),
            "claims": claim_items,
            "accolades": accolade_items,
            "roadmap_items": roadmap_items,
            "entities": _extract_entities(body),
            "external_references": external_refs,
            "last_updated": last_updated,
            "related_docs": frontmatter.get("related_docs", []) if isinstance(frontmatter.get("related_docs"), list) else [],
            **cross_links,
        }
        records.append(record)

    records.sort(key=lambda item: item["slug"])

    today = datetime.now(UTC).date().isoformat()
    site_domain = "https://fruitfulnetworkdevelopment.com"

    article_index = {
        "schema_version": "1.0",
        "generated_at": today,
        "site": site_domain,
        "record_schema": {
            "fields": [
                "title",
                "summary",
                "claims",
                "accolades",
                "roadmap_items",
                "entities",
                "external_references",
                "last_updated",
                "related_service_pages",
                "related_research_pages",
            ]
        },
        "records": records,
    }

    citation_index = {
        "site": "fruitfulnetworkdevelopment.com",
        "updated": today,
        "citations": [
            {
                "topic": "Canonical company brief",
                "url": f"{site_domain}/llms.md",
                "type": "narrative",
            },
            {
                "topic": "Machine reference explorer",
                "url": f"{site_domain}/machine/pages/references.html",
                "type": "machine-page",
            },
            {
                "topic": "Article machine index",
                "url": f"{site_domain}/machine/pages/article-index.json",
                "type": "dataset",
            },
            {
                "topic": "Research thesis and technical framing",
                "url": f"{site_domain}/research.html",
                "type": "page",
            },
            {
                "topic": "Services and operating model",
                "url": f"{site_domain}/services.html",
                "type": "page",
            },
        ],
    }

    references_html = """<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\" />
  <title>Machine References | Fruitful Network Development</title>
  <meta name=\"robots\" content=\"index,follow\" />
  <link rel=\"stylesheet\" href=\"../../main.css\" />
</head>
<body>
  <main class=\"edition\">
    <section class=\"editorial editorial--linear\">
      <h1>Machine Reference Index</h1>
      <p>This page is for crawlers and agents. References are normalized and evidence-oriented.</p>
      <ul>
        <li><a href=\"/machine/pages/article-index.json\">Article index JSON</a></li>
        <li><a href=\"/machine/citation-index.json\">Citation index JSON</a></li>
        <li><a href=\"/machine/pages/fnd-machine-index.json\">Machine endpoint index</a></li>
      </ul>
      <section id=\"machine-citations-reference-page\" hidden aria-hidden=\"true\" data-machine=\"citations\"></section>
    </section>
  </main>

  <script src=\"../../js/citation-governance.js\" defer></script>
  <script>
    document.addEventListener('DOMContentLoaded', async () => {
      if (!window.FNDCitations) return;
      try {
        const payload = await window.FNDCitations.loadReferences();
        window.FNDCitations.renderCitationMachineBlock(
          document.getElementById('machine-citations-reference-page'),
          {
            page: '/machine/pages/references.html',
            references: payload.sources || [],
            evidence_policy: 'non-promotional, evidence-oriented references only'
          }
        );
      } catch (err) {
        // Machine route keeps human-facing output minimal.
      }
    });
  </script>
</body>
</html>
"""

    machine_pages_root = frontend_root / "machine" / "pages"
    machine_pages_root.mkdir(parents=True, exist_ok=True)

    (machine_pages_root / "article-index.json").write_text(json.dumps(article_index, indent=2) + "\n", encoding="utf-8")
    (frontend_root / "machine" / "citation-index.json").write_text(json.dumps(citation_index, indent=2) + "\n", encoding="utf-8")
    (machine_pages_root / "references.html").write_text(references_html, encoding="utf-8")

    endpoint_index_path = machine_pages_root / "fnd-machine-index.json"
    if endpoint_index_path.exists():
        try:
            endpoint_index = json.loads(endpoint_index_path.read_text(encoding="utf-8"))
            if not isinstance(endpoint_index, dict):
                endpoint_index = {"version": "1.0", "site": site_domain, "pages": []}
        except Exception:
            endpoint_index = {"version": "1.0", "site": site_domain, "pages": []}
    else:
        endpoint_index = {"version": "1.0", "site": site_domain, "pages": []}

    endpoint_index["updated_at"] = today
    pages = endpoint_index.setdefault("pages", [])

    def _upsert_page(rel: str, href: str, fmt: str) -> None:
        for page in pages:
            if page.get("rel") == rel:
                page["href"] = href
                page["format"] = fmt
                return
        pages.append({"rel": rel, "href": href, "format": fmt})

    _upsert_page("machine-index", "/machine/pages/fnd-machine-index.json", "application/json")
    _upsert_page("dataset", "/machine/pages/fnd-pages.manifest.json", "application/json")
    _upsert_page("article-index", "/machine/pages/article-index.json", "application/json")
    _upsert_page("citation-index", "/machine/citation-index.json", "application/json")
    _upsert_page("references", "/machine/pages/references.html", "text/html")
    _upsert_page("llm-context", "/llms.md", "text/markdown")

    endpoint_index["pages"] = sorted(pages, key=lambda item: str(item.get("rel", "")))
    endpoint_index_path.write_text(json.dumps(endpoint_index, indent=2) + "\n", encoding="utf-8")
