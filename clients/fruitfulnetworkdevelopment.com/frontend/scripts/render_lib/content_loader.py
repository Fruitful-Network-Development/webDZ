from __future__ import annotations

import json
from pathlib import Path
from typing import Any

PAGE_TEMPLATES_WITH_CONTENT = {
    "fnd_home",
    "fnd_services",
    "fnd_research",
    "fnd_about",
    "fnd_contact",
    "fnd_subpage",
}

REQUIRED_TOP_LEVEL_KEYS = (
    "schema_identifier",
    "site",
    "navigation",
    "pages",
    "machine",
)


class ManifestValidationError(ValueError):
    """Raised when manifest schema validation fails."""


class _ManifestValidator:
    def __init__(self, manifest: dict[str, Any]) -> None:
        self.manifest = manifest
        self.errors: list[str] = []

    def add_error(self, path: str, detail: str) -> None:
        self.errors.append(f"{path}: {detail}")

    def require_key(self, obj: Any, key: str, path: str) -> Any | None:
        if not isinstance(obj, dict):
            self.add_error(path, "must be an object")
            return None
        if key not in obj:
            self.add_error(f"{path}.{key}", "missing required key")
            return None
        return obj[key]

    def require_type(self, value: Any, expected_type: type | tuple[type, ...], path: str) -> bool:
        if not isinstance(value, expected_type):
            names = (
                ", ".join(t.__name__ for t in expected_type)
                if isinstance(expected_type, tuple)
                else expected_type.__name__
            )
            self.add_error(path, f"must be {names}")
            return False
        return True

    def validate(self) -> None:
        for key in REQUIRED_TOP_LEVEL_KEYS:
            self.require_key(self.manifest, key, "manifest")

        schema_identifier = self.manifest.get("schema_identifier")
        if isinstance(schema_identifier, str):
            if not schema_identifier.strip():
                self.add_error("manifest.schema_identifier", "must be a non-empty string")
        elif schema_identifier is not None:
            self.add_error("manifest.schema_identifier", "must be a string")

        # Backward compatibility guard.
        if "schema" in self.manifest and self.manifest.get("schema") != schema_identifier:
            self.add_error(
                "manifest.schema",
                "must match manifest.schema_identifier when both keys are present",
            )

        pages = self.manifest.get("pages")
        if isinstance(pages, dict):
            self._validate_pages(pages)

        machine = self.manifest.get("machine")
        if isinstance(machine, dict):
            self._validate_machine(machine, "manifest.machine")

        # Backward compatibility for older manifest shape.
        machine_surfaces = self.manifest.get("machine_surfaces")
        if isinstance(machine_surfaces, dict):
            self._validate_machine(machine_surfaces, "manifest.machine_surfaces")

        if self.errors:
            details = "\n".join(f"- {entry}" for entry in self.errors)
            raise ManifestValidationError(
                "Manifest schema validation failed with actionable paths:\n"
                f"{details}\n"
                "Fix the key paths above in assets/docs/manifest.json and rerun scripts/render_manifest.py."
            )

    def _validate_pages(self, pages: dict[str, Any]) -> None:
        if not pages:
            self.add_error("manifest.pages", "must include at least one page")
            return

        for page_key, page in pages.items():
            base_path = f"manifest.pages.{page_key}"
            if not self.require_type(page, dict, base_path):
                continue

            file_value = self.require_key(page, "file", base_path)
            if file_value is not None and not self.require_type(file_value, str, f"{base_path}.file"):
                continue

            template_value = self.require_key(page, "template", base_path)
            if not isinstance(template_value, str):
                if template_value is not None:
                    self.add_error(f"{base_path}.template", "must be a string")
                continue

            if template_value in PAGE_TEMPLATES_WITH_CONTENT:
                self.require_key(page, "title", base_path)
                content = self.require_key(page, "content", base_path)
                if isinstance(content, dict):
                    has_main_html = False
                    has_sections = False

                    if "main_html" in content:
                        main_html = self.require_key(content, "main_html", f"{base_path}.content")
                        if main_html is not None:
                            has_main_html = self.require_type(main_html, str, f"{base_path}.content.main_html")

                    if "sections" in content:
                        sections = self.require_key(content, "sections", f"{base_path}.content")
                        if sections is not None and self.require_type(sections, list, f"{base_path}.content.sections"):
                            has_sections = True
                            for idx, section in enumerate(sections):
                                section_path = f"{base_path}.content.sections[{idx}]"
                                if not self.require_type(section, dict, section_path):
                                    continue
                                section_id = self.require_key(section, "id", section_path)
                                if section_id is not None:
                                    self.require_type(section_id, str, f"{section_path}.id")
                                section_html = self.require_key(section, "html", section_path)
                                if section_html is not None:
                                    self.require_type(section_html, str, f"{section_path}.html")
                                if "enabled" in section:
                                    self.require_type(section["enabled"], bool, f"{section_path}.enabled")

                    if not has_main_html and not has_sections:
                        self.add_error(
                            f"{base_path}.content",
                            "must provide either content.main_html or content.sections for template rendering",
                        )
                head = self.require_key(page, "head", base_path)
                if isinstance(head, dict):
                    stylesheets = self.require_key(head, "stylesheets", f"{base_path}.head")
                    if stylesheets is not None:
                        self.require_type(stylesheets, list, f"{base_path}.head.stylesheets")
                self.require_key(page, "shell", base_path)
            elif template_value in {"verbatim_document", "verbatim_fragment"}:
                source_html = self.require_key(page, "source_html", base_path)
                if source_html is not None:
                    self.require_type(source_html, str, f"{base_path}.source_html")
            else:
                self.add_error(f"{base_path}.template", f"unsupported template '{template_value}'")

    def _validate_machine(self, machine_surfaces: dict[str, Any], root_path: str) -> None:
        inpage = self.require_key(machine_surfaces, "inpage", root_path)
        pages = self.require_key(machine_surfaces, "pages", root_path)
        endpoint_maps = self.require_key(machine_surfaces, "endpoint_maps", root_path)

        inpage_ids: set[str] = set()
        page_hrefs: set[str] = set()

        if isinstance(inpage, dict):
            root = self.require_key(inpage, "root", f"{root_path}.inpage")
            if root is not None:
                self.require_type(root, str, f"{root_path}.inpage.root")

            blocks = self.require_key(inpage, "blocks", f"{root_path}.inpage")
            if isinstance(blocks, list):
                if not blocks:
                    self.add_error(f"{root_path}.inpage.blocks", "must include at least one block")
                for idx, block in enumerate(blocks):
                    path = f"{root_path}.inpage.blocks[{idx}]"
                    if not self.require_type(block, dict, path):
                        continue
                    block_id = self.require_key(block, "id", path)
                    if isinstance(block_id, str):
                        inpage_ids.add(block_id)
                    self.require_key(block, "source", path)
                    self.require_key(block, "injection_pattern", path)
                    self.require_key(block, "page", path)

        if isinstance(pages, dict):
            root = self.require_key(pages, "root", f"{root_path}.pages")
            if root is not None:
                self.require_type(root, str, f"{root_path}.pages.root")

            endpoints = self.require_key(pages, "endpoints", f"{root_path}.pages")
            if isinstance(endpoints, list):
                if not endpoints:
                    self.add_error(f"{root_path}.pages.endpoints", "must include at least one endpoint")
                for idx, endpoint in enumerate(endpoints):
                    path = f"{root_path}.pages.endpoints[{idx}]"
                    if not self.require_type(endpoint, dict, path):
                        continue
                    self.require_key(endpoint, "rel", path)
                    href = self.require_key(endpoint, "href", path)
                    if isinstance(href, str):
                        page_hrefs.add(href)
                    self.require_key(endpoint, "format", path)

        required_endpoint_map_keys = ("machine_index", "page_manifest", "llm_context")
        if isinstance(endpoint_maps, dict):
            for key in required_endpoint_map_keys:
                value = self.require_key(endpoint_maps, key, f"{root_path}.endpoint_maps")
                if isinstance(value, str):
                    if key != "llm_context" and value not in page_hrefs:
                        self.add_error(
                            f"{root_path}.endpoint_maps.{key}",
                            f"must reference an href listed in {root_path}.pages.endpoints",
                        )
                elif value is not None:
                    self.add_error(f"{root_path}.endpoint_maps.{key}", "must be a string")

            org_schema_id = endpoint_maps.get("organization_schema_id")
            if org_schema_id is not None and isinstance(org_schema_id, str):
                if org_schema_id not in inpage_ids:
                    self.add_error(
                        f"{root_path}.endpoint_maps.organization_schema_id",
                        f"must match one of {root_path}.inpage.blocks[*].id",
                    )
            elif org_schema_id is not None:
                self.add_error(
                    f"{root_path}.endpoint_maps.organization_schema_id",
                    "must be a string when provided",
                )


