"""Unit tests for Mission Home snapshot (Track Q UX2)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest

from app.application.services.mission_home_service import (
    MissionLifeOsStripOut,
    MissionMemoryStripOut,
    PROCESS_STEPS,
    STEP_STUDIOS,
    _brief_bullets_from_morning,
    _compose_life_os_strip,
    _compose_memory_strip,
    _loop_progress_from_lanes,
    _resolve_process_step,
    compose_mission_home_snapshot,
)
from app.domain.memory.curated import CuratedFileKind
from app.application.services.solo_operator_first_run import SoloFirstRunOut


def test_resolve_process_step_setup_when_first_run_incomplete() -> None:
    step = _resolve_process_step(
        first_run_complete=False,
        approval_count=0,
        active_sessions=[],
        has_daily_plan=True,
    )
    assert step == "setup"


def test_resolve_process_step_verify_when_approvals_pending() -> None:
    step = _resolve_process_step(
        first_run_complete=True,
        approval_count=2,
        active_sessions=[],
        has_daily_plan=False,
    )
    assert step == "verify"


def test_loop_progress_from_lanes() -> None:
    from app.application.services.parallel_hive_view import ParallelBeeLaneOut

    lanes = [
        ParallelBeeLaneOut(lane_id="a", label="Research", status="completed"),
        ParallelBeeLaneOut(lane_id="b", label="Critic", status="running"),
    ]
    pct, chip = _loop_progress_from_lanes(status="running", lanes=lanes)
    assert pct == 50
    assert chip == "Work · 50%"

    verify_pct, verify_chip = _loop_progress_from_lanes(status="needs_input", lanes=lanes)
    assert verify_chip == "Verify"
    assert verify_pct >= 50


def test_brief_bullets_from_morning_sections() -> None:
    bullets = _brief_bullets_from_morning(
        {
            "sections": [
                {"label": "Life OS", "excerpt": "Calendar triage complete.", "binding": "bound"},
                {"label": "Content", "binding": "missing"},
            ],
            "tech_health_score": 0.82,
        },
    )
    assert len(bullets) >= 2
    assert "Life OS" in bullets[0].text


@pytest.mark.asyncio
async def test_compose_mission_home_disabled_when_solo_off() -> None:
    session = AsyncMock()
    with patch("app.application.services.mission_home_service.settings") as mock_settings:
        mock_settings.solo_mode_enabled = False
        mock_settings.operator_loop_enabled = False
        snapshot = await compose_mission_home_snapshot(
            session,
            tenant_id=uuid.uuid4(),
            dashboard_user_id=uuid.uuid4(),
            tenant=None,
        )
    assert snapshot.enabled is False
    assert snapshot.process_steps == PROCESS_STEPS


@pytest.mark.asyncio
async def test_compose_memory_strip_empty_layers() -> None:
    session = AsyncMock()
    tenant_id = uuid.uuid4()

    with patch(
        "app.application.services.mission_home_service.CuratedMemoryService",
    ) as svc_cls:
        svc = svc_cls.return_value
        svc.get_bundle = AsyncMock(
            return_value={
                CuratedFileKind.SOUL: "",
                CuratedFileKind.SKILLS_HIERARCHY: "",
                CuratedFileKind.MISSION: "",
                CuratedFileKind.IDEAL_STATE: "",
                CuratedFileKind.INSTRUCTIONS: "",
            },
        )
        with patch(
            "app.application.services.mission_home_service.CuratedMemoryService.max_chars_per_file",
            return_value=16000,
        ):
            strip = await _compose_memory_strip(session, tenant_id=tenant_id)

    assert len(strip.layers) == 3
    assert strip.layers[0].id == "soul"
    assert strip.layers[0].filled is False
    assert "Empty" in strip.layers[0].preview


@pytest.mark.asyncio
async def test_step_studios_for_setup() -> None:
    assert STEP_STUDIOS["setup"][0].id == "llm_keys"
    assert len(STEP_STUDIOS["verify"]) >= 1


@pytest.mark.asyncio
async def test_compose_mission_home_setup_step() -> None:
    session = AsyncMock()
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    now = datetime.now(tz=UTC)

    first_run = SoloFirstRunOut(
        enabled=True,
        complete=False,
        progress_pct=33,
        generated_at=now,
        steps=[],
    )
    morning = {"sections": [], "tech_health_score": 0.9}
    daily = type(
        "Daily",
        (),
        {"enabled": True, "items": []},
    )()
    inbox = type(
        "Inbox",
        (),
        {"enabled": True, "counts": type("C", (), {"total": 0})(), "items": []},
    )()
    parallel = type("Parallel", (), {"sessions": []})()
    memory_strip = MissionMemoryStripOut()
    life_os_strip = MissionLifeOsStripOut(enabled=True, connected=False, message="Connect Google Calendar")

    with patch("app.application.services.mission_home_service.settings") as mock_settings:
        mock_settings.solo_mode_enabled = True
        mock_settings.operator_loop_enabled = True
        mock_settings.rapid_loop_mission_home_enabled = True
        mock_settings.revenue_funnel_mission_home_enabled = False
        mock_settings.factory_launch_mission_home_enabled = False
        mock_settings.catalog_wave_mission_home_enabled = False
        mock_settings.sub_swarm_fleet_mission_home_enabled = False
        with patch(
            "app.application.services.mission_home_service.compose_solo_first_run",
            AsyncMock(return_value=first_run),
        ):
            with patch(
                "app.application.services.mission_home_service.compose_morning_hive_brief",
                AsyncMock(return_value=morning),
            ):
                with patch(
                    "app.application.services.mission_home_service.compose_solo_daily_plan",
                    AsyncMock(return_value=daily),
                ):
                    with patch(
                        "app.application.services.mission_home_service.compose_approval_inbox_snapshot",
                        AsyncMock(return_value=inbox),
                    ):
                        with patch(
                            "app.application.services.mission_home_service.compose_parallel_hive_view_snapshot",
                            AsyncMock(return_value=parallel),
                        ):
                            with patch(
                                "app.application.services.mission_home_service._compose_memory_strip",
                                AsyncMock(return_value=memory_strip),
                            ):
                                with patch(
                                    "app.application.services.mission_home_service._compose_life_os_strip",
                                    AsyncMock(return_value=life_os_strip),
                                ):
                                    snapshot = await compose_mission_home_snapshot(
                                        session,
                                        tenant_id=tenant_id,
                                        dashboard_user_id=user_id,
                                        tenant=None,
                                    )

    assert snapshot.enabled is True
    assert snapshot.current_step == "setup"
    assert snapshot.first_run_complete is False
    assert snapshot.rapid_loop_widget_enabled is True
    assert len(snapshot.brief_bullets) >= 1
    assert snapshot.step_studios[0].id == "llm_keys"


@pytest.mark.asyncio
async def test_compose_life_os_strip_disabled() -> None:
    session = AsyncMock()
    with patch("app.application.services.mission_home_service.settings") as mock_settings:
        mock_settings.calendar_daily_planner_enabled = False
        strip = await _compose_life_os_strip(session, dashboard_user_id=uuid.uuid4())

    assert strip.enabled is False
    assert "disabled" in strip.message.lower()


@pytest.mark.asyncio
async def test_compose_life_os_strip_maps_calendar_events() -> None:
    session = AsyncMock()
    now = datetime.now(tz=UTC)
    calendar = type(
        "Cal",
        (),
        {
            "enabled": True,
            "connected": True,
            "event_count": 1,
            "message": "1 upcoming event(s).",
            "items": [
                type(
                    "Item",
                    (),
                    {
                        "id": "cal_abc",
                        "title": "Focus block",
                        "start_at": now,
                        "end_at": None,
                        "detail": "Deep work",
                        "href": "/integrations?tab=connectors",
                    },
                )(),
            ],
        },
    )()

    with patch("app.application.services.mission_home_service.settings") as mock_settings:
        mock_settings.calendar_daily_planner_enabled = True
        with patch(
            "app.application.services.calendar_daily_planner.compose_calendar_daily_planner",
            AsyncMock(return_value=calendar),
        ):
            strip = await _compose_life_os_strip(session, dashboard_user_id=uuid.uuid4())

    assert strip.enabled is True
    assert strip.connected is True
    assert len(strip.events) == 1
    assert strip.events[0].title == "Focus block"
