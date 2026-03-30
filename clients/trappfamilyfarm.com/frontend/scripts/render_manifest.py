#!/usr/bin/env python3
"""Render Trapp Family Farm static pages from the manifest."""

from __future__ import annotations

import html
import json
import re
from pathlib import Path


FRONTEND_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = FRONTEND_ROOT / "assets" / "docs" / "manifest.json"


def escape(value: object) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def rel_asset(path: str) -> str:
    return path.lstrip("/")


def external_link_attrs(href: str) -> str:
    return ' target="_blank" rel="noopener noreferrer"' if href.startswith("http") else ""


def render_inline_markdown(text: str) -> str:
    rendered = escape(text)
    rendered = re.sub(
        r"\[([^\]]+)\]\(([^)]+)\)",
        lambda match: (
            f'<a href="{escape(rel_asset(match.group(2)) if match.group(2).startswith("/") else match.group(2))}"'
            f'{external_link_attrs(match.group(2))}>{escape(match.group(1))}</a>'
        ),
        rendered,
    )
    rendered = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", rendered)
    rendered = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", rendered)
    return rendered


def render_paragraphs(paragraphs: list[str]) -> str:
    return "".join(f"<p>{render_inline_markdown(paragraph)}</p>" for paragraph in paragraphs)


def render_image(image: dict[str, str], extra_class: str = "") -> str:
    classes = "json-figure"
    if extra_class:
        classes += f" {extra_class}"
    return (
        f'<figure class="{classes}">'
        f'<img src="{escape(rel_asset(image["src"]))}" alt="{escape(image.get("alt", ""))}">'
        "</figure>"
    )


def render_images(images: list[dict[str, str]], extra_class: str = "") -> str:
    return "".join(render_image(image, extra_class=extra_class) for image in images)


def render_link_list(items: list[dict[str, str]]) -> str:
    if not items:
        return ""
    parts = ['<ul class="json-animal-toc">']
    for item in items:
        href = item.get("href")
        label = escape(item["label"])
        if href:
            resolved = rel_asset(href) if href.startswith("/") else href
            parts.append(
                f'<li><a href="{escape(resolved)}"{external_link_attrs(href)}>{label}</a></li>'
            )
        else:
            parts.append(f"<li><span>{label}</span></li>")
    parts.append("</ul>")
    return "".join(parts)


def render_subsections(items: list[dict[str, object]]) -> str:
    sections = []
    for item in items:
        sections.append(
            '<section class="json-subsection">'
            f'<h3 class="json-subheading">{escape(item["title"])}</h3>'
            f'{render_paragraphs(item.get("body", []))}'
            "</section>"
        )
    return "".join(sections)


def render_podcast(entry: dict[str, object]) -> str:
    meta_parts = [escape(value) for value in [entry.get("subtitle"), entry.get("date_label")] if value]
    meta = f'<p class="json-meta">{" · ".join(meta_parts)}</p>' if meta_parts else ""
    summary = (
        render_paragraphs([entry["summary"]]) if entry.get("summary") else ""
    )
    image = (
        '<div class="json-podcast-media">'
        f'<img src="{escape(rel_asset(entry["image"]["src"]))}" alt="{escape(entry["image"].get("alt", ""))}">'
        "</div>"
        if entry.get("image")
        else ""
    )
    link = (
        f'<p class="json-podcast-link"><a href="{escape(entry["href"])}"'
        f'{external_link_attrs(entry["href"])}>{escape(entry["link_label"])}</a></p>'
    )
    return (
        '<article class="json-podcast">'
        f"{image}"
        '<div class="json-podcast-body">'
        f'<h3>{escape(entry["title"])}</h3>'
        f"{meta}"
        f"{summary}"
        f"{link}"
        "</div>"
        "</article>"
    )


