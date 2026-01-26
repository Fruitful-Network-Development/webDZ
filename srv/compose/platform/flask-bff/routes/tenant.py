"""Tenant console and health routes."""
from __future__ import annotations

from flask import Blueprint, abort, redirect, render_template, request
from jinja2 import TemplateNotFound

from config import DEMO_TABLE_ID
from routes.common import enabled_console_modules, require_tenant_console_access


tenant_bp = Blueprint("tenant", __name__)


@tenant_bp.get("/t/<tenant_id>/console")
def tenant_console(tenant_id: str):
    tenant_cfg, error = require_tenant_console_access(tenant_id)
    if error:
        return error
    enabled_modules = enabled_console_modules(tenant_cfg)

    return render_template(
        "tenant/console.html",
        tenant_id=tenant_id,
        tenant_cfg=tenant_cfg,
        enabled_modules=enabled_modules,
    ), 200


@tenant_bp.get("/t/<tenant_id>/console/")
def tenant_console_slash(tenant_id: str):
    qs = request.query_string.decode("utf-8")
    suffix = f"?{qs}" if qs else ""
    return redirect(f"/t/{tenant_id}/console{suffix}")


@tenant_bp.get("/t/<tenant_id>/console/<module>")
def tenant_console_module(tenant_id: str, module: str):
    tenant_cfg, error = require_tenant_console_access(tenant_id)
    if error:
        return error

    enabled_modules = enabled_console_modules(tenant_cfg)
    if module not in enabled_modules:
        abort(404)

    template_name = f"tenant/console_{module}.html"
    try:
        return render_template(
            template_name,
            tenant_id=tenant_id,
            tenant_cfg=tenant_cfg,
            module=module,
            enabled_modules=enabled_modules,
            demo_table_id=DEMO_TABLE_ID,
        ), 200
    except TemplateNotFound:
        abort(404)


@tenant_bp.get("/t/<tenant_id>/console/<module>/")
def tenant_console_module_slash(tenant_id: str, module: str):
    qs = request.query_string.decode("utf-8")
    suffix = f"?{qs}" if qs else ""
    return redirect(f"/t/{tenant_id}/console/{module}{suffix}")

