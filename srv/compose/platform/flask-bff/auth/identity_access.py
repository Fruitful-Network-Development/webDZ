"""Identity access contract backed by Postgres."""

from __future__ import annotations

from typing import Any, Mapping

from portal.portal_store import PortalStore, PortalStoreError


class IdentityAccessContract:
    """Describe identity access request/response shapes."""

    def __init__(self, store: PortalStore) -> None:
        self._store = store

    def evaluate_access(
        self,
        subject: Mapping[str, Any],
        requested_scopes: list[str],
        context: Mapping[str, Any] | None = None,
    ) -> Mapping[str, Any]:
        """Evaluate access for a subject."""
        _ = context
        user_id = subject.get("user_id") if isinstance(subject, Mapping) else None
        if not user_id:
            return {"allowed": False, "reason": "missing_user_id"}

        try:
            payloads = self._store.fetch_contract_payloads("identity_access")
        except PortalStoreError as exc:
            raise PortalStoreError(f"Identity access unavailable: {exc}") from exc

        matched = self._store.match_payloads_by_value(payloads, user_id)
        allowed = len(matched) > 0

        return {
            "user_id": user_id,
            "allowed": allowed,
            "requested_scopes": requested_scopes,
            "matches": [
                {"source_file": item.source_file, "payload": item.payload}
                for item in matched
            ],
        }
