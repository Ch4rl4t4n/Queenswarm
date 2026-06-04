"""Unit tests for session learnings distill."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.application.services.session_learnings_distill import distill_session_learnings_to_curated_memory


@pytest.mark.asyncio
async def test_distill_skips_skill_factory_sessions() -> None:
    db = AsyncMock()
    session = MagicMock()
    session.tenant_id = uuid.uuid4()
    session.id = uuid.uuid4()
    session.context_summary = {"skill_factory": True}
    session.goal = "Skill Factory build"

    ok = await distill_session_learnings_to_curated_memory(db, session=session)
    assert ok is False
    db.scalar.assert_not_called()
