from __future__ import annotations

from .templates import render_template


def render_document(_manifest: dict[str, object], _page_key: str, page: dict[str, object], _frontend_root) -> str:
    rendered = render_template(page)
    return rendered if rendered.endswith("\n") else rendered + "\n"
