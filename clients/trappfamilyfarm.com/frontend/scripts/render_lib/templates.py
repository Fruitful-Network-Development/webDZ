from __future__ import annotations

from pathlib import Path

from .content_loader import load_collection
from .html_utils import escape, render_images, render_link_list, render_paragraphs, render_subsections


def section_wrapper(title: str, inner: str, section_id: str) -> str:
    return (
        f'<section class="page-section json-page-section" id="{escape(section_id)}">'
        '<div class="container json-container">'
        f'<h2 class="json-section-title">{escape(title)}</h2>'
        f"{inner}"
        "</div>"
        "</section>"
    )


def render_page(page: dict[str, object], manifest: dict[str, object], frontend_root: Path) -> str:
    template = page["template"]
    renderer = PAGE_RENDERERS.get(template)
    if renderer is None:
        raise ValueError(f"Unsupported page template: {template}")
    return renderer(page, manifest, frontend_root)


def render_coming_soon(page: dict[str, object], _manifest: dict[str, object], _frontend_root: Path) -> str:
    return (
        '<section class="page-section json-index-soon">'
        '<div class="container json-container">'
        f'<h1 class="json-coming-soon-heading">{escape(page["content"]["heading"])}</h1>'
        "</div>"
        "</section>"
    )


def render_home_featured(page: dict[str, object], _manifest: dict[str, object], _frontend_root: Path) -> str:
    content = page["content"]
    lead = content["lead"]
    sidebar_cards = "".join(render_home_card(card) for card in content["sidebar_cards"])
    return (
        '<section class="page-section json-home-page">'
        '<div class="container json-container">'
        f'<p class="json-home-kicker">{escape(lead["kicker"])}</p>'
        f'<h1 class="json-home-title">{escape(lead["heading"])}</h1>'
        '<div class="json-home-grid">'
        '<div class="json-home-col json-home-story">'
        f'{render_paragraphs(lead["body"])}'
        f'{render_images(lead["images"])}'
        "</div>"
        f'<aside class="json-home-col json-home-aside">{sidebar_cards}</aside>'
        "</div>"
        "</div>"
        "</section>"
    )


def render_home_card(card: dict[str, object]) -> str:
    template = card["template"]
    if template == "list_card":
        items = "".join(f"<li>{escape(item)}</li>" for item in card["items"])
        return (
            f'<div class="{escape(card["class_name"])}">'
            f'<h2>{escape(card["heading"])}</h2>'
            f"<ul>{items}</ul>"
            f'{render_images(card.get("images", []), extra_class=card.get("image_class", ""))}'
            "</div>"
        )
    if template == "quote_card":
        id_attr = f' id="{escape(card["id"])}"' if card.get("id") else ""
        return (
            f'<div class="{escape(card["class_name"])}"{id_attr}>'
            f'<h2>{escape(card["heading"])}</h2>'
            f'<p class="json-pullquote">{escape(card["quote"])}</p>'
            f'{render_paragraphs(card["body"])}'
            f'{render_images(card.get("images", []))}'
            "</div>"
        )
    raise ValueError(f"Unsupported home card template: {template}")


def render_section_stack(page: dict[str, object], manifest: dict[str, object], frontend_root: Path) -> str:
    return "".join(
        render_section(section, manifest, frontend_root)
        for section in page["sections"]
    )


def render_section(section: dict[str, object], manifest: dict[str, object], frontend_root: Path) -> str:
    template = section["template"]
    renderer = SECTION_RENDERERS.get(template)
    if renderer is None:
        raise ValueError(f"Unsupported section template: {template}")
    return renderer(section, manifest, frontend_root)


def render_split_section(section: dict[str, object], _manifest: dict[str, object], _frontend_root: Path) -> str:
    prose_parts = []
    if section.get("quote"):
        prose_parts.append(f'<p class="json-pullquote">{escape(section["quote"])}</p>')
    if section.get("body"):
        prose_parts.append(render_paragraphs(section["body"]))
    if section.get("links"):
        prose_parts.append(render_link_list(section["links"]))

    prose = '<div class="json-prose">' + "".join(prose_parts) + "</div>"
    images = render_images(section.get("images", []), extra_class=section.get("image_class", ""))
    classes = ["json-split"]
    if section.get("reverse"):
        classes.append("json-split-reverse")
    if section.get("content_first"):
        inner = prose + images
    else:
        inner = images + prose
    return section_wrapper(section["heading"], f'<div class="{" ".join(classes)}">{inner}</div>', section["id"])


