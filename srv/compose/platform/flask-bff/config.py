"""Configuration values for the Flask BFF."""
from __future__ import annotations

import os


def _require_env(name: str) -> str:
    val = os.getenv(name)
    if not val:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return val


OIDC_ISSUER = _require_env("OIDC_ISSUER").rstrip("/")
OIDC_CLIENT_ID = _require_env("OIDC_CLIENT_ID")
OIDC_CLIENT_SECRET = _require_env("OIDC_CLIENT_SECRET")
SESSION_SECRET = _require_env("SESSION_SECRET")

PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "").rstrip("/")
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() == "true"

DEMO_TENANT_ID = "cuyahogaterravita"
DEMO_LOCAL_DOMAIN_ID = "6c3152b3-2d2c-4f10-8fcf-3fca0d2c7af1"
DEMO_ARCHETYPE_ID = "e9fa1d2b-2a25-478a-91ef-1b31f5111c92"
DEMO_TABLE_ID = DEMO_LOCAL_DOMAIN_ID
