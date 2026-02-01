"""Muniment access contract backed by Postgres."""

from __future__ import annotations

from typing import Any, Mapping

from portal.portal_store import PortalStore, PortalStoreError


class MunimentAccessContract:
    """Describe muniment access request/response shapes."""

    def __init__(self, store: PortalStore) -> None:
        self._store = store

    def evaluate_access(
        self,
        subject: Mapping[str, Any],
        muniment_ids: list[str],
        context: Mapping[str, Any] | None = None,
    ) -> Mapping[str, Any]:
        """Evaluate access for muniment resources."""
        _ = context
        try:
            payloads = self._store.fetch_contract_payloads("muniment_access")
        except PortalStoreError as exc:
            raise PortalStoreError(f"Muniment access unavailable: {exc}") from exc

        matched = []
        for muniment_id in muniment_ids:
            matched.extend(self._store.match_payloads_by_value(payloads, muniment_id))

        return {
            "subject": dict(subject),
            "muniment_ids": muniment_ids,
            "matched": [
                {"source_file": item.source_file, "payload": item.payload}
                for item in matched
            ],
        }
