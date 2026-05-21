"""Unit coverage for Redis waggle-dance broadcast helper."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from redis.exceptions import RedisError

from app.core.redis_client import CHANNEL_WAGGLE_DANCE
from app.services.waggle_dance import broadcast_waggle_dance


@pytest.mark.asyncio
async def test_broadcast_waggle_dance_publishes_full_event() -> None:
    swarm_id = uuid.uuid4()
    workflow_id = uuid.uuid4()
    task_id = uuid.uuid4()

    with patch("app.services.waggle_dance.publish_event", new_callable=AsyncMock) as publish:
        await broadcast_waggle_dance(
            dance_type="sub_swarm_workflow_batch",
            swarm_id=swarm_id,
            workflow_id=workflow_id,
            task_id=task_id,
            payload={"batch": 2},
        )

    publish.assert_awaited_once_with(
        CHANNEL_WAGGLE_DANCE,
        {
            "dance_type": "sub_swarm_workflow_batch",
            "swarm_id": str(swarm_id),
            "workflow_id": str(workflow_id),
            "task_id": str(task_id),
            "payload": {"batch": 2},
        },
    )


@pytest.mark.asyncio
async def test_broadcast_waggle_dance_swallows_redis_errors() -> None:
    swarm_id = uuid.uuid4()

    with patch(
        "app.services.waggle_dance.publish_event",
        new_callable=AsyncMock,
        side_effect=RedisError("connection refused"),
    ):
        await broadcast_waggle_dance(dance_type="heartbeat", swarm_id=swarm_id)