def markdown_to_html(markdown: str) -> str:
    lines = markdown.strip().splitlines()
    blocks: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i].rstrip()
        stripped = line.strip()

        if not stripped:
            i += 1
            continue

        if re.fullmatch(r"-{3,}", stripped):
            blocks.append("<hr>")
            i += 1
            continue

        if stripped.startswith("## "):
            blocks.append(f"<h2>{render_inline_markdown(stripped[3:])}</h2>")
            i += 1
            continue

        if stripped.startswith("### "):
            blocks.append(f"<h3>{render_inline_markdown(stripped[4:])}</h3>")
            i += 1
            continue

        if stripped.startswith("- "):
            items = []
            while i < len(lines) and lines[i].strip().startswith("- "):
                items.append(lines[i].strip()[2:].rstrip())
                i += 1
            blocks.append(
                "<ul>"
                + "".join(f"<li>{render_inline_markdown(item)}</li>" for item in items)
                + "</ul>"
            )
            continue

        paragraph_lines = [stripped]
        i += 1
        while i < len(lines):
            candidate = lines[i].strip()
            if not candidate:
                break
            if candidate.startswith(("## ", "### ", "- ")) or re.fullmatch(r"-{3,}", candidate):
                break
            paragraph_lines.append(candidate)
            i += 1
        blocks.append(f"<p>{render_inline_markdown(' '.join(paragraph_lines))}</p>")

    return "".join(blocks)


def section_wrapper(title: str, inner: str, section_id: str) -> str:
    return (
        f'<section class="page-section json-page-section" id="{escape(section_id)}">'
        '<div class="container json-container">'
        f'<h2 class="json-section-title">{escape(title)}</h2>'
        f"{inner}"
        "</div>"
        "</section>"
    )


def render_home(page: dict[str, object]) -> str:
    sections = page["sections"]
    about = sections["about_our_farm"]
    journey = sections["our_journey"]
    horses = sections["draft_horses"]

    journey_items = "".join(f"<li>{escape(item)}</li>" for item in journey["items"])
    return (
        '<section class="page-section json-home-page">'
        '<div class="container json-container">'
        f'<p class="json-home-kicker">{escape(about["kicker"])}</p>'
        f'<h1 class="json-home-title">{escape(about["heading"])}</h1>'
        '<div class="json-home-grid">'
        '<div class="json-home-col json-home-story">'
        f'{render_paragraphs(about["body"])}'
        f'{render_images(about["images"])}'
        "</div>"
        '<aside class="json-home-col json-home-aside">'
        '<div class="json-panel json-panel-journey">'
        f'<h2>{escape(journey["heading"])}</h2>'
        f"<ul>{journey_items}</ul>"
        f'{render_images(journey["images"], extra_class="json-journey-img")}'
        "</div>"
        f'<div class="json-panel json-panel-horses" id="{escape(horses["id"])}">'
        f'<h2>{escape(horses["heading"])}</h2>'
        f'<p class="json-pullquote">{escape(horses["subheading"])}</p>'
        f'{render_paragraphs(horses["body"])}'
        f'{render_images(horses["images"])}'
        "</div>"
        "</aside>"
        "</div>"
        "</div>"
        "</section>"
    )


def render_split_section(section: dict[str, object]) -> str:
    prose_parts = []
    if section.get("quote"):
        prose_parts.append(f'<p class="json-pullquote">{escape(section["quote"])}</p>')
    if section.get("body"):
        prose_parts.append(render_paragraphs(section["body"]))
    if section.get("links"):
        prose_parts.append(render_link_list(section["links"]))
    if section.get("topics"):
        prose_parts.append(render_link_list(section["topics"]))

    prose = '<div class="json-prose">' + "".join(prose_parts) + "</div>"
    images = render_images(section.get("images", []), extra_class=section.get("image_class", ""))
    split_classes = ["json-split"]
    if section.get("reverse"):
        split_classes.append("json-split-reverse")
    if section.get("content_first"):
        inner = prose + images
    else:
        inner = images + prose
    return section_wrapper(section["heading"], f'<div class="{" ".join(split_classes)}">{inner}</div>', section["id"])


def render_subsection_page_section(section: dict[str, object]) -> str:
    inner = render_images(section.get("images", [])) + render_subsections(section.get("items", []))
    return section_wrapper(section["heading"], inner, section["id"])


def render_animals(page: dict[str, object]) -> str:
    sections = page["sections"]
    order = page["section_order"]
    output = []
    for key in order:
        section = sections[key]
        if key == "intro":
            intro_inner = (
                '<div class="json-prose json-intro-prose">'
                f'<p class="json-pullquote">{escape(section["quote"])}</p>'
                f'{render_paragraphs(section["body"])}'
                f'{render_link_list(section["links"])}'
                "</div>"
                f'{render_images(section["images"], extra_class="json-intro-images")}'
            )
            output.append(section_wrapper(section["heading"], intro_inner, section["id"]))
            continue
        output.append(render_split_section(section))
    return "".join(output)