def render_toc_section(section: dict[str, object], _manifest: dict[str, object], _frontend_root: Path) -> str:
    prose = (
        '<div class="json-prose json-intro-prose">'
        + (f'<p class="json-pullquote">{escape(section["quote"])}</p>' if section.get("quote") else "")
        + render_paragraphs(section.get("body", []))
        + render_link_list(section.get("links", []))
        + "</div>"
    )

    if section.get("layout") == "split":
        inner = (
            '<div class="json-split">'
            f'{render_images(section.get("images", []), extra_class=section.get("image_class", ""))}'
            f"{prose}"
            "</div>"
        )
    else:
        inner = prose + render_images(section.get("images", []), extra_class=section.get("image_class", "json-intro-images"))

    return section_wrapper(section["heading"], inner, section["id"])


def render_subsection_collection(section: dict[str, object], _manifest: dict[str, object], _frontend_root: Path) -> str:
    inner = render_images(section.get("images", [])) + render_subsections(section.get("items", []))
    return section_wrapper(section["heading"], inner, section["id"])


def render_rich_cards(section: dict[str, object], _manifest: dict[str, object], _frontend_root: Path) -> str:
    cards = "".join(render_rich_card(card) for card in section["cards"])
    return (
        f'<section class="page-section json-page-section" id="{escape(section["id"])}">'
        '<div class="container json-container">'
        '<div class="json-prose json-more-intro">'
        f'{render_paragraphs(section.get("intro_body", []))}'
        "</div>"
        f'<h2 class="json-section-title">{escape(section["heading"])}</h2>'
        f'<div class="{escape(section.get("cards_class", "json-podcast-list"))}">{cards}</div>'
        "</div>"
        "</section>"
    )


def render_rich_card(card: dict[str, object]) -> str:
    meta_parts = [escape(value) for value in [card.get("subtitle"), card.get("date_label")] if value]
    meta = f'<p class="json-meta">{" · ".join(meta_parts)}</p>' if meta_parts else ""
    summary = render_paragraphs([card["summary"]]) if card.get("summary") else ""
    image = (
        '<div class="json-podcast-media">'
        f'<img src="{escape(card["image"]["src"].lstrip("/"))}" alt="{escape(card["image"].get("alt", ""))}">'
        "</div>"
        if card.get("image")
        else ""
    )
    link = (
        f'<p class="json-podcast-link"><a href="{escape(card["href"])}"'
        f' target="_blank" rel="noopener noreferrer">{escape(card["link_label"])}</a></p>'
        if card.get("href")
        else ""
    )
    return (
        f'<article class="{escape(card.get("class_name", "json-podcast"))}">'
        f"{image}"
        '<div class="json-podcast-body">'
        f'<h3>{escape(card["title"])}</h3>'
        f"{meta}"
        f"{summary}"
        f"{link}"
        "</div>"
        "</article>"
    )


def render_article_archive(page: dict[str, object], manifest: dict[str, object], frontend_root: Path) -> str:
    documents = load_collection(manifest, frontend_root, page["content"]["collection"])
    entry_template = page["content"].get("entry_template", "full_markdown_entry")
    return "".join(render_archive_entry(document, entry_template) for document in documents)


def render_archive_entry(document: dict[str, object], entry_template: str) -> str:
    if entry_template != "full_markdown_entry":
        raise ValueError(f"Unsupported archive entry template: {entry_template}")

    issue_body = (
        f'{render_images([{"src": document["cover_image"], "alt": document.get("cover_alt", "")}], extra_class="json-newsletter-cover")}'
        f'<p class="issue-meta">{escape(document["published_label"])}</p>'
        '<div class="json-newsletter-md json-newsletter-md--marked">'
        f'{document["body_html"]}'
        "</div>"
    )
    return section_wrapper(document["title"], issue_body, document["slug"])


PAGE_RENDERERS = {
    "coming_soon": render_coming_soon,
    "home_featured": render_home_featured,
    "section_stack": render_section_stack,
    "article_archive": render_article_archive,
}


SECTION_RENDERERS = {
    "split_section": render_split_section,
    "toc_section": render_toc_section,
    "subsection_collection": render_subsection_collection,
    "rich_cards": render_rich_cards,
}
