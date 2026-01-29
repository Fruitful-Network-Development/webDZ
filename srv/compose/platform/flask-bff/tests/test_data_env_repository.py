from pathlib import Path

import pytest

from adapters.filesystem_json.repository import FilesystemJsonDataEnvRepository
from core.data_env.errors import DataEnvResourceNotFound, DataEnvValidationError


FIXTURE_ROOT = Path(__file__).resolve().parent / "fixtures" / "data_env"


def test_repository_loads_resources():
    repo = FilesystemJsonDataEnvRepository(FIXTURE_ROOT)
    resources = repo.list_resources()
    assert "platform.mss" in resources
    assert "platform.local" in resources
    assert "platform.manifest" in resources
    assert "platform.fnd" in resources

    mss = repo.get_platform_mss()
    assert mss["msn_id"] == "platform"
    assert mss["entity_type"] == "legal_entity"
    assert mss["exposed"] == ["5_2"]

    local = repo.get_platform_local()
    assert any(entry["local_id"] == "5_2" for entry in local)

    manifest = repo.get_platform_manifest()
    assert manifest[0]["archetype"] == "5_1"


def test_find_by_local_id():
    repo = FilesystemJsonDataEnvRepository(FIXTURE_ROOT)
    entry = repo.find_by_local_id("5_2")
    assert entry == {"local_id": "5_2", "title": "administrative_division_table"}


def test_get_resource_missing():
    repo = FilesystemJsonDataEnvRepository(FIXTURE_ROOT)
    with pytest.raises(DataEnvResourceNotFound):
        repo.get_resource("missing")


def test_manifest_validation(tmp_path):
    (tmp_path / "platform.profile.json").write_text(
        '{"platform_mss":"mss","platform_fnd":"fnd","platform_manifest":"manifest","platform_local":"local"}'
    )
    (tmp_path / "platform.mss.json").write_text(
        '{"mss":{"msn_id":"platform","entity_type":"legal_entity","exposed":[]}}'
    )
    (tmp_path / "platform.fnd.json").write_text(
        '{"fnd":{"msn_id":"platform","root":"frontend","root_entry":"index.html"}}'
    )
    (tmp_path / "platform.local.json").write_text(
        '{"local":[{"local_id":"1","title":"root"}]}'
    )
    (tmp_path / "platform.manifest.json").write_text(
        '{"manifest":[{"archetype":"5_1","column_count":"3"}]}'
    )
    with pytest.raises(DataEnvValidationError):
        FilesystemJsonDataEnvRepository(tmp_path)

