from __future__ import annotations

import html
import re


def escape(value: object) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def slugify(value: object) -> str:
    text = str(value or "").strip().lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-") or "section"


def rel_asset(path: str) -> str:
    return str(path).lstrip("/")


def external_link_attrs(href: str) -> str:
    return ' target="_blank" rel="noopener noreferrer"' if str(href).startswith(("http://", "https://")) else ""


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
    rendered = re.sub(r"`([^`]+)`", r"<code>\1</code>", rendered)
    return rendered


def render_paragraphs(paragraphs: list[str]) -> str:
    return "".join(f"<p>{render_inline_markdown(paragraph)}</p>" for paragraph in paragraphs)


def render_figure(image: dict[str, str], class_name: str = "figure", image_class: str = "figure__img") -> str:
    caption = image.get("caption")
    figcaption = f'<figcaption class="figure__cap">{escape(caption)}</figcaption>' if caption else ""
    return (
        f'<figure class="{escape(class_name)}">'
        f'<img class="{escape(image_class)}" src="{escape(rel_asset(image["src"]))}" alt="{escape(image.get("alt", ""))}">'
        f"{figcaption}"
        "</figure>"
    )


def render_image(image: dict[str, str], class_name: str = "figure", image_class: str = "figure__img") -> str:
    return render_figure(image, class_name=class_name, image_class=image_class)

