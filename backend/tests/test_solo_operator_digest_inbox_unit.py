"""Unit tests for four-lane digest inbox."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.application.services.solo_operator_digest_inbox import (
    compose_four_lane_digest_inbox,
    promote_digest_session_to_task,
)
from app.application.services.solo_operator_four_lanes import FOUR_LANE_PAYLOAD_KEY


def _routine(*, rid: uuid.UUID, lane: str, name: str = "lane") -> MagicMock:
    row = MagicMock()
    row.id = rid
    row.name = name
    row.context_payload = {FOUR_LANE_PAYLOAD_KEY: lane}
    return row


def _session(
    *,
    sid: uuid.UUID,
    routine_id: str,
    status: str = "needs_input",
    approval: str | None = None,
) -> MagicMock:
    row = MagicMock()
    row.id = sid
    row.tenant_id = uuid.uuid4()
    row.goal = "Four Lane · Najman marketing digest goal"
    row.status = status
    row.task_id = None
    row.swarm_id = None
    row.created_at = datetime.now(tz=UTC)
    row.context_summary = {"routine_id": routine_id}
    if approval:
        row.context_summary["approval_state"] = approval
    critic = MagicMock()
    critic.role = "critic"
    critic.last_output = "CZ digest excerpt for operator."
    row.sub_agents = [critic]
    return row


@pytest.mark.asyncio
async def test_compose_digest_inbox_when_lane_session_then_lists_item(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tenant_id = uuid.uuid4()
    routine_id = uuid.uuid4()
    session_id = uuid.uuid4()
    db = AsyncMock()

    async def _load(_db, *, tenant_id: uuid.UUID):  # noqa: ARG001
        return [_routine(rid=routine_id, lane="marketing_najman")]

    async def _scalars(_stmt):  # noqa: ANN001
        result = MagicMock()
        result.all.return_value = [
            _session(sid=session_id, routine_id=str(routine_id)),
        ]
        return result

    db.scalars = _scalars
    monkeypatch.setattr(
        "app.application.services.solo_operator_digest_inbox._load_tenant_routines",
        _load,
    )

    inbox = await compose_four_lane_digest_inbox(db, tenant_id=tenant_id, limit=10)
    assert inbox.pending_count == 1
    assert len(inbox.items) == 1
    assert inbox.items[0].lane_id == "marketing_najman"
    assert inbox.items[0].promote_ready is True


@pytest.mark.asyncio
async def test_promote_digest_when_missing_session_then_not_ok(monkeypatch: pytest.MonkeyPatch) -> None:
    db = AsyncMock()
    db.get = AsyncMock(return_value=None)
    result = await promote_digest_session_to_task(
        db,
        tenant_id=uuid.uuid4(),
        session_id=uuid.uuid4(),
        reviewer_subject="test",
    )
    assert result["ok"] is False
