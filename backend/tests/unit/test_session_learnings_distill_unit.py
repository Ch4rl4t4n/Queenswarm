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


@pytest.mark.asyncio
async def test_distill_skips_without_verified_approve() -> None:
    db = AsyncMock()
    session = MagicMock()
    session.tenant_id = uuid.uuid4()
    session.id = uuid.uuid4()
    session.context_summary = {"approval_state": "pending"}
    session.goal = "Routine digest"

    ok = await distill_session_learnings_to_curated_memory(db, session=session)
    assert ok is False


@pytest.mark.asyncio
async def test_distill_allowed_when_verified_distill_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    db = AsyncMock()
    session = MagicMock()
    session.tenant_id = uuid.uuid4()
    session.id = uuid.uuid4()
    session.context_summary = {"verified_distill": True, "raw_goal": "Digest"}
    session.goal = "Digest"

    sub = MagicMock()
    sub.role = "researcher"
    sub.status = "completed"
    sub.short_memory = {"last_summary": "x" * 120}
    sub.last_output = ""
    sub.spawn_order = 1

    async def _scalars(_stmt):  # noqa: ANN001
        result = MagicMock()
        result.all.return_value = [sub]
        return result

    db.scalars = _scalars  # type: ignore[method-assign]

    class _FakeCuratedService:
        def __init__(self, *, db: AsyncMock) -> None:
            self.db = db

        async def get(self, *_args, **_kwargs):  # noqa: ANN002, ANN003
            return None

        async def upsert(self, **_kwargs):  # noqa: ANN003
            return MagicMock(version=2, char_count=500)

    monkeypatch.setattr(
        "app.application.services.session_learnings_distill.CuratedMemoryService",
        _FakeCuratedService,
    )

    ok = await distill_session_learnings_to_curated_memory(db, session=session)
    assert ok is True
