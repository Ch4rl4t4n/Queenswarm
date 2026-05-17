"""OpenAPI regression coverage for Phase 11.2 routes."""

from __future__ import annotations

from app.main import app


def test_phase11_openapi_contains_memory_evolution_routes() -> None:
    schema = app.openapi()
    paths = schema.get("paths", {})
    assert "/api/v1/hive-mind/memory-evolution/run" in paths
    assert "/api/v1/hive-mind/memory-evolution/proposals" in paths
    assert "/api/v1/hive-mind/memory-evolution/proposals/{proposal_id}/approve" in paths
    assert "/api/v1/hive-mind/memory-evolution/proposals/{proposal_id}/reject" in paths
    assert "/api/v1/agents/suggestions" in paths
    assert "/api/v1/agents/suggestions/{suggestion_id}/review" in paths
    assert "/api/v1/agents/sessions/autonomy/summary" in paths
