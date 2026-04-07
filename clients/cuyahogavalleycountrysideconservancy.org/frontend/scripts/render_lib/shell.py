from __future__ import annotations

from .html_utils import escape, external_link_attrs, rel_asset
from .templates import render_page


def render_navigation(manifest: dict[str, object], current_file: str) -> str:
    links = []
    for item in manifest["navigation"]:
        current = ' aria-current="page"' if item["href"] == current_file else ""
        links.append(f'<a href="{escape(item["href"])}"{current}>{escape(item["label"])}</a>')
    return "".join(links)


def render_header(manifest: dict[str, object], current_file: str) -> str:
    shell = manifest["site"]["shell"]
    wordmark_icon = shell.get("wordmark_icon")
    icon_html = (
        f'<img class="masthead__wordmark-icon" src="{escape(rel_asset(wordmark_icon))}" width="24" height="24" alt="" aria-hidden="true" />'
        if wordmark_icon
        else ""
    )
    return (
        f'<header class="{escape(shell.get("masthead_class", "masthead"))}">'
        '<div class="masthead__top">'
        f'<a class="{escape(shell.get("wordmark_class", "masthead__wordmark"))}" href="{escape(manifest["site"]["homepage_href"])}">'
        f"{icon_html}"
        f'{escape(shell["wordmark_text"])}'
        "</a>"
        f'<p class="masthead__subtitle">{escape(shell["subtitle"])}</p>'
        "</div>"
        f'<nav class="masthead__nav" aria-label="Primary">{render_navigation(manifest, current_file)}</nav>'
        "</header>"
    )


def render_footer_column(column: dict[str, object]) -> str:
    template = column["template"]
    heading = f'<h4 class="footer__mini-heading">{escape(column["heading"])}</h4>'

    if template == "rich_text":
        body = "".join(f'<p class="{escape(paragraph.get("class_name", "footer__text"))}">{paragraph["html"]}</p>' for paragraph in column["paragraphs"])
    elif template == "newsletter_form":
        body = (
            f'<form class="footer-newsletter" action="{escape(column.get("action", "/newsletter.html"))}" method="{escape(column.get("method", "get"))}">'
            f'<label class="footer-newsletter__label">{escape(column["label"])}'
            f'<input class="footer-newsletter__input" type="email" name="{escape(column.get("name", "email"))}" autocomplete="email" placeholder="{escape(column.get("placeholder", "you@example.org"))}" />'
            "</label>"
            f'<button class="footer-newsletter__button" type="submit">{escape(column.get("button_label", "Join"))}</button>'
            "</form>"
            + "".join(f'<p class="{escape(paragraph.get("class_name", "footer__nav-muted"))}">{paragraph["html"]}</p>' for paragraph in column.get("paragraphs", []))
        )
    else:
        raise ValueError(f"Unsupported footer column template: {template}")

    return f'<section class="{escape(column["class_name"])}">{heading}{body}</section>'


def render_footer(manifest: dict[str, object]) -> str:
    footer = manifest["footer"]
    columns = "".join(render_footer_column(column) for column in footer["columns"])
    production = footer["production_mark"]
    return (
        f'<footer class="{escape(footer.get("class_name", "footer"))}">'
        f'<div class="{escape(footer.get("main_class", "footer__main"))}">{columns}</div>'
        f'<div class="{escape(footer.get("lower_class", "footer__lower"))}">'
        f'<div class="footer__copyright">{escape(footer["copyright"])}</div>'
        f'<a class="footer__production-mark" href="{escape(production["href"])}"{external_link_attrs(production["href"])}>'
        f'<span>{escape(production["label"])}</span>'
        '<span class="footer__production-icon" aria-hidden="true"></span>'
        "</a>"
        "</div>"
        "</footer>"
    )


def render_document(manifest: dict[str, object], page_key: str, page: dict[str, object], frontend_root) -> str:
    stylesheets = page.get("stylesheets", manifest["site"].get("stylesheets", []))
    stylesheet_tags = "\n".join(f'  <link rel="stylesheet" href="{escape(rel_asset(path))}" />' for path in stylesheets)
    site_scripts = manifest["site"].get("scripts", [])
    page_scripts = page.get("scripts", [])
    scripts = list(dict.fromkeys([*site_scripts, *page_scripts])) if page_scripts else list(site_scripts)
    script_tags = "\n".join(f'  <script src="{escape(rel_asset(path))}" defer></script>' for path in scripts)
    description = page.get("description", manifest["site"].get("description", ""))
    body_class = f' class="{escape(page["body_class"])}"' if page.get("body_class") else ""

    return "\n".join(
        [
            "<!DOCTYPE html>",
            '<html lang="en">',
            "<head>",
            '  <meta charset="UTF-8" />',
            '  <meta name="viewport" content="width=device-width, initial-scale=1.0" />',
            f"  <title>{escape(page['title'])}</title>",
            f'  <meta name="description" content="{escape(description)}" />',
            f'  <link rel="icon" type="{escape(manifest["site"]["favicon_type"])}" href="{escape(rel_asset(manifest["site"]["favicon"]))}" />',
            stylesheet_tags,
            "</head>",
            f"<body{body_class}>",
            "  <!-- Generated from assets/docs/manifest.json by scripts/render_manifest.py -->",
            f"  {render_header(manifest, page['file'])}",
            f'  <main class="{escape(page["main_class"])}">{render_page(page, manifest, frontend_root)}</main>',
            f"  {render_footer(manifest)}",
            script_tags,
            "</body>",
            "</html>",
            "",
        ]
    )
