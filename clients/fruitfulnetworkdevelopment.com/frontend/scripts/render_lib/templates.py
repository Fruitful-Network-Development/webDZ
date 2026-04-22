from __future__ import annotations

from .html_utils import generation_marker


def render_template(page: dict[str, object]) -> str:
    template = page["template"]

    if template == "verbatim_document":
        return apply_generation_marker(page["source_html"])

    if template == "verbatim_fragment":
        source = page["source_html"]
        marker = generation_marker()
        return f"{marker}\n{source.lstrip()}"

    renderer = PAGE_RENDERERS.get(template)
    if renderer is None:
        raise ValueError(f"Unsupported page template: {template}")
    return renderer(page)


def render_home(page: dict[str, object]) -> str:
    return page["content"]["main_html"].strip()


def render_services(page: dict[str, object]) -> str:
    return page["content"]["main_html"].strip()


def render_research(page: dict[str, object]) -> str:
    return page["content"]["main_html"].strip()


def render_about(page: dict[str, object]) -> str:
    return page["content"]["main_html"].strip()


def render_contact(page: dict[str, object]) -> str:
    return page["content"]["main_html"].strip()


def render_subpage(page: dict[str, object]) -> str:
    return page["content"]["main_html"].strip()


def apply_generation_marker(source_html: str) -> str:
    marker = generation_marker()
    if marker in source_html:
        return source_html

    body_index = source_html.find("<body")
    if body_index < 0:
        return source_html

    body_open_end = source_html.find(">", body_index)
    if body_open_end < 0:
        return source_html

    insertion_point = body_open_end + 1
    return source_html[:insertion_point] + f"\n  {marker}" + source_html[insertion_point:]


PAGE_RENDERERS = {
    "fnd_home": render_home,
    "fnd_services": render_services,
    "fnd_research": render_research,
    "fnd_about": render_about,
    "fnd_contact": render_contact,
    "fnd_subpage": render_subpage,
}
