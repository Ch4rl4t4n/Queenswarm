"""OpenAPI coverage for Phase 6 durable sub-agent job routes."""

from __future__ import annotations

from app.main import app


def test_phase6_openapi_contains_sub_agent_job_route() -> None:
    """Agents router exposes Celery job poll endpoint for durable sub-agent steps."""

    paths = app.openapi().get("paths") or {}
    assert "/api/v1/agents/sessions/{session_id}/sub-agents/{sub_agent_id}/job" in paths
    assert "/api/v1/agents/sessions/{session_id}/sub-agents/{sub_agent_id}/retry" in paths
    assert "/api/v1/agents/sessions/{session_id}/audit-logs" in paths
    assert "/api/v1/agents/sessions/{session_id}/audit-logs/export" in paths
    assert "/api/v1/agents/sessions/{session_id}/context-history" in paths
    assert "/api/v1/agents/sessions/{session_id}/report/export" in paths
