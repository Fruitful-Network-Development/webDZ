"""Keycloak JWT verification helpers."""
from __future__ import annotations

from dataclasses import dataclass
import os
import time
from typing import Any, Dict

import requests
from authlib.jose import jwt


class KeycloakAuthError(RuntimeError):
    """Raised when Keycloak authentication fails."""


@dataclass(frozen=True)
class KeycloakConfig:
    issuer: str
    audience: str
    jwks_url: str
    algorithms: tuple[str, ...] = ("RS256",)


_JWKS_CACHE: dict[str, Any] = {"expires_at": 0, "jwks": None}


def load_config() -> KeycloakConfig:
    issuer = os.getenv("KEYCLOAK_ISSUER") or os.getenv("OIDC_ISSUER")
    audience = os.getenv("KEYCLOAK_AUDIENCE") or os.getenv("OIDC_CLIENT_ID")
    if not issuer or not audience:
        raise KeycloakAuthError("Set KEYCLOAK_ISSUER/KEYCLOAK_AUDIENCE or OIDC_ISSUER/OIDC_CLIENT_ID.")
    jwks_url = os.getenv("KEYCLOAK_JWKS_URL") or f"{issuer.rstrip('/')}/protocol/openid-connect/certs"
    return KeycloakConfig(issuer=issuer, audience=audience, jwks_url=jwks_url)


def _get_jwks(config: KeycloakConfig) -> Dict[str, Any]:
    ttl = int(os.getenv("KEYCLOAK_JWKS_TTL", "300"))
    now = int(time.time())
    if _JWKS_CACHE["jwks"] is not None and _JWKS_CACHE["expires_at"] > now:
        return _JWKS_CACHE["jwks"]

    response = requests.get(config.jwks_url, timeout=10)
    if response.status_code != 200:
        raise KeycloakAuthError(f"Failed to fetch JWKS: {response.status_code}")
    jwks = response.json()
    _JWKS_CACHE["jwks"] = jwks
    _JWKS_CACHE["expires_at"] = now + ttl
    return jwks


def decode_token(token: str) -> dict[str, Any]:
    config = load_config()
    jwks = _get_jwks(config)

    claims_options = {
        "iss": {"essential": True, "value": config.issuer},
        "aud": {"essential": True, "value": config.audience},
        "exp": {"essential": True},
    }

    try:
        claims = jwt.decode(token, jwks, claims_options=claims_options)
        claims.validate()
    except Exception as exc:  # pragma: no cover - authlib throws multiple types
        raise KeycloakAuthError("Token validation failed.") from exc

    return dict(claims)
