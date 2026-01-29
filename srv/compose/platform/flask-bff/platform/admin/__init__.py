"""Platform admin routes."""

from platform.admin.legacy import admin_bp
from platform.admin.routes import admin_data_env_bp

__all__ = ["admin_bp", "admin_data_env_bp"]

