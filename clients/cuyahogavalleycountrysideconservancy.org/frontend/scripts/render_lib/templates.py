from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path
import re

from .content_loader import load_collection, load_fragment
from .html_utils import escape, external_link_attrs, rel_asset, render_figure, render_inline_markdown, render_paragraphs, slugify


HISTORY_LEGACY_ASSET_PATHS = {
    "assets/icons/farm.svg": "assets/icon/icon-domain-local.svg",
    "assets/image/countryside/img-cvcc-aerialfarm.avif": "assets/image/aerial_farm.avif",
    "assets/image/countryside/img-cvcc-foodterminal.avif": "assets/image/historic/food_terminal.avif",
    "assets/image/countryside/img-cvcc-historicbridge.avif": "assets/image/historic/bridge.avif",
    "assets/image/countryside/img-cvcc-historicgreenhouse.avif": "assets/image/historic/greenhouse.avif",
    "assets/image/countryside/img-cvcc-pictorialmap.avif": "assets/image/pictorial_map.avif",
    "assets/image/countryside/img-cvcc-vineyard.avif": "assets/image/vineyard.avif",
    "assets/image/countryside/img-cvcc-widefarm.avif": "assets/image/long_farm_pano.avif",
    "assets/image/countryside/img-oxbow-orchard-scene.avif": "assets/image/farms/OBO/oxbow_orchard.avif",
    "assets/image/countryside/img-purple_brown-scene.avif": "assets/image/farms/PBFS/purple_brown_farm_stead.avif",
    "assets/image/greenfield_berry_farm/img-greenfield_berry-scene.avif": "assets/image/farms/GBF/img-greenfield_berry-scene.avif",
    "assets/image/keleman_point_farm/img-keleman_point-scene.avif": "assets/image/farms/KPF/img-keleman_point-scene.avif",
    "assets/image/spiceacres/img-spice_acres-scene.avif": "assets/image/farms/SA/img-spice_acres-scene.avif",
    "assets/image/spicey_lamb_farm/img-spicy_lamb-scene.avif": "assets/image/farms/SLF/img-spicy_lamb-scene.avif",
    "assets/image/stock/img-stock-farm_pano.avif": "assets/image/farms/SLF/img-stock-aerial_farm.avif",
}

HAPPENING_TYPE_META = {
    "special_day": {"label": "Special day", "color": "#6d5a3b"},
    "span": {"label": "Date span", "color": "#4d6a54"},
    "recurring": {"label": "Recurring", "color": "#2f6168"},
    "ongoing": {"label": "Ongoing", "color": "#708087"},
}


def render_page(page: dict[str, object], manifest: dict[str, object], frontend_root: Path) -> str:
    renderer = PAGE_RENDERERS.get(page["template"])
    if renderer is None:
        raise ValueError(f"Unsupported page template: {page['template']}")
    return renderer(page, manifest, frontend_root)


def render_archive_home(page: dict[str, object], manifest: dict[str, object], frontend_root: Path) -> str:
    content = page["content"]
    posts = prepare_posts(load_collection(manifest, frontend_root, content["newsletter_collection"]), manifest, frontend_root)
    happenings = load_collection(manifest, frontend_root, content["happenings_collection"])
    latest_post = select_featured_post(posts)
    upcoming = upcoming_happenings(happenings, limit=5)

    intro_panels = "".join(
        (
            f'<section class="home-hero__panel" aria-labelledby="{escape(panel["id"])}">'
            f'<p class="home-intro-note">{panel["note_html"]}</p>'
            f'<h2 id="{escape(panel["id"])}">{escape(panel["heading"])}</h2>'
            f'{render_paragraphs(panel["body"])}'
            "</section>"
        )
        for panel in content["intro_panels"]
    )
    mission_blocks = "".join(
        (
            '<section class="home-hero__mission-block">'
            f'<h3>{escape(block["heading"])}</h3>'
            f'{render_paragraphs(block["body"])}'
            "</section>"
        )
        for block in content["mission_blocks"]
    )
    donate_callout = (
        '<section class="home-donate-callout" aria-label="Donation link">'
        f'<p class="home-donate-callout__eyebrow">{escape(content["donate_callout"]["eyebrow"])}</p>'
        f'<p class="home-donate-callout__body">{escape(content["donate_callout"]["body"])}</p>'
        f'<a class="button" href="{escape(content["donate_callout"]["href"])}">{escape(content["donate_callout"]["link_label"])}</a>'
        "</section>"
    )

    return (
        '<section class="section section--hero hero-bleed">'
        f'{render_figure(content["hero_image"], class_name="figure figure--mounted figure--pano")}'
        '<div class="home-hero__copy">'
        f'<p class="kicker kicker--hero">{escape(content["kicker"])}</p>'
        f'<h1 class="headline-lg headline-lg--hero">{escape(content["headline"])}</h1>'
        '<div class="home-hero__stack">'
        f"{intro_panels}"
        f'<div class="home-hero__mission" aria-label="Mission and objective">{mission_blocks}</div>'
        f"{donate_callout}"
        "</div>"
        "</div>"
        "</section>"
        '<section class="home-news-feature" aria-labelledby="home-news-feature-heading">'
        '<article class="home-news-feature__article">'
        f'<p class="home-news-feature__eyebrow">{escape(content["newsletter_feature"]["eyebrow"])}</p>'
        f'<h2 id="home-news-feature-heading" class="section-heading" style="margin:0 0 0.45rem;">{escape(content["newsletter_feature"]["heading"])}</h2>'
        f"{render_home_latest_post(latest_post)}"
        "</article>"
        '<aside class="home-news-feature__signup">'
        f'<p class="home-news-feature__eyebrow">{escape(content["signup"]["eyebrow"])}</p>'
        f'<h3>{escape(content["signup"]["heading"])}</h3>'
        f'<p class="timeline-intro" style="margin:0;">{content["signup"]["intro_html"]}</p>'
        f'{render_signup_form(content["signup"]["form"], "home-newsletter-ack", "home-news-feature__ack")}'
        "</aside>"
        "</section>"
        '<section class="home-events-strip" aria-labelledby="home-events-strip-heading">'
        '<div class="home-events-strip__head">'
        f'<h2 id="home-events-strip-heading">{escape(content["events"]["heading"])}</h2>'
        f'<a href="{escape(content["events"]["href"])}">{escape(content["events"]["link_label"])}</a>'
        "</div>"
        f'<div class="home-events-strip__grid">{render_home_event_cards(upcoming)}</div>'
        "</section>"
    )


