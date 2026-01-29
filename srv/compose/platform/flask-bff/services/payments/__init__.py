"""Payments service integration boundary (placeholder)."""
from __future__ import annotations

from typing import Protocol


class PaymentsService(Protocol):
    def fetch_status(self, *, tenant_id: str) -> dict:
        """Return billing status details for the tenant."""
        raise NotImplementedError