def render_info(page: dict[str, object]) -> str:
    sections = page["sections"]
    podcasts = sections["podcasts"]
    intro = sections["intro"]
    output = [
        '<section class="page-section json-page-section" id="podcasts">'
        '<div class="container json-container">'
        '<div class="json-prose json-more-intro">'
        f'{render_paragraphs(intro["body"])}'
        "</div>"
        f'<h2 class="json-section-title">{escape(podcasts["heading"])}</h2>'
        '<div class="json-podcast-list">'
        + "".join(render_podcast(item) for item in podcasts["items"])
        + "</div>"
        "</div>"
        "</section>"
    ]
    if sections.get("news", {}).get("body"):
        output.append(section_wrapper("News", render_paragraphs(sections["news"]["body"]), "news"))
    return "".join(output)


def render_newsletter(page: dict[str, object]) -> str:
    sections = []
    for issue in page["issues"]:
        issue_body = (
            f'{render_images([issue["cover_image"]], extra_class="json-newsletter-cover")}'
            f'<p class="issue-meta">{escape(issue["published_label"])}</p>'
            '<div class="json-newsletter-md json-newsletter-md--marked">'
            f'{markdown_to_html(issue["content_markdown"])}'
            "</div>"
        )
        sections.append(section_wrapper(issue["title"], issue_body, issue["id"]))
    return "".join(sections)


def render_page_main(page_key: str, page: dict[str, object]) -> str:
    if page["template"] == "coming_soon":
        return (
            '<section class="page-section json-index-soon">'
            '<div class="container json-container">'
            f'<h1 class="json-coming-soon-heading">{escape(page["content"]["heading"])}</h1>'
            "</div>"
            "</section>"
        )
    if page["template"] == "home":
        return render_home(page)
    if page["template"] == "standard_sections":
        return "".join(
            render_subsection_page_section(page["sections"][key])
            if page["sections"][key]["layout"] == "subsections"
            else render_split_section(page["sections"][key])
            for key in page["section_order"]
        )
    if page["template"] == "animals":
        return render_animals(page)
    if page["template"] == "info":
        return render_info(page)
    if page["template"] == "newsletter":
        return render_newsletter(page)
    raise ValueError(f"Unsupported page template for {page_key}: {page['template']}")


def render_navigation(manifest: dict[str, object], current_file: str) -> str:
    items = []
    for item in manifest["navigation"]:
        active = ' class="active"' if item["href"] == current_file else ""
        items.append(
            "<li>"
            f'<a href="{escape(item["href"])}"{active}>{escape(item["label"])}</a>'
            "</li>"
        )
    return "".join(items)


def render_header(manifest: dict[str, object], page: dict[str, object], current_file: str) -> str:
    nav_html = render_navigation(manifest, current_file)
    header_graphic = ""
    if page.get("show_header_graphic"):
        header_graphic = (
            '<div class="header-graphic" aria-hidden="true">'
            f'<img src="{escape(rel_asset(manifest["site"]["header_graphic"]))}" alt="">'
            "</div>"
        )

    main_nav = ""
    if page.get("show_main_nav", True):
        main_nav = (
            '<nav class="main-nav" aria-label="Primary">'
            f'<ul class="nav-with-icons" id="nav-root">{nav_html}</ul>'
            "</nav>"
        )

    drawer = (
        '<div class="nav-overlay" id="nav-overlay" aria-hidden="true"></div>'
        '<aside class="nav-drawer" id="site-nav-drawer" role="dialog" aria-modal="true" '
        'aria-labelledby="site-nav-drawer-title" aria-hidden="true">'
        '<div class="nav-drawer-top">'
        '<p class="nav-drawer-title" id="site-nav-drawer-title">Menu</p>'
        '<button type="button" class="nav-drawer-close" aria-label="Close menu"><span aria-hidden="true">×</span></button>'
        "</div>"
        '<nav class="nav-drawer-nav" aria-label="Site pages">'
        f'<ul class="nav-with-icons nav-drawer-list" id="nav-drawer-root">{nav_html}</ul>'
        "</nav>"
        "</aside>"
    )

    return (
        '<header class="site-header">'
        '<div class="header-inner">'
        '<button type="button" class="nav-toggle" aria-label="Open menu" '
        'aria-expanded="false" aria-controls="site-nav-drawer">'
        '<span class="nav-toggle-bars" aria-hidden="true"><span></span><span></span><span></span></span>'
        "</button>"
        f"{header_graphic}"
        '<a href="home.html" class="logo">'
        '<span class="logo-text"><span>TRAPP</span><span>FAMILY</span><span>FARM</span></span>'
        "</a>"
        f"{main_nav}"
        "</div>"
        "</header>"
        f"{drawer}"
    )