def render_board_directory(page: dict[str, object], manifest: dict[str, object], frontend_root: Path) -> str:
    profiles = load_collection(manifest, frontend_root, page["content"]["collection"])
    ordered = sort_board_profiles(profiles)
    chair = next((profile for profile in ordered if has_tag(profile, "board_chair")), None)
    others = [profile for profile in ordered if profile is not chair]
    content = page["content"]

    featured = (
        f'<section class="board-featured"><h2 class="section-heading">{escape(content["featured_heading"])}</h2>{render_board_card(chair, featured=True)}</section>'
        if chair
        else ""
    )
    grid_cards = "".join(render_board_card(profile) for profile in (others or ordered))

    return (
        '<header class="home-lead board-lead">'
        f'<p class="home-lead__eyebrow">{escape(content["eyebrow"])}</p>'
        f'<h1 class="headline-site">{escape(content["heading"])}</h1>'
        f'<p class="home-lead__deck">{escape(content["deck"])}</p>'
        "</header>"
        f"{featured}"
        '<section class="board-grid">'
        f'<h2 class="section-heading">{escape(content["grid_heading"])}</h2>'
        f'<div class="board-grid__cards">{grid_cards}</div>'
        "</section>"
        f'<p class="timeline-intro board-closing-note">{content["closing_html"]}</p>'
    )


