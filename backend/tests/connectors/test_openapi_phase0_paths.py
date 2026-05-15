"""OpenAPI regressions tracked during Phase 0 stabilization."""

from __future__ import annotations

from app.main import app


def test_openapi_includes_dashboard_me_and_connectors() -> None:
    """Auth session + Phase 0 connector routes stay discoverable."""

    paths = app.openapi().get("paths") or {}
    assert "/api/v1/auth/me" in paths
    assert "/api/v1/auth/me/password" in paths
    assert "/api/v1/agents/sessions" in paths
    assert "/api/v1/agents/sessions/{session_id}/events" in paths
    assert "/api/v1/agents/sessions/{session_id}/review" in paths
    assert "/api/v1/agents/routines" in paths
    assert "/api/v1/agents/routines/{routine_id}/trigger" in paths
    assert "/api/v1/connectors/catalog" in paths
