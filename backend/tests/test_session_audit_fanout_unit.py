"""Unit tests for supervisor session audit live fan-out."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock

import pytest

from app.application.services.supervisor import session_audit_fanout as fanout


@pytest.mark.asyncio
async def test_publish_supervisor_session_audit_event_when_local_hook_set_then_delivers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Publish helper delivers locally and attempts Redis fan-out."""

    session_id = uuid.uuid4()
    tenant_id = uuid.uuid4()
    delivered: list[dict[str, object]] = []

    async def _local(_session_id: uuid.UUID, payload: dict[str, object]) -> None:
        delivered.append({"session_id": str(_session_id), **payload})

    monkeypatch.setattr(fanout, "deliver_supervisor_session_audit_local", _local)
    monkeypatch.setattr(fanout, "publish_event", AsyncMock())

    entry = {"id": "audit-1", "action": "supervisor_session_control"}
    await fanout.publish_supervisor_session_audit_event(
        session_id=session_id,
        tenant_id=tenant_id,
        entry=entry,
    )

    assert len(delivered) == 1
    assert delivered[0]["type"] == "supervisor_session.audit"
    assert delivered[0]["entry"] == entry
