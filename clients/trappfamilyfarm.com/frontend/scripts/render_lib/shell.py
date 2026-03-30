from __future__ import annotations

from .html_utils import escape, external_link_attrs, rel_asset, render_css_vars
from .templates import render_page


def render_navigation(manifest: dict[str, object], current_file: str) -> str:
    items = []
    for item in manifest["navigation"]:
        active = ' class="active"' if item["href"] == current_file else ""
        items.append(
            "<li>"
            f'<a href="{escape(item["href"])}"{active}>{escape(item["label"])}</a>'
            "</li>"
        )
    return "".join(items)


def render_header(manifest: dict[str, object], page: dict[str, object], current_file: str) -> str:
    shell = manifest["site"]["shell"]
    page_shell = page.get("shell", {})
    nav_html = render_navigation(manifest, current_file)
    header_graphic = ""
    if page_shell.get("show_header_graphic"):
        header_graphic = (
            '<div class="header-graphic" aria-hidden="true">'
            f'<img src="{escape(rel_asset(shell["assets"]["header_graphic"]))}" alt="">'
            "</div>"
        )

    main_nav = ""
    if page_shell.get("show_main_nav", True):
        main_nav = (
            '<nav class="main-nav" aria-label="Primary">'
            f'<ul class="nav-with-icons" id="nav-root">{nav_html}</ul>'
            "</nav>"
        )

    wordmark = "".join(f"<span>{escape(line)}</span>" for line in shell["wordmark_lines"])
    menu_label = escape(shell.get("menu_label", "Menu"))
    homepage_href = escape(manifest["site"]["homepage_href"])

    drawer = (
        '<div class="nav-overlay" id="nav-overlay" aria-hidden="true"></div>'
        '<aside class="nav-drawer" id="site-nav-drawer" role="dialog" aria-modal="true" '
        'aria-labelledby="site-nav-drawer-title" aria-hidden="true">'
        '<div class="nav-drawer-top">'
        f'<p class="nav-drawer-title" id="site-nav-drawer-title">{menu_label}</p>'
        '<button type="button" class="nav-drawer-close" aria-label="Close menu"><span aria-hidden="true">×</span></button>'
        "</div>"
        '<nav class="nav-drawer-nav" aria-label="Site pages">'
        f'<ul class="nav-with-icons nav-drawer-list" id="nav-drawer-root">{nav_html}</ul>'
        "</nav>"
        "</aside>"
    )

    return (
        '<header class="site-header">'
        '<div class="header-inner">'
        '<button type="button" class="nav-toggle" aria-label="Open menu" '
        'aria-expanded="false" aria-controls="site-nav-drawer">'
        '<span class="nav-toggle-bars" aria-hidden="true"><span></span><span></span><span></span></span>'
        "</button>"
        f"{header_graphic}"
        f'<a href="{homepage_href}" class="logo">'
        f'<span class="logo-text">{wordmark}</span>'
        "</a>"
        f"{main_nav}"
        "</div>"
        "</header>"
        f"{drawer}"
    )


def render_footer(manifest: dict[str, object]) -> str:
    shell = manifest["site"]["shell"]
    footer = manifest["footer"]
    columns = "".join(render_footer_column(column) for column in footer["columns"])
    return (
        '<footer class="site-footer" id="footer-root">'
        '<div class="footer-inner">'
        '<div class="footer-illustration">'
        f'<img src="{escape(rel_asset(shell["assets"]["footer_graphic"]))}" alt="">'
        "</div>"
        f"{columns}"
        "</div>"
        f'<div class="footer-bottom"><p>{escape(footer["copyright"])}</p></div>'
        "</footer>"
    )


def render_footer_column(column: dict[str, object]) -> str:
    template = column["template"]
    class_name = escape(column["class_name"])
    heading = escape(column["heading"])

    if template == "contact_lines":
        items = []
        for item in column["items"]:
            item_template = item["template"]
            if item_template == "text":
                items.append(escape(item["value"]))
            elif item_template == "phone":
                items.append(f'<a href="tel:+1{escape(item["value"])}">{escape(item["label"])}</a>')
            elif item_template == "email":
                items.append(f'<a href="mailto:{escape(item["value"])}">{escape(item["value"])}</a>')
            else:
                raise ValueError(f"Unsupported footer item template: {item_template}")
        body = "<p>" + "<br>".join(items) + "</p>"
    elif template == "line_list":
        body = "<p>" + "<br>".join(escape(line) for line in column["lines"]) + "</p>"
    elif template == "social_links":
        body = "".join(
            f'<p><a class="{escape(link.get("class_name", "instagram-link"))}" href="{escape(link["href"])}"{external_link_attrs(link["href"])} '
            f'aria-label="{escape(link["label"])}"><img src="{escape(rel_asset(link["icon"]))}" alt=""></a></p>'
            for link in column["links"]
        )
    else:
        raise ValueError(f"Unsupported footer column template: {template}")

    return f'<div class="footer-col {class_name}"><h3>{heading}</h3>{body}</div>'


def render_document(manifest: dict[str, object], page_key: str, page: dict[str, object], frontend_root) -> str:
    shell = manifest["site"]["shell"]
    current_file = page["file"]
    body_classes = " ".join(value for value in [page.get("body_class", "")] if value)
    body_class_attr = f' class="{escape(body_classes)}"' if body_classes else ""
    favicon = escape(rel_asset(shell["assets"]["favicon"]))
    return "\n".join(
        [
            "<!DOCTYPE html>",
            "<html lang=\"en\">",
            "<head>",
            "  <meta charset=\"UTF-8\">",
            "  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">",
            f"  <title>{escape(page['title'])}</title>",
            f"  <meta name=\"description\" content=\"{escape(page['description'])}\">",
            f'  <link rel="icon" type="image/svg+xml" href="{favicon}">',
            '  <link rel="stylesheet" href="css/style.css">',
            "</head>",
            f'<body data-page="{escape(page_key)}"{body_class_attr} style="{escape(render_css_vars(manifest))}">',
            f"  <!-- Generated from assets/docs/manifest.json by scripts/render_manifest.py -->",
            f"  {render_header(manifest, page, current_file)}",
            f'  <main class="main" id="main-root">{render_page(page, manifest, frontend_root)}</main>',
            f"  {render_footer(manifest)}",
            '  <script src="js/site-shell.js"></script>',
            '  <script src="js/gallery-home-button.js"></script>',
            "</body>",
            "</html>",
        ]
    ) + "\n"
