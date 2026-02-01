"""Console data contract backed by Postgres."""

from __future__ import annotations

from typing import Any, Mapping

from portal.portal_store import PortalStore, PortalStoreError


class ConsoleDataContract:
    """Describe console data retrieval shapes."""

    def __init__(self, store: PortalStore) -> None:
        self._store = store

    def fetch_console_data(
        self,
        console_id: Mapping[str, Any],
        domains: list[str] | None = None,
        filters: Mapping[str, Any] | None = None,
        context: Mapping[str, Any] | None = None,
    ) -> Mapping[str, Any]:
        """Fetch console data from Postgres."""
        _ = filters, context
        try:
            payloads = self._store.fetch_contract_payloads("console_data")
        except PortalStoreError as exc:
            raise PortalStoreError(f"Console data unavailable: {exc}") from exc

        matched = payloads
        if isinstance(console_id, Mapping):
            for value in console_id.values():
                if isinstance(value, str):
                    matched = self._store.match_payloads_by_value(matched, value) or matched

        return {
            "console_id": dict(console_id),
            "domains": domains or [],
            "payloads": [
                {"source_file": item.source_file, "payload": item.payload}
                for item in matched
            ],
        }