def load_manifest(manifest_path: Path) -> dict[str, object]:
    manifest = json.loads(manifest_path.read_text())
    if not isinstance(manifest, dict):
        raise ManifestValidationError("Manifest root must be a JSON object.")
    validator = _ManifestValidator(manifest)
    validator.validate()
    _validate_schema_upgrade_guard(manifest, manifest_path)
    return manifest


def _validate_schema_upgrade_guard(manifest: dict[str, object], manifest_path: Path) -> None:
    lock_path = manifest_path.with_name("manifest-schema.lock.json")
    if not lock_path.exists():
        raise ManifestValidationError(
            "Schema lock missing: assets/docs/manifest-schema.lock.json must exist to gate schema upgrades."
        )

    lock_payload = json.loads(lock_path.read_text())
    if not isinstance(lock_payload, dict):
        raise ManifestValidationError("manifest-schema.lock.json must be a JSON object.")

    locked_identifier = lock_payload.get("schema_identifier")
    if not isinstance(locked_identifier, str) or not locked_identifier.strip():
        raise ManifestValidationError("manifest-schema.lock.json.schema_identifier must be a non-empty string.")

    current_identifier = manifest.get("schema_identifier")
    if locked_identifier != current_identifier:
        raise ManifestValidationError(
            "Schema identifier changed without lock update.\n"
            "Before accepting a schema upgrade: run scripts/check_visible_dom_regression.py and "
            "scripts/check_machine_surface_diff.py, then update assets/docs/manifest-schema.lock.json."
        )
