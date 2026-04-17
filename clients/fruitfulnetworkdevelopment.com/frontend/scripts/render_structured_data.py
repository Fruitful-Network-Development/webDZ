#!/usr/bin/env python3
"""Render page JSON-LD/canonicals and build machine-readable LLM artifacts."""
from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

FRONTEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = FRONTEND_ROOT.parents[2]
MANIFEST_PATH = FRONTEND_ROOT / "assets/seo/structured-data.manifest.json"
CANONICAL_REPORT_PATH = REPO_ROOT / "docs/LLM-optimization-report.md"
FRONTEND_REPORT_MIRROR_PATH = FRONTEND_ROOT / "assets/docs/LLM-optimization-report.md"
MACHINE_BRIEF_PATH = FRONTEND_ROOT / "assets/docs/LLM-optimization-report.machine-brief.md"
CITATION_GRAPH_PATH = FRONTEND_ROOT / "assets/docs/LLM-optimization-report.citation-graph.json"
ENTITY_PROFILE_PATH = FRONTEND_ROOT / "assets/docs/LLM-optimization-report.entity-profiles.jsonld"
CITATION_INDEX_PATH = FRONTEND_ROOT / "machine/citation-index.json"
DOCS_CORPUS_MAP_PATH = FRONTEND_ROOT / "machine/docs-corpus-map.json"
HUBS_PATH = FRONTEND_ROOT / "machine/structured-data-hubs.json"
LLMS_TXT_PATH = FRONTEND_ROOT / "llms.txt"
LLMS_MD_PATH = FRONTEND_ROOT / "llms.md"
SITEMAP_PATH = FRONTEND_ROOT / "sitemap.xml"

TODAY = date.today().isoformat()
VERSION = "1.1.0"
REQUIRED_SECTIONS = [
    "Document Metadata",
    "Core Claims",
    "Company Facts",
    "Milestones And Future Roadmap",
    "Accolades And Proof Points",
    "Citations And External References",
]


def absolute_url(base: str, path: str) -> str:
    if path.startswith("http://") or path.startswith("https://"):
        return path
    return f"{base.rstrip('/')}{path}"


def build_breadcrumb(base_url: str, items: list[dict]) -> dict:
    return {
        "@type": "BreadcrumbList",
        "itemListElement": [
            {
                "@type": "ListItem",
                "position": index + 1,
                "name": item["name"],
                "item": absolute_url(base_url, item["path"]),
            }
            for index, item in enumerate(items)
        ],
    }


def render_page(html_path: Path, manifest: dict, page_path: str, cfg: dict) -> None:
    text = html_path.read_text(encoding="utf-8")

    canonical_path = "/" if page_path == "/index.html" else page_path
    canonical_url = absolute_url(manifest["baseUrl"], canonical_path)
    canonical_line = f'  <link rel="canonical" href="{canonical_url}" />\n'

    if 'rel="canonical"' in text:
        text = re.sub(r"\s*<link rel=\"canonical\" href=\"[^\"]*\"\s*/>\n", canonical_line, text, count=1)
    else:
        text = text.replace("</head>\n", canonical_line + "</head>\n", 1)

    graph = [manifest["organization"], manifest["website"], build_breadcrumb(manifest["baseUrl"], cfg.get("breadcrumb", []))]
    if cfg.get("includeServices"):
        graph.extend(manifest.get("services", []))
    if cfg.get("includePerson"):
        graph.append(manifest["person"])
    if cfg.get("includeDocs"):
        graph.append(manifest["docs"]["dataset"])
        graph.extend(manifest["docs"].get("articles", []))
        graph.extend(manifest["docs"].get("reports", []))
    if cfg.get("includeReport"):
        graph.extend(manifest["docs"].get("reports", []))

    payload = {"@context": "https://schema.org", "@graph": graph}
    jsonld = json.dumps(payload, indent=2)
    block = (
        '  <script type="application/ld+json" data-structured-data="page">\n'
        f"{jsonld}\n"
        "  </script>\n"
    )

    start_marker = '  <script type="application/ld+json" data-structured-data="page">'
    if start_marker in text:
        before = text.split(start_marker, 1)[0]
        after = text.split("  </script>\n", 1)[1]
        text = before + block + after
    else:
        text = text.replace("</head>\n", block + "</head>\n", 1)

    text = text.replace('  <script src="./js/structured-data.js" defer></script>\n', "")
    text = text.replace('  <script src="../js/structured-data.js" defer></script>\n', "")

    html_path.write_text(text, encoding="utf-8")


