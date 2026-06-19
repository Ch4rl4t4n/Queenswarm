"""Unit tests for ST6 strategic/AFK Mission Home split."""

from __future__ import annotations

from app.application.services.mission_home_service import (
    MissionActionOut,
    MissionActiveSessionOut,
    _compose_strategic_afk_split,
)


def test_compose_strategic_afk_split_limits_items() -> None:
    actions = [
        MissionActionOut(id=f"a{i}", title=f"Action {i}", detail="", href="/tasks", priority=i + 1)
        for i in range(5)
    ]
    sessions = [
        MissionActiveSessionOut(
            session_id=f"s{i}",
            goal=f"Lane digest {i}",
            status="running",
            progress_label="1/2",
            href=f"/agents?session={i}",
        )
        for i in range(3)
    ]
    strategic, afk = _compose_strategic_afk_split(enabled=True, next_actions=actions, active_sessions=sessions)
    assert len(strategic.items) == 3
    assert afk.enabled is True
    assert len(afk.sessions) == 3
