"""Pure logic tests for hive waggle→swarm_events fan-out mapping."""

from __future__ import annotations

import pytest

from app.services.hive_waggle_relay import (
    HIVE_SYNC_HINT_EVENT,
    build_hive_sync_hint_event,
)


def test_hint_suppressed_when_dance_type_mismatches_pulse() -> None:
    raw = {
        "dance_type": "other",
        "swarm_id": "s",
        "payload": {"needs_global_sync": True},
    }
    assert build_hive_sync_hint_event(raw) is None


def test_hint_requires_payload_dict_with_positive_sync_need() -> None:
    pulse = {"dance_type": "sub_swarm_workflow_pulse", "swarm_id": "sx", "payload": "oops"}
    assert build_hive_sync_hint_event(pulse) is None
    vague = {"dance_type": "sub_swarm_workflow_pulse", "swarm_id": "sx", "payload": {}}
    assert build_hive_sync_hint_event(vague) is None


def test_hint_escalates_on_sync_need_with_telemetry() -> None:
    raw = {
        "dance_type": "sub_swarm_workflow_pulse",
        "swarm_id": "abc",
        "workflow_id": "wf",
        "task_id": "tk",
        "payload": {"needs_global_sync": True, "steps_reported": 3, "error": None},
    }
    mapped = build_hive_sync_hint_event(raw)
    assert mapped is not None
    assert mapped["event"] == HIVE_SYNC_HINT_EVENT
    assert mapped["swarm_id"] == "abc"
    assert mapped["telemetry_subset"]["steps_reported"] == 3


@pytest.mark.asyncio
async def test_relay_loop_publishes_hint_and_handles_cancel() -> None:
    from unittest.mock import AsyncMock, patch

    import asyncio

    from app.services.hive_waggle_relay import run_hive_waggle_relay_loop

    waggle = {
        "dance_type": "sub_swarm_workflow_pulse",
        "swarm_id": "s1",
        "payload": {"needs_global_sync": True},
    }

    async def fake_subscribe(_channel: str):
        yield waggle
        await asyncio.sleep(3600)

    with (
        patch("app.services.hive_waggle_relay.subscribe_channel", side_effect=fake_subscribe),
        patch("app.services.hive_waggle_relay.publish_event", new_callable=AsyncMock) as publish,
    ):
        task = asyncio.create_task(run_hive_waggle_relay_loop())
        await asyncio.sleep(0.05)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    publish.assert_awaited()
