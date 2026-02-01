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
        _ = context
        filters = filters or {}
        domains = domains or []

        msn_id = None
        if isinstance(console_id, Mapping):
            msn_id_value = console_id.get("msn_id")
            if isinstance(msn_id_value, str):
                msn_id = msn_id_value

        mode = str(filters.get("mode")) if filters.get("mode") else None
        is_admin = mode == "admin" or filters.get("is_admin") is True

        try:
            return self._fetch_admin_console(console_id, domains) if is_admin else self._fetch_tenant_console(
                console_id,
                domains,
                msn_id,
            )
        except PortalStoreError as exc:
            raise PortalStoreError(f"Console data unavailable: {exc}") from exc

    def _fetch_tenant_console(
        self,
        console_id: Mapping[str, Any],
        domains: list[str],
        msn_id: str | None,
    ) -> Mapping[str, Any]:
        if not msn_id:
            raise PortalStoreError("Tenant console requires msn_id.")

        compendium = self._store.fetch_compendium_entries(msn_id)
        anthology = self._store.fetch_anthology_entries(msn_id)
        taxonomy = self._store.fetch_taxonomy_local_map(msn_id)
        msn_map = self._store.fetch_msn_local_map(msn_id)
        muniments = self._store.fetch_muniment_entries(msn_id)

        allowed_muniments = [
            entry for entry in muniments if (entry.get("muniment") or "").lower() == "open"
        ]

        return {
            "console_id": dict(console_id),
            "domains": domains,
            "mode": "tenant",
            "msn_id": msn_id,
            "entry": compendium[0] if compendium else None,
            "anthology": anthology,
            "muniment": {
                "all": muniments,
                "allowed": allowed_muniments,
            },
            "taxonomy": taxonomy,
            "msn_map": msn_map,
        }

    def _fetch_admin_console(
        self,
        console_id: Mapping[str, Any],
        domains: list[str],
    ) -> Mapping[str, Any]:
        compendium = self._store.fetch_compendium_entries()
        anthology_by_msn = {
            entry["msn_id"]: self._store.fetch_anthology_entries(entry["msn_id"])
            for entry in compendium
        }
        taxonomy_by_msn = {
            entry["msn_id"]: self._store.fetch_taxonomy_local_map(entry["msn_id"])
            for entry in compendium
        }
        msn_map_by_msn = {
            entry["msn_id"]: self._store.fetch_msn_local_map(entry["msn_id"])
            for entry in compendium
        }
        muniment_by_msn = {
            entry["msn_id"]: self._store.fetch_muniment_entries(entry["msn_id"])
            for entry in compendium
        }

        conspectus_payloads = self._store.fetch_contract_payloads("portal_configuration")
        conspectus = [
            {"source_file": payload.source_file, "payload": payload.payload}
            for payload in conspectus_payloads
            if payload.source_file.startswith("platform.conspectus")
        ]

        beneficiary_payloads = self._store.fetch_contract_payloads("identity_access")
        beneficiaries = [
            {"source_file": payload.source_file, "payload": payload.payload}
            for payload in beneficiary_payloads
            if payload.source_file.startswith("platform.beneficiary")
        ]

        muniment_registry = self._store.fetch_all_muniment_entries()

        return {
            "console_id": dict(console_id),
            "domains": domains,
            "mode": "admin",
            "compendium": compendium,
            "anthology": anthology_by_msn,
            "taxonomy": taxonomy_by_msn,
            "msn_map": msn_map_by_msn,
            "muniment": muniment_by_msn,
            "muniment_registry": muniment_registry,
            "facilitators": conspectus,
            "beneficiaries": beneficiaries,
        }