def render_footer(manifest: dict[str, object]) -> str:
    footer = manifest["footer"]
    visit = footer["visit"]
    stand = footer["farm_stand"]
    social = footer["social_links"][0]
    return (
        '<footer class="site-footer" id="footer-root">'
        '<div class="footer-inner">'
        '<div class="footer-illustration">'
        f'<img src="{escape(rel_asset(manifest["site"]["footer_graphic"]))}" alt="">'
        "</div>"
        '<div class="footer-col footer-details">'
        f'<h3>{escape(visit["heading"])}</h3>'
        "<p>"
        f'{escape(visit["address_lines"][0])}<br>{escape(visit["address_lines"][1])}<br>'
        f'<a href="tel:+1{escape(visit["phone_digits"])}">{escape(visit["phone"])}</a><br>'
        f'<a href="mailto:{escape(visit["email"])}">{escape(visit["email"])}</a>'
        "</p>"
        "</div>"
        '<div class="footer-col footer-hours">'
        f'<h3>{escape(stand["heading"])}</h3>'
        f'<p>{escape(stand["days"])}<br>{escape(stand["hours"])}<br>{escape(stand["note"])}</p>'
        "</div>"
        '<div class="footer-col footer-follow">'
        "<h3>Follow along</h3>"
        f'<p><a class="instagram-link" href="{escape(social["href"])}"{external_link_attrs(social["href"])} '
        f'aria-label="{escape(social["label"])}"><img src="{escape(rel_asset(social["icon"]))}" alt=""></a></p>'
        "</div>"
        "</div>"
        f'<div class="footer-bottom"><p>{escape(footer["copyright"])}</p></div>'
        "</footer>"
    )


def render_css_vars(manifest: dict[str, object]) -> str:
    rules = [f"--hero-bg-image: url('{rel_asset(manifest['site']['hero_background'])}')"]
    for prefix, items in [
        ("nav", manifest["icons"]["navigation"]),
        ("footer", manifest["icons"]["footer"]),
        ("section", manifest["icons"]["sections"]),
    ]:
        for key, path in items.items():
            rules.append(f"--icon-{prefix}-{key}: url('{rel_asset(path)}')")
    return "; ".join(rules)


def render_document(manifest: dict[str, object], page_key: str, page: dict[str, object]) -> str:
    body_classes = [page.get("body_class", "")]
    body_classes = " ".join(cls for cls in body_classes if cls)
    current_file = page["file"]
    body_class_attr = f' class="{escape(body_classes)}"' if body_classes else ""
    return "\n".join(
        [
            "<!DOCTYPE html>",
            "<html lang=\"en\">",
            "<head>",
            "  <meta charset=\"UTF-8\">",
            "  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">",
            f"  <title>{escape(page['title'])}</title>",
            f"  <meta name=\"description\" content=\"{escape(page['description'])}\">",
            f'  <link rel="icon" type="image/svg+xml" href="{escape(rel_asset(manifest["site"]["favicon"]))}">',
            '  <link rel="stylesheet" href="css/style.css">',
            "</head>",
            f'<body data-page="{escape(page_key)}"{body_class_attr} style="{escape(render_css_vars(manifest))}">',
            f"  <!-- Generated from assets/docs/manifest.json by scripts/render_manifest.py -->",
            f"  {render_header(manifest, page, current_file)}",
            f'  <main class="main" id="main-root">{render_page_main(page_key, page)}</main>',
            f"  {render_footer(manifest)}",
            '  <script src="js/site-shell.js"></script>',
            '  <script src="js/gallery-home-button.js"></script>',
            "</body>",
            "</html>",
        ]
    ) + "\n"


def build() -> None:
    manifest = json.loads(MANIFEST_PATH.read_text())
    for page_key, page in manifest["pages"].items():
        output_path = FRONTEND_ROOT / page["file"]
        output_path.write_text(render_document(manifest, page_key, page))
        print(f"rendered {output_path.relative_to(FRONTEND_ROOT)}")


if __name__ == "__main__":
    build()