def parse_sections(markdown_text: str) -> dict[str, str]:
    sections: dict[str, str] = {}
    current = ""
    bucket: list[str] = []
    for line in markdown_text.splitlines():
        match = re.match(r"^##\s+(.+)$", line.strip())
        if match:
            if current:
                sections[current] = "\n".join(bucket).strip()
            current = match.group(1).strip()
            bucket = []
            continue
        if current:
            bucket.append(line)
    if current:
        sections[current] = "\n".join(bucket).strip()
    missing = [name for name in REQUIRED_SECTIONS if name not in sections]
    if missing:
        raise ValueError(f"Missing required sections: {', '.join(missing)}")
    return sections


def parse_numbered_items(section_text: str) -> list[str]:
    items: list[str] = []
    for line in section_text.splitlines():
        match = re.match(r"^\s*\d+\.\s+(.+)$", line.strip())
        if match:
            items.append(match.group(1).strip())
    return items


def parse_bulleted_items(section_text: str) -> list[str]:
    items: list[str] = []
    for line in section_text.splitlines():
        match = re.match(r"^\s*-\s+(.+)$", line)
        if match:
            items.append(match.group(1).strip())
    return items


def parse_company_facts(section_text: str) -> dict[str, str]:
    facts: dict[str, str] = {}
    for item in parse_bulleted_items(section_text):
        key, _, value = item.partition(":")
        if key and value:
            clean_key = key.replace("**", "").strip(" *").strip()
            clean_value = value.replace("**", "").strip()
            facts[clean_key] = clean_value
    return facts


def parse_citation_urls(section_text: str) -> list[str]:
    urls: list[str] = []
    for line in section_text.splitlines():
        match = re.search(r"https?://[^\s)]+", line)
        if match:
            urls.append(normalize_url(match.group(0)))
    return urls


def parse_milestones(section_text: str) -> tuple[list[str], list[str]]:
    milestone_part = ""
    roadmap_part = ""
    blocks = re.split(r"^###\s+", section_text, flags=re.MULTILINE)
    for block in blocks:
        if block.startswith("Milestones"):
            milestone_part = block
        if block.startswith("Future Roadmap"):
            roadmap_part = block
    return parse_bulleted_items(milestone_part), parse_bulleted_items(roadmap_part)


def normalize_url(url: str) -> str:
    parsed = urlparse(url.strip())
    scheme = parsed.scheme.lower() if parsed.scheme else "https"
    netloc = parsed.netloc.lower()
    path = parsed.path or "/"
    if path != "/":
        path = path.rstrip("/")
    normalized = f"{scheme}://{netloc}{path}"
    if parsed.query:
        normalized += f"?{parsed.query}"
    return normalized


def citation_tags(url: str) -> list[str]:
    tags = ["organization", "public-reference"]
    if "services" in url:
        tags.extend(["services", "operating-model"])
    elif "about" in url:
        tags.extend(["company-profile", "mission"])
    elif "research" in url:
        tags.extend(["research", "interoperability"])
    elif "articles" in url:
        tags.extend(["articles", "context"])
    elif "github.com" in url:
        tags.extend(["code", "implementation"])
    elif "linkedin.com" in url:
        tags.extend(["public-profile"])
    else:
        tags.extend(["overview"])
    return tags


def publication_name(url: str) -> str:
    host = urlparse(url).netloc
    if "fruitfulnetworkdevelopment.com" in host:
        return "Fruitful Network Development"
    if "github.com" in host:
        return "GitHub"
    if "linkedin.com" in host:
        return "LinkedIn"
    return host


