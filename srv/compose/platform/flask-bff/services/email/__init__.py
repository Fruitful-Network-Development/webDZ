"""Email service integration boundary (placeholder)."""
from __future__ import annotations

from typing import Protocol


class EmailService(Protocol):
    def send(self, *, to: str, subject: str, body: str) -> None:
        """Send an email notification."""
        raise NotImplementedError
