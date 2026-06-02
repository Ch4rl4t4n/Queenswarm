"""Unit tests for operator mission feed helpers."""

from __future__ import annotations

import json
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.application.services import operator_mission_feed as feed


@pytest.mark.asyncio
async def test_push_mission_feed_event_writes_to_redis(monkeypatch: pytest.MonkeyPatch) -> None:
    tenant_id = uuid.uuid4()
    redis = AsyncMock()
    redis.lpush = AsyncMock()
    redis.ltrim = AsyncMock()
    redis.expire = AsyncMock()

    async def _fake_get_redis():
        yield redis

    monkeypatch.setattr(feed, "get_redis", _fake_get_redis)
    await feed.push_mission_feed_event(
        tenant_id=tenant_id,
        kind="task_completed",
        title="Mission task completed",
        body="Landing page audit",
        href="/tasks?task=abc",
        entity_id="abc",
    )
    redis.lpush.assert_awaited_once()
    blob = redis.lpush.await_args.args[1]
    payload = json.loads(blob)
    assert payload["kind"] == "task_completed"
    assert payload["read"] is False


@pytest.mark.asyncio
async def test_list_mission_feed_events_parses_rows(monkeypatch: pytest.MonkeyPatch) -> None:
    tenant_id = uuid.uuid4()
    redis = AsyncMock()
    redis.lrange = AsyncMock(
        return_value=[
            json.dumps({"id": "e1", "title": "Done", "read": False}),
        ],
    )

    async def _fake_get_redis():
        yield redis

    monkeypatch.setattr(feed, "get_redis", _fake_get_redis)
    rows = await feed.list_mission_feed_events(tenant_id, limit=5)
    assert len(rows) == 1
    assert rows[0]["id"] == "e1"
