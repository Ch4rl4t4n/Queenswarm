"""OpenAPI regression coverage for Phase 12.1 browser harness routes."""

from __future__ import annotations

from app.main import app


def test_phase12_openapi_contains_browser_harness_routes() -> None:
    schema = app.openapi()
    paths = schema.get("paths", {})
    assert "/api/v1/agents/browser-sessions" in paths
    assert "/api/v1/agents/browser-sessions/{browser_session_id}/actions" in paths
    assert "/api/v1/agents/browser-sessions/{browser_session_id}/approve" in paths
