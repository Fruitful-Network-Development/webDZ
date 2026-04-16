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
    raise ValueError(f"Unsupported page template: {template}")


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
