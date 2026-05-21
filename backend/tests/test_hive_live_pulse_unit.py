"""Tests for hive live WebSocket pulse deltas."""

from __future__ import annotations

import uuid

from app.application.services.hive_live_pulse import HiveAgentDelta


def test_hive_agent_delta_serializes_uuid_as_string() -> None:
    agent_id = uuid.uuid4()
    row = HiveAgentDelta(
        id=agent_id,
        status="running",
        pollen_points=12.5,
        performance_score=0.75,
        current_task_title="Verify recipe",
        hive_tier="worker",
    )
    dumped = row.model_dump(mode="json")
    assert dumped["id"] == str(agent_id)
    assert dumped["status"] == "running"
    assert dumped["hive_tier"] == "worker"


def test_hive_agent_delta_allows_empty_task_hint() -> None:
    row = HiveAgentDelta(
        id=uuid.uuid4(),
        status="idle",
        pollen_points=0.0,
        performance_score=0.0,
    )
    dumped = row.model_dump(mode="json")
    assert dumped["current_task_id"] is None
    assert dumped["current_task_title"] is None