def render_article_archive(page: dict[str, object], manifest: dict[str, object], frontend_root: Path) -> str:
    posts = prepare_posts(load_collection(manifest, frontend_root, page["content"]["collection"]), manifest, frontend_root)
    featured = select_featured_post(posts)
    content = page["content"]
    archive_posts = [post for post in posts if featured and post["slug"] != featured["slug"]]
    page_size = max(int(content.get("page_size", 9)), 1)
    cards = "".join(
        render_post_card(post, page_number=(index // page_size) + 1, hidden=index >= page_size)
        for index, post in enumerate(archive_posts)
    )
    templates = "".join(render_post_template(post) for post in posts)
    pagination = render_newsletter_pagination(len(archive_posts), page_size, content)
    reset_link = (
        '<a class="newsletter-archive__reset" href="newsletter.html">Show newest newsletter</a>'
        if featured
        else ""
    )

    return (
        '<section class="section newsletter-archive"'
        f' data-newsletter-archive data-default-slug="{escape(featured["slug"] if featured else "")}">'
        f'<p class="home-lead__eyebrow" style="margin-bottom: var(--sp-3);">{escape(content["eyebrow"])}</p>'
        f'<h1 class="headline-site">{escape(content["heading"])}</h1>'
        f'<p class="timeline-intro">{escape(content["deck"])}</p>'
        '<div class="newsletter-archive__viewer-head">'
        f'<h2 id="newsletter-viewer-heading" class="section-heading">{escape(content["featured_heading"])}</h2>'
        f"{reset_link}"
        "</div>"
        f'<div id="newsletter-viewer">{render_post_entry(featured, class_name="blog-reader newsletter-viewer__article", include_anchor=False)}</div>'
        '<div class="newsletter-register">'
        '<div class="newsletter-register__head">'
        f'<h2 class="section-heading">{escape(content["archive_heading"])}</h2>'
        '<p class="timeline-intro">Browse older issues in reverse chronological order.</p>'
        "</div>"
        f'<div class="newsletter-register__grid" aria-label="Newsletter archive cards">{cards}</div>'
        f"{pagination}"
        "</div>"
        f'<div class="newsletter-archive__templates" hidden>{templates}</div>'
        "</section>"
        '<section class="section">'
        f'<h2 class="section-heading">{escape(content["signup"]["heading"])}</h2>'
        f'<p class="timeline-intro">{content["email_card"]["body_html"]}</p>'
        f'{render_signup_form(content["signup"]["form"], "newsletter-ack", "form-note")}'
        "</section>"
    )


def render_happenings_overview(page: dict[str, object], manifest: dict[str, object], frontend_root: Path) -> str:
    content = page["content"]
    data = load_collection(manifest, frontend_root, content["collection"])
    upcoming = upcoming_happenings(data, limit=10)
    schedule_entries = build_schedule_entries(data)
    grouped_schedule = group_schedule_by_month(schedule_entries)
    section_cards = render_happening_sections(data)
    window_label = happenings_window_label(schedule_entries)

    return (
        '<section class="section">'
        f'<p class="home-lead__eyebrow" style="margin-bottom: var(--sp-3);">{escape(content["eyebrow"])}</p>'
        f'<h1 class="headline-site">{escape(content["heading"])}</h1>'
        f'<p class="timeline-intro">{escape(content["deck"])}</p>'
        "</section>"
        '<section class="section happenings-annual" aria-labelledby="happenings-annual-heading">'
        '<div class="happenings-meta">'
        '<div>'
        f'<h2 id="happenings-annual-heading" class="section-heading" style="margin:0;">{escape(content["annual_heading"])}</h2>'
        f'<p>{content["annual_note_html"]}</p>'
        "</div>"
        f'<p id="happenings-window-label" class="home-lead__eyebrow" style="margin:0;">{escape(window_label)}</p>'
        "</div>"
        '<section aria-labelledby="happenings-upcoming-heading">'
        f'<h3 id="happenings-upcoming-heading" class="section-heading" style="margin:0;">{escape(content["upcoming_heading"])}</h3>'
        f'<p class="timeline-intro" style="margin:0.35rem 0 0;">{escape(content["upcoming_note"])}</p>'
        f'<div class="happenings-upcoming-grid">{render_happening_cards(upcoming)}</div>'
        "</section>"
        '<div class="happenings-main-layout">'
        '<div class="happenings-calendar-shell">'
        '<div class="happenings-controls" aria-label="Happenings views">'
        '<span class="happenings-control-chip">All</span>'
        '<span class="happenings-control-chip">Scheduled</span>'
        '<span class="happenings-control-chip">Recurring</span>'
        '<span class="happenings-control-chip">Ongoing</span>'
        "</div>"
        f'<div class="happenings-calendar-wrap happenings-calendar-wrap--static">{grouped_schedule}</div>'
        f'<div class="happenings-legend">{render_happening_legend()}</div>'
        "</div>"
        '<aside class="happenings-detail">'
        f'<h3>{escape(content["detail_heading"])}</h3>'
        f'<p class="happenings-detail__sub">{escape(content["detail_note"])}</p>'
        f"{section_cards}"
        "</aside>"
        "</div>"
        "</section>"
    )


def render_timeline_stack(page: dict[str, object], manifest: dict[str, object], frontend_root: Path) -> str:
    payload = load_collection(manifest, frontend_root, page["content"]["collection"])
    periods = sorted(payload["periods"], key=parts_key)
    events = sorted(payload["events"], key=parts_key)
    grouped = group_events_by_period(periods, events)
    content = page["content"]
    intro_html = "".join(f"<p>{paragraph}</p>" for paragraph in content["intro_html"])
    periods_html = "".join(render_history_period(entry["period"], entry["events"]) for entry in grouped)

    return (
        '<header class="history-intro">'
        f'<p class="history-kicker">{escape(content["eyebrow"])}</p>'
        f'<h1 class="headline-site">{escape(content["heading"])}</h1>'
        f"{intro_html}"
        "</header>"
        '<section class="history-summary" aria-labelledby="history-summary-heading">'
        f'<p id="history-summary-heading" class="history-summary__eyebrow">{escape(content["summary_eyebrow"])}</p>'
        f'<p id="history-summary-text" class="history-summary__counts">{escape(len(events))} events grouped into {escape(len(grouped))} period sections.</p>'
        f'<p class="history-summary__note">{content["summary_note_html"]}</p>'
        "</section>"
        '<section aria-labelledby="history-periods-heading">'
        f'<h2 id="history-periods-heading" class="history-kicker">{escape(content["periods_heading"])}</h2>'
        f'<div id="history-periods">{periods_html}</div>'
        "</section>"
    )


def render_static_fragment(page: dict[str, object], _manifest: dict[str, object], frontend_root: Path) -> str:
    return load_fragment(frontend_root, page["content"]["source"])


def render_home_latest_post(post: dict[str, object]) -> str:
    if not post:
        return '<p class="timeline-intro" style="margin:0;">Browse all seasonal writing in <a href="newsletter.html">Newsletter</a>.</p>'
    return render_featured_post_card(post, href=f'newsletter.html#{escape(post["slug"])}')


def render_signup_form(form: dict[str, object], ack_id: str, ack_class: str) -> str:
    fields = []
    for field in form["fields"]:
        attrs = [f'id="{escape(field["id"])}"', f'name="{escape(field["name"])}"', f'type="{escape(field["type"])}"']
        if field.get("autocomplete"):
            attrs.append(f'autocomplete="{escape(field["autocomplete"])}"')
        if field.get("placeholder"):
            attrs.append(f'placeholder="{escape(field["placeholder"])}"')
        if field.get("required"):
            attrs.append("required")
        wrapper_start = "<div>" if field.get("wrap", True) else ""
        wrapper_end = "</div>" if field.get("wrap", True) else ""
        fields.append(
            wrapper_start
            + f'<label for="{escape(field["id"])}">{field["label_html"]}</label>'
            + f'<input {" ".join(attrs)} />'
            + wrapper_end
        )

    grid_start = '<div class="form-grid">' if form.get("use_grid") else ""
    grid_end = "</div>" if form.get("use_grid") else ""
    return (
        f'<form class="{escape(form["class_name"])}" action="{escape(form["action"])}" method="{escape(form["method"])}" id="{escape(form["id"])}">'
        f"{grid_start}{''.join(fields)}{grid_end}"
        + "".join(f'<p class="{escape(note.get("class_name", "form-note"))}">{note["html"]}</p>' for note in form.get("notes", []))
        + f'<p id="{escape(ack_id)}" class="{escape(ack_class)}" hidden>{escape(form["ack_label"])}</p>'
        + f'<button class="{escape(form["button_class"])}" type="submit">{escape(form["button_label"])}</button>'
        "</form>"
    )


def select_featured_post(posts: list[dict[str, object]]) -> dict[str, object] | None:
    if not posts:
        return None
    featured = next((post for post in posts if post.get("feature") is True), None)
    return featured or posts[0]


def cover_image_for_post(post: dict[str, object]) -> dict[str, str]:
    source = post.get("resolved_cover_image") or post.get("cover_image") or "favicon.png"
    return {
        "src": source,
        "alt": post.get("resolved_cover_alt") or post.get("cover_alt") or post.get("title") or "Newsletter image",
    }


def render_post_card(post: dict[str, object], page_number: int = 1, hidden: bool = False) -> str:
    image = cover_image_for_post(post)
    media_class = "newsletter-card__media newsletter-card__media--fallback" if post.get("resolved_cover_is_fallback") else "newsletter-card__media"
    return (
        f'<article class="newsletter-card newsletter-card--compact" data-post-id="{escape(post["slug"])}" data-page="{escape(page_number)}"{" hidden" if hidden else ""}>'
        f'<a class="newsletter-card__link" href="#{escape(post["slug"])}">'
        f'{render_figure(image, class_name=media_class)}'
        '<div class="newsletter-card__content">'
        f'<p class="newsletter-card__meta">{escape(build_post_meta(post))}</p>'
        f'<h3 class="newsletter-card__title">{escape(post["title"])}</h3>'
        f'<p class="newsletter-card__excerpt">{escape(post.get("excerpt", ""))}</p>'
        '<div class="newsletter-card__footer">'
        '<span class="newsletter-card__cta">Read in the viewer</span>'
        "</div>"
        "</div>"
        "</a>"
        "</article>"
    )


def render_post_entry(post: dict[str, object], class_name: str = "blog-reader", include_anchor: bool = True) -> str:
    image = cover_image_for_post(post)
    anchor = f' id="{escape(post["slug"])}"' if include_anchor else ""
    meta = build_post_meta(post)
    figure_class = "figure figure--newsletter-fallback" if post.get("resolved_cover_is_fallback") else "figure"
    return (
        f'<article class="{escape(class_name)}"{anchor}>'
        f'<p class="home-news-feature__eyebrow">{escape(meta)}</p>'
        f'<h2>{escape(post["title"])}</h2>'
        f'{render_figure(image, class_name=figure_class)}'
        f'{post["body_html"]}'
        "</article>"
    )


def prepare_posts(posts: list[dict[str, object]], manifest: dict[str, object], frontend_root: Path) -> list[dict[str, object]]:
    ordered = sorted(posts, key=lambda post: str(post.get("published_sort", "")), reverse=True)
    default_image = str(manifest.get("site", {}).get("favicon", "favicon.png"))
    prepared = []
    for post in ordered:
        item = dict(post)
        item["resolved_cover_image"] = resolve_post_cover_image(item, frontend_root, default_image)
        item["resolved_cover_alt"] = item.get("cover_alt") or item.get("title") or "Newsletter image"
        item["resolved_cover_is_fallback"] = item["resolved_cover_image"] == rel_asset(default_image)
        prepared.append(item)
    return prepared


def resolve_post_cover_image(post: dict[str, object], frontend_root: Path, default_image: str) -> str:
    candidates: list[str] = []
    if post.get("cover_image"):
        candidates.append(str(post["cover_image"]))
    slug = str(post.get("slug", "")).strip()
    if slug:
        for stem in (f"assets/image/blog-images/{slug}", f"assets/image/blog-images/{slug}-1"):
            for extension in (".avif", ".png", ".jpg", ".jpeg", ".webp"):
                candidates.append(f"{stem}{extension}")
    for candidate in candidates:
        if (frontend_root / rel_asset(candidate)).exists():
            return rel_asset(candidate)
    return rel_asset(default_image)


def build_post_meta(post: dict[str, object]) -> str:
    return " · ".join(part for part in [str(post.get("published_label", "")), str(post.get("author", ""))] if part)


def render_featured_post_card(post: dict[str, object], href: str) -> str:
    image = cover_image_for_post(post)
    media_class = "newsletter-card__media newsletter-card__media--feature newsletter-card__media--fallback" if post.get("resolved_cover_is_fallback") else "newsletter-card__media newsletter-card__media--feature"
    return (
        '<article class="newsletter-card newsletter-card--feature">'
        f'<a class="newsletter-card__link" href="{escape(href)}">'
        f'{render_figure(image, class_name=media_class)}'
        '<div class="newsletter-card__content">'
        f'<p class="newsletter-card__meta">{escape(build_post_meta(post))}</p>'
        f'<h3 class="newsletter-card__title">{escape(post["title"])}</h3>'
        f'<p class="newsletter-card__excerpt">{escape(post.get("excerpt", ""))}</p>'
        '<div class="newsletter-card__footer">'
        '<span class="newsletter-card__cta">Read the full newsletter</span>'
        "</div>"
        "</div>"
        "</a>"
        "</article>"
    )


def render_post_template(post: dict[str, object]) -> str:
    return (
        f'<template data-newsletter-template="{escape(post["slug"])}">'
        f'{render_post_entry(post, class_name="blog-reader newsletter-viewer__article", include_anchor=False)}'
        "</template>"
    )


def render_newsletter_pagination(total_posts: int, page_size: int, content: dict[str, object]) -> str:
    if total_posts <= page_size:
        return ""
    page_count = (total_posts + page_size - 1) // page_size
    buttons = "".join(
        (
            f'<button class="newsletter-pagination__button{" is-active" if page_number == 1 else ""}"'
            f' type="button" data-newsletter-page="{page_number}"'
            f'{" aria-current=\"page\"" if page_number == 1 else ""}>'
            f"{page_number}"
            "</button>"
        )
        for page_number in range(1, page_count + 1)
    )
    return (
        f'<nav class="newsletter-pagination" aria-label="{escape(content.get("pagination_aria_label", "Newsletter archive pages"))}">'
        f'<button class="newsletter-pagination__button newsletter-pagination__button--direction" type="button" data-newsletter-prev>{escape(content.get("pagination_previous_label", "Previous"))}</button>'
        f'<div class="newsletter-pagination__pages">{buttons}</div>'
        f'<button class="newsletter-pagination__button newsletter-pagination__button--direction" type="button" data-newsletter-next>{escape(content.get("pagination_next_label", "Next"))}</button>'
        "</nav>"
    )


def sort_board_profiles(profiles: list[dict[str, object]]) -> list[dict[str, object]]:
    return sorted(
        profiles,
        key=lambda profile: (0 if has_tag(profile, "board_chair") else 1, str(profile.get("name", "")).lower()),
    )


def has_tag(profile: dict[str, object], tag: str) -> bool:
    return tag.lower() in {str(item).lower() for item in profile.get("tags", [])}


def social_pairs(profile: dict[str, object]) -> list[tuple[str, str]]:
    items: list[tuple[str, str]] = []
    for row in profile.get("socials", []):
        if not isinstance(row, dict):
            continue
        platform = row.get("platform")
        value = row.get("value")
        if platform and value:
            items.append((str(platform).lower(), str(value).strip()))
            continue
        for key, value in row.items():
            if value:
                items.append((str(key).lower(), str(value).strip()))
    return items


def social_href(key: str, value: str) -> str:
    if key == "instagram" and not value.startswith("http"):
        return "https://instagram.com/" + value.lstrip("@")
    if key in {"facebook", "linkedin", "website"} and not value.startswith("http"):
        return "https://" + value.lstrip("/")
    return value


def social_label(key: str, value: str) -> str:
    labels = {
        "website": value.replace("https://", "").replace("http://", "").replace("www.", ""),
        "facebook": "Facebook",
        "instagram": "Instagram",
        "linkedin": "LinkedIn",
    }
    return labels.get(key, key.title())


def board_contact_href(kind: str, value: str) -> str:
    if kind == "email":
        return "mailto:" + value
    if kind == "phone":
        digits = "".join(ch for ch in value if ch.isdigit() or ch == "+")
        return "tel:" + digits
    return value


def board_contact_icon(kind: str) -> str:
    return {
        "email": "assets/icon/icon-mail.svg",
        "phone": "assets/icon/icon-hardware.svg",
    }.get(kind, "assets/icon/ui/icon-link.svg")


def render_board_card(profile: dict[str, object], featured: bool = False) -> str:
    if not profile:
        return ""
    role = "Board chair" if has_tag(profile, "board_chair") else "Board member"
    symbolic = "assets/icon/icon-profile.svg" in str(profile.get("image", "")).lower()
    portrait = (
        '<div class="board-card__portrait board-card__portrait--symbolic" role="img" aria-label="Symbolic portrait marker">'
        '<img class="board-card__placeholder-icon" src="assets/icon/icon-profile.svg" alt="" aria-hidden="true" />'
        "</div>"
        if symbolic or not profile.get("image")
        else f'<figure class="board-card__portrait"><img class="board-card__photo" src="{escape(rel_asset(profile["image"]))}" alt="Portrait of {escape(profile.get("name", "Board member"))}" loading="lazy" decoding="async" /></figure>'
    )
    paragraphs = [paragraph for paragraph in profile.get("bio", []) if paragraph]
    summary_bio = str(profile.get("summary_bio", "") or "").strip()
    summary = summary_bio or (paragraphs[0] if paragraphs else "Biography currently unavailable.")
    detail_lines = paragraphs if summary_bio else paragraphs[1:]
    if profile.get("year_joined_board"):
        detail_lines.append(f'Year joined board: {profile["year_joined_board"]}')
    if profile.get("why_joined_the_board"):
        detail_lines.append(f'Why joined the board: {profile["why_joined_the_board"]}')
    detail = (
        '<details class="board-card__details">'
        "<summary>Read full profile</summary>"
        f'<div class="board-card__details-body">{"".join(f"<p>{escape(line)}</p>" for line in detail_lines)}</div>'
        "</details>"
        if detail_lines
        else ""
    )
    meta_items = []
    if profile.get("email"):
        meta_items.append(
            f'<li><a href="mailto:{escape(profile["email"])}"><img src="assets/icon/icon-mail.svg" alt="" aria-hidden="true" /><span>Email</span></a></li>'
        )
    if profile.get("secondary_email"):
        href = board_contact_href("email", str(profile["secondary_email"]))
        meta_items.append(
            f'<li><a href="{escape(href)}"><img src="{escape(board_contact_icon("email"))}" alt="" aria-hidden="true" /><span>Alt email</span></a></li>'
        )
    if profile.get("phone"):
        href = board_contact_href("phone", str(profile["phone"]))
        meta_items.append(
            f'<li><a href="{escape(href)}"><img src="{escape(board_contact_icon("phone"))}" alt="" aria-hidden="true" /><span>Phone</span></a></li>'
        )
    for key, value in social_pairs(profile):
        href = social_href(key, value)
        meta_items.append(
            f'<li><a href="{escape(href)}"{external_link_attrs(href)}><img src="{escape(board_social_icon(key))}" alt="" aria-hidden="true" /><span>{escape(social_label(key, value))}</span></a></li>'
        )
    tags = [str(tag).replace("_", " ") for tag in profile.get("tags", []) if str(tag).lower() != "board_chair"]
    featured_class = " board-card--featured" if featured else ""
    chair_mark = '<span class="board-card__chair-mark">Chair</span>' if role == "Board chair" else ""
    meta_html = '<ul class="board-card__meta">' + "".join(meta_items) + "</ul>" if meta_items else ""
    tags_html = '<p class="board-card__tags">' + "".join(f"<span>{escape(tag)}</span>" for tag in tags[:4]) + "</p>" if tags else ""
    return (
        f'<article class="board-card{featured_class}">'
        '<div class="board-card__head">'
        f"{portrait}"
        '<div class="board-card__identity">'
        f'<p class="board-card__role">{chair_mark}{escape(role)}</p>'
        f'<h3>{escape(profile.get("name", "Board member"))}</h3>'
        "</div>"
        "</div>"
        f'<p class="board-card__summary">{escape(summary)}</p>'
        f"{detail}"
        f"{meta_html}"
        f"{tags_html}"
        "</article>"
    )


def board_social_icon(key: str) -> str:
    return {
        "website": "assets/icon/icon-www.svg",
        "facebook": "assets/icon/logos/logo-facebook.svg",
        "instagram": "assets/icon/logos/logo-instagram.svg",
        "linkedin": "assets/icon/logos/logo-linkedin.svg",
    }.get(key, "assets/icon/ui/icon-link.svg")


def to_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return datetime.strptime(str(value)[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def format_date(value: date) -> str:
    return value.strftime("%b %d, %Y").replace(" 0", " ")


def format_month_day(value: date) -> str:
    return value.strftime("%b %d").replace(" 0", " ")


def next_occurrence(recurrence: dict[str, object], today: date) -> date | None:
    start = to_date(recurrence.get("starts_on")) or today
    until = to_date(recurrence.get("until")) or (start + timedelta(days=365))
    if today > until:
        return None
    weekday = recurrence.get("weekday")
    if weekday is None:
        return start if start >= today else None
    probe = max(start, today)
    offset = (int(weekday) - probe.weekday() - 1) % 7
    candidate = probe + timedelta(days=offset)
    return candidate if candidate <= until else None


def classify_schedule_entry(entry: dict[str, object]) -> str:
    if entry.get("entry_type") == "recurring_pattern":
        return "recurring"
    if entry.get("timeline_kind") == "dated_point":
        return "special_day"
    return "span"


def build_schedule_entries(data: dict[str, object]) -> list[dict[str, object]]:
    entries = []
    for raw in data.get("schedule", {}).get("entries", []):
        start = to_date(raw.get("start_date"))
        end = to_date(raw.get("end_date")) or start
        entries.append(
            {
                "id": f'happening-{raw["id"]}',
                "title": raw.get("title") or "Program listing",
                "start": start,
                "end": end,
                "time_text": raw.get("time_text") or "",
                "location": raw.get("location") or raw.get("category") or "",
                "summary": raw.get("summary") or "",
                "url": raw.get("url") or "",
                "kind": classify_schedule_entry(raw),
                "recurrence": raw.get("recurrence"),
            }
        )
    return [entry for entry in entries if entry["start"]]


def upcoming_happenings(data: dict[str, object], limit: int) -> list[dict[str, object]]:
    today = date.today()
    cards = []
    for entry in build_schedule_entries(data):
        if entry["kind"] == "recurring" and entry["recurrence"]:
            next_day = next_occurrence(entry["recurrence"], today)
            if not next_day:
                continue
            cards.append({**entry, "next_date": next_day, "date_label": format_date(next_day), "tag_label": "Recurring"})
            continue
        if entry["start"] >= today:
            label = format_date(entry["start"]) if entry["start"] == entry["end"] else f'{format_month_day(entry["start"])} - {format_month_day(entry["end"])}'
            cards.append({**entry, "next_date": entry["start"], "date_label": label, "tag_label": HAPPENING_TYPE_META[entry["kind"]]["label"]})
    cards.sort(key=lambda item: item["next_date"])
    return cards[:limit]


def render_home_event_cards(cards: list[dict[str, object]]) -> str:
    if not cards:
        return '<p class="timeline-intro" style="margin:0;">See current dates and recurring programs on <a href="happenings.html">Programs &amp; calendar</a>.</p>'
    return "".join(
        (
            f'<a class="home-event-mini" href="happenings.html#{escape(card["id"])}" style="border-left-color:{escape(HAPPENING_TYPE_META[card["kind"]]["color"])}">'
            f'<h3 class="home-event-mini__title">{escape(card["title"])}</h3>'
            f'<p class="home-event-mini__date">{escape(card["date_label"])}</p>'
            f'<p class="home-event-mini__meta">{escape(card["location"])}</p>'
            f'<span class="home-event-mini__tag" style="color:{escape(HAPPENING_TYPE_META[card["kind"]]["color"])}">{escape(card["tag_label"])}</span>'
            "</a>"
        )
        for card in cards
    )


def render_happening_cards(cards: list[dict[str, object]]) -> str:
    items = []
    for card in cards:
        time_html = f'<p class="happenings-card__meta">{escape(card["time_text"])}</p>' if card.get("time_text") else ""
        location_html = f'<p class="happenings-card__meta">{escape(card["location"])}</p>' if card.get("location") else ""
        items.append(
            f'<article class="happenings-card" id="{escape(card["id"])}" style="border-left-color:{escape(HAPPENING_TYPE_META[card["kind"]]["color"])}">'
            f'<h4 class="happenings-card__title">{escape(card["title"])}</h4>'
            f'<p class="happenings-card__meta">{escape(card["date_label"])}</p>'
            f"{time_html}"
            f"{location_html}"
            f'<span class="happenings-chip">{escape(card["tag_label"])}</span>'
            "</article>"
        )
    return "".join(items)


def happenings_window_label(entries: list[dict[str, object]]) -> str:
    if not entries:
        return ""
    dates = [entry["start"] for entry in entries if entry.get("start")]
    return f"{format_date(min(dates))} - {format_date(max(dates))}"


def group_schedule_by_month(entries: list[dict[str, object]]) -> str:
    groups: dict[str, list[dict[str, object]]] = defaultdict(list)
    for entry in entries:
        groups[entry["start"].strftime("%B %Y")].append(entry)
    parts = ['<div class="happenings-month-stack">']
    for label, group in sorted(groups.items(), key=lambda item: datetime.strptime(item[0], "%B %Y")):
        parts.append(f'<section class="happenings-month-group"><h4>{escape(label)}</h4><div class="happenings-month-group__cards">')
        for entry in group:
            if entry.get("kind") == "recurring":
                date_label = f'{format_date(entry["start"])} onward'
            elif entry["start"] == entry["end"]:
                date_label = format_date(entry["start"])
            elif entry["start"].year != entry["end"].year:
                date_label = f'{format_date(entry["start"])} - {format_date(entry["end"])}'
            else:
                date_label = f'{format_month_day(entry["start"])} - {format_month_day(entry["end"])}'
            location_html = f"<p>{escape(entry['location'])}</p>" if entry.get("location") else ""
            summary_html = f"<p>{escape(entry['summary'])}</p>" if entry.get("summary") else ""
            link_html = (
                f'<p><a href="{escape(entry["url"])}"{external_link_attrs(entry["url"])}>Official source</a></p>'
                if entry.get("url")
                else ""
            )
            parts.append(
                f'<article class="happenings-record">'
                f'<h5>{escape(entry["title"])}</h5>'
                f'<p>{escape(date_label)}{f" · {escape(entry["time_text"])}" if entry.get("time_text") else ""}</p>'
                f"{location_html}"
                f"{summary_html}"
                f"{link_html}"
                "</article>"
            )
        parts.append("</div></section>")
    parts.append("</div>")
    return "".join(parts)


def render_happening_legend() -> str:
    return "".join(
        (
            '<div class="happenings-legend-item">'
            f'<span class="happenings-legend-dot" style="background:{escape(meta["color"])}"></span>'
            f'{escape(meta["label"])}'
            "</div>"
        )
        for meta in HAPPENING_TYPE_META.values()
    )


def render_happening_sections(data: dict[str, object]) -> str:
    items_by_id = {item["id"]: item for item in data.get("items", [])}
    parts = []
    for section in data.get("sections", []):
        entries = [items_by_id[item_id] for item_id in section.get("item_ids", []) if item_id in items_by_id]
        cards = []
        for item in entries[:3]:
            paragraph_html = f"<p>{escape(item['paragraph'])}</p>" if item.get("paragraph") else ""
            date_html = f"<p>{escape(item['date_label'])}</p>" if item.get("date_label") else ""
            link_html = (
                f'<p><a href="{escape(item["primary_url"])}"{external_link_attrs(item["primary_url"])}>Open source</a></p>'
                if item.get("primary_url")
                else ""
            )
            cards.append(
                '<article class="happenings-detail-card">'
                f'<h4>{escape(item["title"])}</h4>'
                f"{paragraph_html}"
                f"{date_html}"
                f"{link_html}"
                "</article>"
            )
        body = "".join(cards)
        parts.append(
            '<section class="happenings-section-summary">'
            f'<p class="happenings-detail__pill">{escape(section["title"])}</p>'
            f'<p>{escape(section["about"])}</p>'
            f"{body}"
            "</section>"
        )
    return "".join(parts)


def parts_key(item: dict[str, object]) -> tuple[int, ...]:
    parts = item.get("start", {}).get("parts", [])
    return tuple(int(part) for part in parts)


def group_events_by_period(periods: list[dict[str, object]], events: list[dict[str, object]]) -> list[dict[str, object]]:
    bucket = {period["id"]: [] for period in periods}
    unassigned: list[dict[str, object]] = []
    for event in events:
        if event.get("period_id") in bucket:
            bucket[event["period_id"]].append(event)
        else:
            unassigned.append(event)
    grouped = [{"period": period, "events": bucket[period["id"]]} for period in periods]
    if unassigned:
        grouped.append(
            {
                "period": {
                    "id": "unassigned",
                    "title": "Unassigned",
                    "summary": "These events are present in the dataset without a recognized period assignment.",
                    "icon_path": "",
                },
                "events": unassigned,
            }
        )
    return grouped


def render_history_period(period: dict[str, object], events: list[dict[str, object]]) -> str:
    icon = ""
    if period.get("icon_path"):
        icon = f'<img class="history-period__icon" src="{escape(resolve_history_asset(period["icon_path"]))}" alt="" loading="lazy" decoding="async" />'
    summary_html = f'<p class="history-period-summary">{escape(period["summary"])}</p>' if period.get("summary") else ""
    return (
        f'<section class="history-period" id="{escape(period["id"])}">'
        '<header class="history-period-header">'
        '<div class="history-period__label">'
        f'<p class="history-period__eyebrow">{escape(period.get("start", {}).get("label", "Period"))}</p>'
        f'<h2 class="history-period__title">{escape(period["title"])}</h2>'
        f"{summary_html}"
        "</div>"
        f"{icon}"
        "</header>"
        f'<div class="history-period-events">{"".join(render_history_event(event) for event in events)}</div>'
        "</section>"
    )


def render_history_event(event: dict[str, object]) -> str:
    body_parts = [event.get("paragraph"), event.get("summary")]
    body_html = "".join(f"<p>{escape(part)}</p>" for part in dedupe_nonempty(body_parts))
    images = render_history_images(event)
    audio = render_history_audio(event)
    meta = render_history_meta(event)
    sources = render_history_sources(event)
    related = render_history_related(event)
    files = render_history_files(event)
    heading_html = f'<p class="history-event__heading">{escape(event["heading"])}</p>' if event.get("heading") else ""

    return (
        f'<article class="history-event" id="{escape(event.get("slug") or slugify(event.get("title")))}">'
        '<header class="history-event__header">'
        f'<p class="history-event__date">{escape(history_date_label(event))}</p>'
        f'<h3 class="history-event__title">{escape(event.get("title") or "Untitled event")}</h3>'
        f"{heading_html}"
        "</header>"
        '<div class="history-event__grid">'
        f'<div class="history-event__main">{body_html}{images}{sources}{files}</div>'
        f'<aside class="history-event__side">{meta}{audio}{related}</aside>'
        "</div>"
        "</article>"
    )


def history_date_label(event: dict[str, object]) -> str:
    display = event.get("display") or {}
    return display.get("date_text") or event.get("heading") or "Date not stated"


def render_history_images(event: dict[str, object]) -> str:
    artifacts = event.get("artifacts") or {}
    images = artifacts.get("images") or []
    if not images:
        return ""
    parts = ['<section class="history-media"><div class="history-media-grid">']
    for image in images[:3]:
        meta_html = f'<p class="history-media-card__meta">{escape(image["meta"])}</p>' if image.get("meta") else ""
        description_html = f'<p class="history-media-card__desc">{escape(image["description"])}</p>' if image.get("description") else ""
        parts.append(
            '<figure class="history-media-card">'
            f'<img class="history-media-card__img" src="{escape(resolve_history_asset(image.get("path", "")))}" alt="{escape(image.get("alt") or image.get("title") or "Archival image")}" loading="lazy" decoding="async" />'
            '<figcaption class="history-media-card__copy">'
            f'<p class="history-media-card__title">{escape(image.get("title") or "Archival image")}</p>'
            f"{meta_html}"
            f"{description_html}"
            "</figcaption>"
            "</figure>"
        )
    parts.append("</div></section>")
    return "".join(parts)


def render_history_audio(event: dict[str, object]) -> str:
    artifacts = event.get("artifacts") or {}
    audio_entries = artifacts.get("audio") or []
    if not audio_entries:
        return ""
    return (
        '<section class="history-meta-block">'
        "<h4>Audio</h4>"
        '<div class="audio-shelf">'
        + "".join(
            (
                '<div class="oral-player">'
                '<button class="oral-player__button" type="button">Play</button>'
                '<div class="oral-player__meta">'
                f'<div class="oral-player__title">{escape(audio.get("title") or "Audio excerpt")}</div>'
                '<div class="oral-player__bar"><div class="oral-player__progress" style="width:0%;"></div></div>'
                '<div class="oral-player__time">00:00 / --:--</div>'
                f'<audio src="{escape(resolve_history_asset(audio.get("path", "")))}" preload="metadata"></audio>'
                "</div>"
                "</div>"
            )
            for audio in audio_entries[:2]
        )
        + "</div></section>"
    )


def render_history_meta(event: dict[str, object]) -> str:
    location = event.get("location") or {}
    details = event.get("details") or {}
    lines = []
    if location.get("label"):
        lines.append(f"<p>{escape(location['label'])}</p>")
    if location.get("description"):
        lines.append(f"<p>{escape(location['description'])}</p>")
    if details.get("practical_locations"):
        lines.append(f"<p>{escape(details['practical_locations'])}</p>")
    if not lines:
        return ""
    return '<section class="history-meta-block"><h4>Location</h4>' + "".join(lines) + "</section>"


def render_history_sources(event: dict[str, object]) -> str:
    sources = event.get("sources") or {}
    source_links = [source.get("url") for source in sources.get("primary", []) if source.get("url")]
    source_links.extend(source.get("url") for source in sources.get("additional", []) if source.get("url"))
    details = event.get("details") or {}
    if details.get("primary_documentation_links"):
        source_links.extend(re.findall(r"https?://[^\s;,)]+", details["primary_documentation_links"]))
    source_links = unique_values(source_links)
    if not source_links:
        return ""
    return (
        '<section class="history-links"><h4>Sources</h4><ul>'
        + "".join(
            f'<li><a href="{escape(url)}"{external_link_attrs(url)}>{escape(url.replace("https://", "").replace("http://", ""))}</a></li>'
            for url in source_links
        )
        + "</ul></section>"
    )


def render_history_files(event: dict[str, object]) -> str:
    files = event.get("files") or {}
    paths = files.get("source_file_paths") or []
    if not paths:
        return ""
    return (
        '<section class="history-files"><h4>Files</h4><ul>'
        + "".join(
            f'<li><a href="{escape(resolve_history_asset(path))}">{escape(Path(path).name or "File")}</a></li>'
            for path in paths[:5]
        )
        + "</ul></section>"
    )


def render_history_related(event: dict[str, object]) -> str:
    farms = event.get("related_farms") or []
    if not farms:
        return ""
    return (
        '<section class="history-meta-block"><h4>Related farms</h4><ul>'
        + "".join(
            f'<li><a href="{escape(farm.get("profile_path", "#"))}">{escape(farm.get("title") or "Farm record")}</a></li>'
            for farm in farms[:5]
        )
        + "</ul></section>"
    )


def resolve_history_asset(path: str) -> str:
    if not path:
        return ""
    return rel_asset(HISTORY_LEGACY_ASSET_PATHS.get(path, path))


def dedupe_nonempty(values: list[str | None]) -> list[str]:
    out = []
    for value in values:
        token = str(value or "").strip()
        if token and token not in out:
            out.append(token)
    return out


def unique_values(values: list[str]) -> list[str]:
    seen = set()
    out = []
    for value in values:
        if value and value not in seen:
            out.append(value)
            seen.add(value)
    return out


PAGE_RENDERERS = {
    "archive_home": render_archive_home,
    "board_directory": render_board_directory,
    "article_archive": render_article_archive,
    "happenings_overview": render_happenings_overview,
    "timeline_stack": render_timeline_stack,
    "static_fragment": render_static_fragment,
}
