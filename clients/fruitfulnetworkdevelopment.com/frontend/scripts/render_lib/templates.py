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
    return render_modular_page_body(page)


def render_services(page: dict[str, object]) -> str:
    return render_modular_page_body(page)


def render_research(page: dict[str, object]) -> str:
    return render_modular_page_body(page)


def render_about(page: dict[str, object]) -> str:
    return render_modular_page_body(page)


def render_contact(page: dict[str, object]) -> str:
    return render_modular_page_body(page)


def render_subpage(page: dict[str, object]) -> str:
    return render_modular_page_body(page)


def render_modular_page_body(page: dict[str, object]) -> str:
    content = page.get("content", {})
    if not isinstance(content, dict):
        return ""

    # Canonical modular shape: page content is composed from ordered sections.
    sections = content.get("sections")
    if isinstance(sections, list):
        parts: list[str] = []
        for section in sections:
            if not isinstance(section, dict):
                continue
            if section.get("enabled", True) is False:
                continue
            html = section.get("html")
            if isinstance(html, str) and html.strip():
                parts.append(html.strip())
        if parts:
            return "\n\n".join(parts)

    # Backward compatibility for legacy save-point page payloads.
    main_html = content.get("main_html")
    if isinstance(main_html, str):
        return main_html.strip()
    return ""


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
