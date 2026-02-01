"""Portal configuration contract backed by Postgres."""

from __future__ import annotations

from typing import Any, Mapping

from portal.portal_store import PortalStore, PortalStoreError


class PortalConfigurationContract:
    """Describe portal configuration retrieval/update shapes."""

    def __init__(self, store: PortalStore) -> None:
        self._store = store

    def fetch_configuration(
        self,
        portal_id: Mapping[str, Any],
        sections: list[str] | None = None,
        context: Mapping[str, Any] | None = None,
    ) -> Mapping[str, Any]:
        """Fetch portal configuration from Postgres."""
        _ = context
        msn_id = portal_id.get("msn_id") if isinstance(portal_id, Mapping) else None
        try:
            payloads = self._store.fetch_contract_payloads("portal_configuration")
        except PortalStoreError as exc:
            raise PortalStoreError(f"Portal configuration unavailable: {exc}") from exc

        filtered = payloads
        if msn_id:
            filtered = self._store.match_payloads_by_value(payloads, msn_id)

        entry = next(
            (item for item in filtered if item.source_file.startswith("mss.compendium")),
            None,
        )

        return {
            "portal_id": dict(portal_id),
            "sections": sections or [],
            "entry": entry.payload if entry else None,
            "payloads": [
                {"source_file": item.source_file, "payload": item.payload}
                for item in filtered
            ],
        }
