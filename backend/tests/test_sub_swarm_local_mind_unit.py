"""Tests for sub-swarm local hive mind projections."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.application.services.sub_swarm_local_mind import build_local_mind_detail, build_local_mind_summary
from app.infrastructure.persistence.models.enums import SwarmPurpose
from app.infrastructure.persistence.models.swarm import SubSwarm


def test_build_local_mind_summary_when_never_synced_then_needs_sync() -> None:
    swarm = SubSwarm(
        name="colony-scout",
        purpose=SwarmPurpose.SCOUT,
        local_memory={"wizard_template": "exec-assistant", "hive_ui": {"accent_hex": "#FFB800"}},
    )
    summary = build_local_mind_summary(swarm)
    assert summary["needs_sync"] is True
    assert summary["wizard_template"] == "exec-assistant"
    assert summary["sync_progress_pct"] == 100


def test_build_local_mind_summary_when_recent_sync_then_counts_down(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.application.services.sub_swarm_local_mind.settings.hive_sync_interval_sec", 300)
    now = datetime(2026, 5, 21, 12, 0, 0, tzinfo=UTC)
    swarm = SubSwarm(
        name="colony-eval",
        purpose=SwarmPurpose.EVAL,
        local_memory={"last_waggle": {"cue": "handoff to sim"}},
        last_global_sync_at=now - timedelta(seconds=60),
    )
    summary = build_local_mind_summary(swarm, now=now)
    assert summary["needs_sync"] is False
    assert summary["sync_due_in_sec"] == 240
    assert summary["last_waggle_cue"] == "handoff to sim"


def test_build_local_mind_detail_includes_preview() -> None:
    swarm = SubSwarm(
        name="wizard-colony",
        purpose=SwarmPurpose.ACTION,
        local_memory={"goals": ["Ship weekly digest"], "secret_key": "hidden"},
        member_count=4,
        is_active=True,
    )
    detail = build_local_mind_detail(swarm)
    assert detail["goal_preview"] == "Ship weekly digest"
    assert "secret_key" not in detail["local_memory_preview"]
