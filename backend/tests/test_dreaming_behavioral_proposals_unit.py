"""Dreaming behavioral proposals unit tests."""

from __future__ import annotations

import uuid
from types import SimpleNamespace

import pytest

from app.application.services.dreaming_behavioral_proposals import (
    _extract_proposals_from_briefing,
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
