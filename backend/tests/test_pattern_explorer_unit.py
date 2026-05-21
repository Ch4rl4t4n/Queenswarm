"""Unit tests for Pattern Explorer dashboard payload."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.application.services.pattern_explorer import build_pattern_explorer_payload


@pytest.mark.asyncio
async def test_build_pattern_explorer_payload_when_sessions_have_patterns_then_usage_tallies() -> None:
    """Aggregate unique pattern counts within rolling window."""

    tenant_id = uuid4()
    now = datetime.now(tz=UTC)
    row = SimpleNamespace(
        id=uuid4(),
        tenant_id=tenant_id,
        goal="Plan and research quarterly report",
        status="completed",
        started_at=now - timedelta(hours=2),
        context_summary={
            "agentic_patterns": {
                "primary": ["planning", "reflection", "rag"],
                "secondary": ["tool_use"],
                "all": ["planning", "reflection", "rag", "tool_use"],
                "forced_reflection": True,
                "rationale": ["baseline: planning + multi-agent + RAG + guardrails"],
                "router_version": "heuristic-v1",
            },
        },
    )

    class _FakeScalars:
        def __init__(self, items: list[object]) -> None:
            self._items = items

        def all(self) -> list[object]:
            return self._items

    class _FakeSession:
        async def scalars(self, _stmt):  # noqa: ANN001
            return _FakeScalars([row])

    payload = await build_pattern_explorer_payload(_FakeSession(), tenant_id=tenant_id, window_hours=24)
    assert payload["unique_patterns_today"] == 4
    assert payload["sessions_in_window"] == 1
    assert payload["recent_sessions"][0]["rationale"]
    assert "planning" in payload["recent_sessions"][0]["all"]


@pytest.mark.asyncio
async def test_build_pattern_explorer_payload_when_no_sessions_then_empty_usage() -> None:
    """Return zero usage when tenant has no patterned sessions."""

    class _FakeScalars:
        def all(self) -> list[object]:
            return []

    class _FakeSession:
        async def scalars(self, _stmt):  # noqa: ANN001
            return _FakeScalars()

    payload = await build_pattern_explorer_payload(_FakeSession(), tenant_id=uuid4())
    assert payload["unique_patterns_today"] == 0
    assert payload["recent_sessions"] == []
    assert len(payload["catalog"]) >= 19
