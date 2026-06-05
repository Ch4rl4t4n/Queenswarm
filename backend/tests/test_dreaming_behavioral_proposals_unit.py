"""Dreaming behavioral proposals unit tests."""

from __future__ import annotations

import uuid
from types import SimpleNamespace

import pytest

from app.application.services.dreaming_behavioral_proposals import (
    _extract_proposals_from_briefing,
    apply_behavioral_proposals,
    compose_dreaming_behavioral_snapshot,
)


def test_extract_proposals_from_stalled_briefing() -> None:
    md = "# Report\n\nStalled signals: 2\n\nAlways prioritize triage before live publish."
    props = _extract_proposals_from_briefing(md)
    assert len(props) >= 1


@pytest.mark.asyncio
async def test_compose_dreaming_behavioral_empty_when_no_batch() -> None:
    from unittest.mock import AsyncMock

    session = AsyncMock()
    session.scalar = AsyncMock(return_value=None)
    snap = await compose_dreaming_behavioral_snapshot(session, tenant_id=uuid.uuid4())
    assert snap.enabled is True
    assert snap.proposals == []


@pytest.mark.asyncio
async def test_apply_behavioral_proposals_appends_instructions(monkeypatch) -> None:
    from unittest.mock import AsyncMock

    tenant_id = uuid.uuid4()
    batch = SimpleNamespace(
        id=uuid.uuid4(),
        briefing_md="Always use simulate-first before Gumroad publish.",
        status="completed",
    )

    session = AsyncMock()
    session.scalar = AsyncMock(return_value=batch)

    class FakeCurated:
        version = 1

        def __init__(self) -> None:
            self.content_md = "=== BEHAVIORAL ===\nBase prefs."

        async def get(self, _tenant_id, _kind):
            return SimpleNamespace(content_md=self.content_md, version=1)

        async def upsert(self, _tenant_id, _kind, content_md, user_id=None):
            self.content_md = content_md
            return SimpleNamespace(version=2)

    fake = FakeCurated()
    monkeypatch.setattr(
        "app.application.services.curated_memory_service.CuratedMemoryService",
        lambda db: fake,
    )

    result = await apply_behavioral_proposals(
        session,
        tenant_id=tenant_id,
        proposal_ids=["proposal-0"],
    )
    assert result.applied == 1
    assert "qs-nightly-learning" in fake.content_md
    assert "simulate-first" in fake.content_md.lower()
