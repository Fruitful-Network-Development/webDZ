from __future__ import annotations

from pathlib import Path

from .html_utils import generation_marker
from .templates import render_template


def _escape(value: object) -> str:
    text = str(value)
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def render_navigation(manifest: dict[str, object], page: dict[str, object]) -> str:
    current_href = page.get("navigation_current_href", page.get("file"))
    current_file = page.get("file", "")
    links = []
    for item in manifest.get("navigation", []):
        href = item["href"]
        if current_file.startswith("subpages/") and href.startswith("./"):
            href = "../" + href[2:]
        classes = "topbar__link"
        if href == current_href:
            classes += " is-current"
        links.append(f'<a class="{classes}" href="{_escape(href)}">{_escape(item["label"])}</a>')
    return "\n        ".join(links)


def render_header(manifest: dict[str, object], page: dict[str, object]) -> str:
    shell = manifest.get("site", {}).get("shell", {})
    home_href = page.get("shell", {}).get("home_href", shell.get("home_href", "./index.html"))
    mark = shell.get("mark", "FND")
    menu_icon = shell.get("menu_icon", "/assets/icon/icon-menu.svg")
    search_icon = shell.get("search_icon", "/assets/icon/icon-search.svg")
    return "\n".join(
        [
            '  <header class="topbar">',
            '    <div class="topbar__inner">',
            '      <button class="topbar__icon topbar__menu header__button--sidebar" type="button" aria-label="Index">',
            f'        <img src="{_escape(menu_icon)}" alt="" />',
            "      </button>",
            f'      <a class="topbar__mark" href="{_escape(home_href)}">{_escape(mark)}</a>',
            '      <nav class="topbar__nav" aria-label="Primary">',
            f"        {render_navigation(manifest, page)}",
            "      </nav>",
            '      <button class="topbar__icon" type="button" aria-label="Search">',
            f'        <img src="{_escape(search_icon)}" alt="" />',
            "      </button>",
            "    </div>",
            "  </header>",
        ]
    )


def render_footer(manifest: dict[str, object], page: dict[str, object]) -> str:
    footer_cfg = manifest.get("footer", {})
    page_shell = page.get("shell", {})
    if not page_shell.get("show_footer", False):
        return ""

    social_links = "".join(
        f'<a href="{_escape(link["href"])}" aria-label="{_escape(link["label"])}"><img src="{_escape(link["icon"])}" alt="{_escape(link.get("alt", link["label"]))}" loading="lazy" /></a>'
        for link in footer_cfg.get("social", [])
    )

    columns = []
    for col in footer_cfg.get("columns", []):
        lines = "".join(f"<p>{line}</p>" for line in col.get("lines", []))
        columns.append(
            "".join(
                [
                    f'<section{(" class=\"" + _escape(col["class_name"]) + "\"") if col.get("class_name") else ""}>',
                    f"<h2>{_escape(col['heading'])}</h2>",
                    lines,
                    "</section>",
                ]
            )
        )

    subscribe = footer_cfg.get("subscribe")
    subscribe_html = ""
    if subscribe:
        subscribe_html = "\n".join(
            [
                f'    <div class="ledger-footer__subscribe" id="{_escape(subscribe.get("id", "newsletter-subscribe"))}">',
                f'      {subscribe["html"]}',
                "    </div>",
            ]
        )

    return "\n".join(
        [
            '  <footer class="ledger-footer">',
            f'    <div class="ledger-footer__social" aria-label="Social links">{social_links}</div>',
            f'    <div class="ledger-footer__grid">{"".join(columns)}</div>',
            subscribe_html,
            "  </footer>",
        ]
    )


def render_head(page: dict[str, object]) -> str:
    head = page.get("head", {})
    lines = [
        "<head>",
        '  <meta charset="utf-8" />',
        f'  <meta name="viewport" content="{_escape(head.get("viewport", "width=device-width, initial-scale=1.0"))}" />',
        f"  <title>{_escape(page['title'])}</title>",
    ]
    if page.get("description"):
        lines.append(f'  <meta name="description" content="{_escape(page["description"])}" />')
    if head.get("canonical"):
        lines.append(f'  <link rel="canonical" href="{_escape(head["canonical"])}" />')
    for meta in head.get("meta", []):
        attrs = " ".join(f'{_escape(k)}="{_escape(v)}"' for k, v in meta.items())
        lines.append(f"  <meta {attrs} />")
    favicon = head.get("favicon", "favicon.svg")
    lines.append(f'  <link rel="icon" type="image/svg+xml" href="{_escape(favicon)}">')
    for href in head.get("stylesheets", []):
        lines.append(f'  <link rel="stylesheet" href="{_escape(href)}">')
    lines.append("</head>")
    return "\n".join(lines)


