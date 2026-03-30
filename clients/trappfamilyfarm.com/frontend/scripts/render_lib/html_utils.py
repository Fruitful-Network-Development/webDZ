from __future__ import annotations

import html
import re


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


def render_link_list(items: list[dict[str, str]], class_name: str = "json-animal-toc") -> str:
    if not items:
        return ""

    parts = [f'<ul class="{escape(class_name)}">']
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


def render_css_vars(manifest: dict[str, object]) -> str:
    shell = manifest["site"]["shell"]
    rules = [f"--hero-bg-image: url('{rel_asset(shell['assets']['hero_background'])}')"]
    for prefix, items in [
        ("nav", manifest["icons"]["navigation"]),
        ("footer", manifest["icons"]["footer"]),
        ("section", manifest["icons"]["sections"]),
    ]:
        for key, path in items.items():
            rules.append(f"--icon-{prefix}-{key}: url('{rel_asset(path)}')")
    return "; ".join(rules)
