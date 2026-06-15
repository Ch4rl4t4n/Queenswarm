"""Unit tests for episodic memory timeline builder."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.application.services.episodic_memory_service import build_episodic_summary, build_episodic_timeline


@pytest.mark.asyncio
async def test_build_episodic_timeline_merges_sources() -> None:
    """Timeline includes session events and sorts reverse-chronologically."""

    tenant_id = uuid4()
    now = datetime.now(tz=UTC)
    session_id = uuid4()
    event = SimpleNamespace(
        id=uuid4(),
        tenant_id=tenant_id,
        supervisor_session_id=session_id,
        sub_agent_session_id=None,
        event_type="session_created",
        level="info",
        message="Supervisor session started.",
        occurred_at=now - timedelta(hours=1),
    )
    insight = SimpleNamespace(
        id=uuid4(),
        tenant_id=tenant_id,
        cycle_id=uuid4(),
        source_kind="supervisor_session",
        source_ref=str(session_id),
        summary="Consolidated learning from verified workflow.",
        confidence=0.82,
        created_at=now - timedelta(hours=2),
    )

    class _FakeSession:
        def __init__(self) -> None:
            self._calls = 0

        async def get(self, _model, _id):  # noqa: ANN001
            return None

        async def scalars(self, _stmt):  # noqa: ANN001
            self._calls += 1
            if self._calls == 1:
                return [event]
            if self._calls == 2:
                return [insight]
            return []

        async def scalar(self, _stmt):  # noqa: ANN001
            return 0

    payload = await build_episodic_timeline(_FakeSession(), tenant_id=tenant_id, retention_days=30, limit=20)
    assert payload["item_count"] >= 2
    kinds = {item["kind"] for item in payload["items"]}
    assert "session_event" in kinds
    assert "dream_insight" in kinds
    assert payload["items"][0]["occurred_at"] >= payload["items"][-1]["occurred_at"]


@pytest.mark.asyncio
async def test_build_episodic_summary_returns_counts() -> None:
    """Summary exposes per-source counters."""

    class _FakeSession:
        def __init__(self) -> None:
            self._scalar_calls = 0

        async def get(self, _model, _id):  # noqa: ANN001
            return None

        async def scalar(self, _stmt):  # noqa: ANN001
            self._scalar_calls += 1
            if self._scalar_calls == 5:
                return None
            return 3

    payload = await build_episodic_summary(_FakeSession(), tenant_id=uuid4(), retention_days=90)
    assert payload["retention_days"] == 90
    assert payload["counts"]["session_events"] == 3
    assert payload["total_items"] == 12
    assert payload["latest_at"] is None