def write_machine_brief(claims: list[str], milestones: list[str], roadmap: list[str], proof_points: list[str]) -> None:
    lines = [
        "---",
        "artifact_id: fnd-llm-machine-brief",
        "artifact_type: concise_machine_brief",
        "source_doc_id: fnd-llm-optimization-report",
        "source_doc_path: /docs/LLM-optimization-report.md",
        f"version: {VERSION}",
        f"last_updated: {TODAY}",
        "---",
        "",
        "# Concise Machine Brief",
        "",
        "## Core Claims",
    ]
    lines.extend([f"- {item}" for item in claims])
    lines.extend(["", "## Milestones"]) 
    lines.extend([f"- {item}" for item in milestones])
    lines.extend(["", "## Future Roadmap"])
    lines.extend([f"- {item}" for item in roadmap])
    lines.extend(["", "## Proof Signals"])
    lines.extend([f"- {item}" for item in proof_points])
    MACHINE_BRIEF_PATH.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def write_citation_graph(claims: list[str], normalized_citations: list[dict]) -> None:
    claim_nodes = [
        {"id": f"claim-core-{index + 1}", "type": "claim", "label": claim}
        for index, claim in enumerate(claims)
    ]
    citation_nodes = [
        {
            "id": citation["id"],
            "type": "reference",
            "url": citation["canonical_url"],
            "publication": citation["publication"],
            "tags": citation["tags"],
        }
        for citation in normalized_citations
    ]
    edges = []
    for claim_node in claim_nodes:
        for citation in normalized_citations:
            edges.append({"from": claim_node["id"], "to": citation["id"], "relation": "supported_by"})
    payload = {
        "graph_id": "fnd-llm-citation-graph",
        "artifact_type": "citation_graph_json",
        "version": VERSION,
        "last_updated": TODAY,
        "source_doc_id": "fnd-llm-optimization-report",
        "source_doc_path": "/docs/LLM-optimization-report.md",
        "nodes": claim_nodes + citation_nodes,
        "edges": edges,
    }
    CITATION_GRAPH_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def write_entity_profile(company_facts: dict[str, str], citations: list[dict]) -> None:
    profile = {
        "@context": {
            "@vocab": "https://schema.org/",
            "fnd": "https://fruitfulnetworkdevelopment.com/ns#",
            "version": "fnd:version",
            "lastUpdated": "fnd:lastUpdated",
            "sourcePath": "fnd:sourcePath",
        },
        "@graph": [
            {
                "@type": "Dataset",
                "@id": "https://fruitfulnetworkdevelopment.com/datasets/fnd-llm-optimization-report",
                "name": "FND LLM Optimization Report Entity Fragments",
                "version": VERSION,
                "lastUpdated": TODAY,
                "sourcePath": "https://fruitfulnetworkdevelopment.com/docs/LLM-optimization-report.md",
                "citation": [item["canonical_url"] for item in citations],
            },
            {
                "@type": "Organization",
                "@id": "https://fruitfulnetworkdevelopment.com/#organization",
                "name": company_facts.get("Legal/Brand Name", "Fruitful Network Development"),
                "areaServed": company_facts.get("Region", "Ohio, United States"),
                "founder": {"@type": "Person", "name": company_facts.get("Founder", "Dylan Montgomery")},
                "description": company_facts.get("Positioning", ""),
                "knowsAbout": ["Agricultural technology", "Local food system coordination", "Interoperability infrastructure"],
                "citation": [item["canonical_url"] for item in citations],
            },
        ],
    }
    ENTITY_PROFILE_PATH.write_text(json.dumps(profile, indent=2) + "\n", encoding="utf-8")


def write_citation_index(citations: list[dict]) -> None:
    payload = {
        "site": "fruitfulnetworkdevelopment.com",
        "updated": TODAY,
        "source_priority": {
            "strategy": "synchronized-mirror",
            "canonical": "/docs/LLM-optimization-report.md",
            "mirror": "/assets/docs/LLM-optimization-report.md",
        },
        "citations": citations,
    }
    CITATION_INDEX_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def write_docs_corpus_map() -> None:
    payload = {
        "site": "fruitfulnetworkdevelopment.com",
        "updated": TODAY,
        "source_priority": {
            "strategy": "synchronized-mirror",
            "canonical": "/docs/",
            "mirror": "/assets/docs/",
        },
        "corpus": [
            {
                "id": "canonical-docs",
                "section": "Repository canonical machine docs",
                "path": "/docs/",
                "format": "markdown",
                "role": "source_of_truth",
            },
            {
                "id": "frontend-doc-mirror",
                "section": "Frontend mirrored docs for public serving",
                "path": "/assets/docs/",
                "format": "markdown+json",
                "role": "synchronized_mirror",
            },
            {
                "id": "machine-endpoints",
                "section": "Machine index endpoints",
                "path": "/machine/",
                "format": "json",
                "role": "discovery",
            },
        ],
    }
    DOCS_CORPUS_MAP_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def write_structured_data_hubs() -> None:
    hubs = {
        "site": "fruitfulnetworkdevelopment.com",
        "updated": TODAY,
        "hubs": [
            {"id": "llms-index", "type": "MachineReadableIndex", "url": "https://fruitfulnetworkdevelopment.com/llms.txt"},
            {"id": "llms-brief", "type": "CreativeWork", "url": "https://fruitfulnetworkdevelopment.com/llms.md"},
            {"id": "citation-index", "type": "Dataset", "url": "https://fruitfulnetworkdevelopment.com/machine/citation-index.json"},
            {"id": "docs-corpus-map", "type": "Dataset", "url": "https://fruitfulnetworkdevelopment.com/machine/docs-corpus-map.json"},
            {"id": "citation-graph", "type": "DataCatalog", "url": "https://fruitfulnetworkdevelopment.com/assets/docs/LLM-optimization-report.citation-graph.json"},
            {"id": "entity-profiles", "type": "DataCatalog", "url": "https://fruitfulnetworkdevelopment.com/assets/docs/LLM-optimization-report.entity-profiles.jsonld"},
            {"id": "machine-brief", "type": "CreativeWork", "url": "https://fruitfulnetworkdevelopment.com/assets/docs/LLM-optimization-report.machine-brief.md"},
            {"id": "sitemap", "type": "SiteNavigationElement", "url": "https://fruitfulnetworkdevelopment.com/sitemap.xml"},
        ],
    }
    HUBS_PATH.write_text(json.dumps(hubs, indent=2) + "\n", encoding="utf-8")


