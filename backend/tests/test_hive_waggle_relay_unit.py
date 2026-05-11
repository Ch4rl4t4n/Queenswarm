"""Pure logic tests for hive waggle→swarm_events fan-out mapping."""

from __future__ import annotations

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
