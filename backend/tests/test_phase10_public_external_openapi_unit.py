"""OpenAPI regression coverage for Phase 10.4 routes."""

from __future__ import annotations

from app.main import app


def test_phase10_openapi_contains_public_share_and_external_api_routes() -> None:
    schema = app.openapi()
    paths = schema.get("paths", {})
    assert "/api/v1/shares" in paths
    assert "/api/v1/shares/{share_id}" in paths
    assert "/api/v1/public/share/{share_token}" in paths
    assert "/api/v1/ext-api/v1/scope" in paths
    assert "/api/v1/ext-api/v1/projects/{project_slug}/run" in paths