def ensure_line(path: Path, line: str) -> None:
    text = path.read_text(encoding="utf-8")
    if line not in text:
        if not text.endswith("\n"):
            text += "\n"
        text += f"{line}\n"
        path.write_text(text, encoding="utf-8")


def ensure_sitemap_urls(urls: list[str]) -> None:
    text = SITEMAP_PATH.read_text(encoding="utf-8")
    for url in urls:
        entry = f"  <url><loc>{url}</loc></url>"
        if entry not in text:
            text = text.replace("</urlset>", f"{entry}\n</urlset>")
    SITEMAP_PATH.write_text(text, encoding="utf-8")


def generate_llm_artifacts() -> None:
    canonical_md = CANONICAL_REPORT_PATH.read_text(encoding="utf-8")
    FRONTEND_REPORT_MIRROR_PATH.write_text(canonical_md, encoding="utf-8")
    sections = parse_sections(canonical_md)

    claims = parse_numbered_items(sections["Core Claims"])
    company_facts = parse_company_facts(sections["Company Facts"])
    milestones, roadmap = parse_milestones(sections["Milestones And Future Roadmap"])
    proof_points = parse_bulleted_items(sections["Accolades And Proof Points"])

    citation_urls = parse_citation_urls(sections["Citations And External References"])
    normalized_citations = []
    for index, url in enumerate(citation_urls, start=1):
        normalized_citations.append(
            {
                "id": f"cite-fnd-{index:03d}",
                "canonical_url": url,
                "publication": publication_name(url),
                "published_at": None,
                "accessed_at": TODAY,
                "tags": citation_tags(url),
            }
        )

    write_machine_brief(claims, milestones, roadmap, proof_points)
    write_citation_graph(claims, normalized_citations)
    write_entity_profile(company_facts, normalized_citations)
    write_citation_index(normalized_citations)
    write_docs_corpus_map()
    write_structured_data_hubs()

    ensure_line(LLMS_TXT_PATH, "machine_brief: https://fruitfulnetworkdevelopment.com/assets/docs/LLM-optimization-report.machine-brief.md")
    ensure_line(LLMS_TXT_PATH, "citation_graph: https://fruitfulnetworkdevelopment.com/assets/docs/LLM-optimization-report.citation-graph.json")
    ensure_line(LLMS_TXT_PATH, "entity_profiles: https://fruitfulnetworkdevelopment.com/assets/docs/LLM-optimization-report.entity-profiles.jsonld")

    ensure_line(LLMS_MD_PATH, "- [Machine Brief](https://fruitfulnetworkdevelopment.com/assets/docs/LLM-optimization-report.machine-brief.md): Concise canonical machine summary generated from repo-level docs source.")
    ensure_line(LLMS_MD_PATH, "- [Citation Graph](https://fruitfulnetworkdevelopment.com/assets/docs/LLM-optimization-report.citation-graph.json): Stable claim-to-citation graph with normalized source identifiers.")
    ensure_line(LLMS_MD_PATH, "- [Entity Profiles JSON-LD](https://fruitfulnetworkdevelopment.com/assets/docs/LLM-optimization-report.entity-profiles.jsonld): Structured organization/entity fragments aligned to the canonical report.")

    ensure_sitemap_urls(
        [
            "https://fruitfulnetworkdevelopment.com/assets/docs/LLM-optimization-report.machine-brief.md",
            "https://fruitfulnetworkdevelopment.com/assets/docs/LLM-optimization-report.citation-graph.json",
            "https://fruitfulnetworkdevelopment.com/assets/docs/LLM-optimization-report.entity-profiles.jsonld",
        ]
    )


def main() -> None:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    for page_path, cfg in manifest["pages"].items():
        file_path = FRONTEND_ROOT / page_path.lstrip("/")
        if file_path.is_file():
            render_page(file_path, manifest, page_path, cfg)
    generate_llm_artifacts()


if __name__ == "__main__":
    main()