def _page_path_from_file(file_path: str) -> str:
    normalized = file_path.strip("/")
    return "/" if normalized == "index.html" else f"/{normalized}"


def render_machine_inpage_blocks(
    manifest: dict[str, object], page_key: str, page: dict[str, object], frontend_root: Path
) -> str:
    machine = manifest.get("machine") or manifest.get("machine_surfaces") or {}
    if not isinstance(machine, dict):
        return ""

    inpage = machine.get("inpage", {})
    if not isinstance(inpage, dict):
        return ""

    root = inpage.get("root")
    blocks = inpage.get("blocks", [])
    if not isinstance(root, str) or not isinstance(blocks, list):
        return ""

    page_path = _page_path_from_file(str(page.get("file", "")))
    rendered_blocks: list[str] = []
    for block in blocks:
        if not isinstance(block, dict):
            continue
        block_page_key = block.get("page_key")
        block_page_path = block.get("page")
        if block_page_key not in {None, page_key} and block_page_path not in {None, page_path}:
            continue
        if block_page_key not in {None, page_key}:
            continue
        if block_page_key is None and block_page_path not in {None, page_path}:
            continue

        source = block.get("source")
        if not isinstance(source, str):
            continue
        source_path = frontend_root / root / source
        if not source_path.exists():
            continue
        payload = source_path.read_text().strip()

        block_id = _escape(block.get("id", "machine-block"))
        pattern = block.get("injection_pattern")
        if pattern == "script:application/ld+json":
            rendered_blocks.append(
                "\n".join(
                    [
                        f'  <script type="application/ld+json" data-machine-block-id="{block_id}" data-machine-page-key="{_escape(page_key)}">',
                        payload,
                        "  </script>",
                    ]
                )
            )
        elif pattern == "script:application/json":
            rendered_blocks.append(
                "\n".join(
                    [
                        f'  <script type="application/json" data-machine-block-id="{block_id}" data-machine-page-key="{_escape(page_key)}">',
                        payload,
                        "  </script>",
                    ]
                )
            )
        elif pattern == "meta:container":
            rendered_blocks.append(
                "\n".join(
                    [
                        f'  <template data-machine-block-id="{block_id}" data-machine-page-key="{_escape(page_key)}" data-machine-content-type="application/json">',
                        payload,
                        "  </template>",
                    ]
                )
            )

    return "\n".join(rendered_blocks)


def render_document(manifest: dict[str, object], _page_key: str, page: dict[str, object], _frontend_root) -> str:
    if page["template"] in {"verbatim_document", "verbatim_fragment"}:
        rendered = render_template(page)
        return rendered if rendered.endswith("\n") else rendered + "\n"

    body_attrs = []
    if page.get("body_id"):
        body_attrs.append(f'id="{_escape(page["body_id"])}"')
    if page.get("body_class"):
        body_attrs.append(f'class="{_escape(page["body_class"])}"')
    body_attr_text = (" " + " ".join(body_attrs)) if body_attrs else ""

    main_html = render_template(page)
    footer_html = render_footer(manifest, page)
    machine_inpage_blocks = render_machine_inpage_blocks(manifest, _page_key, page, _frontend_root)
    scripts = page.get("scripts", [])
    script_tags = "\n".join(f'  <script src="{_escape(src)}" defer></script>' for src in scripts)
    inline_scripts = "\n".join(f"  <script>\n{script}\n  </script>" for script in page.get("inline_scripts", []))

    lines = [
        "<!doctype html>",
        '<html lang="en">',
        render_head(page),
        f"<body{body_attr_text}>",
        f"  {generation_marker()}",
        render_header(manifest, page),
        f'  <main class="{_escape(page.get("main_class", "edition"))}">',
        f"{main_html}",
        "  </main>",
    ]
    if machine_inpage_blocks:
        lines.append(machine_inpage_blocks)
    if footer_html:
        lines.append(footer_html)
    if script_tags:
        lines.append(script_tags)
    if inline_scripts:
        lines.append(inline_scripts)
    lines.extend(["</body>", "</html>", ""])

    doc = "\n".join(lines)
    return doc
