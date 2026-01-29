"""Admin data environment routes."""
from __future__ import annotations

from flask import Blueprint, current_app, jsonify

from authz import require_root_admin
from core.data_env.errors import DataEnvError, DataEnvResourceNotFound


admin_data_env_bp = Blueprint("admin_data_env", __name__)


def _repo():
    repo = current_app.extensions.get("data_env")
    if not repo:
        return None, (jsonify({"error": "data_env_unavailable"}), 500)
    return repo, None


@admin_data_env_bp.get("/admin/data-env/resources")
@require_root_admin
def data_env_resources():
    repo, error = _repo()
    if error:
        return error
    return jsonify({"resources": repo.list_resources()}), 200


@admin_data_env_bp.get("/admin/data-env/resource/<resource_id>")
@require_root_admin
def data_env_resource(resource_id: str):
    repo, error = _repo()
    if error:
        return error
    try:
        resource = repo.get_resource(resource_id)
    except DataEnvResourceNotFound:
        return jsonify({"error": "resource_not_found"}), 404
    except DataEnvError:
        return jsonify({"error": "data_env_error"}), 500
    return jsonify({"resource_id": resource_id, "resource": resource}), 200


@admin_data_env_bp.get("/admin/platform/mss")
@require_root_admin
def data_env_platform_mss():
    repo, error = _repo()
    if error:
        return error
    return jsonify(repo.get_platform_mss()), 200


@admin_data_env_bp.get("/admin/platform/manifest")
@require_root_admin
def data_env_platform_manifest():
    repo, error = _repo()
    if error:
        return error
    return jsonify(repo.get_platform_manifest()), 200


@admin_data_env_bp.get("/admin/platform/local")
@require_root_admin
def data_env_platform_local():
    repo, error = _repo()
    if error:
        return error
    return jsonify(repo.get_platform_local()), 200

