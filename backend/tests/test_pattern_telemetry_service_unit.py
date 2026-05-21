"""Unit tests for agentic pattern success telemetry."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.application.services.pattern_telemetry_service import build_pattern_telemetry


@pytest.mark.asyncio
async def test_build_pattern_telemetry_when_completed_sessions_then_success_rates() -> None:
    """Patterns on completed sessions produce success rate percentages."""

    tenant_id = uuid4()
    now = datetime.now(tz=UTC)
    row = SimpleNamespace(
        id=uuid4(),
        tenant_id=tenant_id,
        status="completed",
        started_at=now - timedelta(hours=1),
        context_summary={
            "agentic_patterns": {
                "all": ["planning", "reflection", "rag"],
                "primary": ["planning", "reflection"],
            },
        },
    )

    class _FakeSession:
        async def scalars(self, _stmt):  # noqa: ANN001
            return [row]

    payload = await build_pattern_telemetry(_FakeSession(), tenant_id=tenant_id, window_hours=24)
    assert payload["sessions_analyzed"] == 1
    assert payload["patterns_tracked"] == 3
    top = payload["top_patterns"]
    assert top[0]["success_rate_pct"] == 100.0
    assert top[0]["label"] == "Planning"


@pytest.mark.asyncio
async def test_build_pattern_telemetry_when_no_patterned_sessions_then_empty() -> None:
    """Return empty top_patterns when no finalized patterned sessions exist."""

    class _FakeSession:
        async def scalars(self, _stmt):  # noqa: ANN001
            return []

    payload = await build_pattern_telemetry(_FakeSession(), tenant_id=uuid4())
    assert payload["sessions_analyzed"] == 0
    assert payload["top_patterns"] == []
