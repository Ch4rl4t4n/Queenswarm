"""Unit tests for Mission Home snapshot (Track Q UX2)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest

from app.application.services.mission_home_service import (
    MissionActiveSessionOut,
    MissionAutopilotStripOut,
    MissionLifeOsStripOut,
    MissionMemoryStripOut,
    PROCESS_STEPS,
    STEP_STUDIOS,
    _brief_bullets_from_morning,
    _compose_agent_loop_strip,
    _compose_autopilot_strip,
    _compose_data_monitor_strip,
    _compose_discovery_strip,
    _compose_goldmine_strip,
    _compose_loop_guardrails_strip,
    _compose_social_intel_strip,
    _compose_life_os_strip,
    _compose_memory_strip,
    _compose_tool_outcome_strip,
    _loop_progress_from_lanes,
    _resolve_process_step,
    compose_mission_home_snapshot,
)
from app.application.services.agent_quality_scorecard_service import MissionAgentQualityStripOut
from app.application.services.weak_signal_bee_service import WeakSignalPreviewOut
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
    autopilot_strip = MissionAutopilotStripOut(enabled=True, routines_enabled=True, trio_bound=2)

    with patch("app.application.services.mission_home_service.settings") as mock_settings:
        mock_settings.solo_mode_enabled = True
        mock_settings.operator_loop_enabled = True
        mock_settings.rapid_loop_mission_home_enabled = True
        mock_settings.revenue_funnel_mission_home_enabled = False
        mock_settings.factory_launch_mission_home_enabled = False
        mock_settings.catalog_wave_mission_home_enabled = False
        mock_settings.sub_swarm_fleet_mission_home_enabled = False
        mock_settings.forager_goldmine_dispatch_enabled = False
        mock_settings.closed_loop_presets_enabled = False
        mock_settings.data_monitor_wizard_enabled = False
        mock_settings.forager_discovery_enabled = False
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
                                    with patch(
                                        "app.application.services.mission_home_service._compose_autopilot_strip",
                                        AsyncMock(return_value=autopilot_strip),
                                    ):
                                        with patch(
                                            "app.application.services.mission_home_service.compose_weak_signal_preview",
                                            AsyncMock(
                                                return_value=type(
                                                    "WS",
                                                    (),
                                                    {"advisor_hint": None},
                                                )(),
                                            ),
                                        ):
                                                with patch(
                                                    "app.application.services.mission_home_service.compose_agent_quality_strip",
                                                    AsyncMock(
                                                        return_value=MissionAgentQualityStripOut(
                                                            enabled=False,
                                                        ),
                                                    ),
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


@pytest.mark.asyncio
async def test_compose_autopilot_strip_disabled_when_routines_off() -> None:
    session = AsyncMock()
    with patch("app.application.services.mission_home_service.settings") as mock_settings:
        mock_settings.routines_enabled = False
        strip = await _compose_autopilot_strip(session, tenant_id=uuid.uuid4())

    assert strip.enabled is False
    assert strip.routines_enabled is False
    assert "disabled" in strip.message.lower()


@pytest.mark.asyncio
async def test_compose_autopilot_strip_maps_trio_and_four_lanes() -> None:
    session = AsyncMock()
    tenant_id = uuid.uuid4()

    trio = {
        "lanes_bound": 2,
        "lanes_total": 3,
        "lanes": [
            {
                "lane_id": "life_os",
                "label": "Life OS",
                "description": "Morning briefing",
                "binding": "context_payload",
                "routine_active": True,
            },
        ],
    }
    digest = type("Digest", (), {"pending_count": 2, "items": []})()

    with patch("app.application.services.mission_home_service.settings") as mock_settings:
        mock_settings.routines_enabled = True
        with patch(
            "app.application.services.solo_operator_trio.get_solo_trio_status",
            AsyncMock(return_value=trio),
        ):
            with patch(
                "app.application.services.solo_operator_digest_inbox.compose_four_lane_digest_inbox",
                AsyncMock(return_value=digest),
            ):
                with patch(
                    "app.application.services.solo_operator_four_lanes._load_tenant_routines",
                    AsyncMock(return_value=[]),
                ):
                    strip = await _compose_autopilot_strip(session, tenant_id=tenant_id)

    assert strip.enabled is True
    assert strip.trio_bound == 2
    assert strip.digest_pending == 2
    assert any(row.group == "trio" for row in strip.lanes)
    assert any(row.group == "four_lane" for row in strip.lanes)


def test_compose_agent_loop_strip_disabled_when_flag_off() -> None:
    sessions = [
        MissionActiveSessionOut(
            session_id="s1",
            goal="Ship POS-O",
            status="running",
            progress_label="Planning",
            progress_pct=40,
            loop_chip="Work",
            href="/agents?session=s1",
            loop_timeline_href="/agents?session=s1#agent-loop-timeline",
        ),
    ]
    with patch("app.application.services.mission_home_service.settings") as mock_settings:
        mock_settings.agent_loop_timeline_enabled = False
        strip = _compose_agent_loop_strip(sessions)

    assert strip.enabled is False


def test_compose_agent_loop_strip_maps_primary_session() -> None:
    sessions = [
        MissionActiveSessionOut(
            session_id="s1",
            goal="Ship POS-O",
            status="running",
            progress_label="Planning",
            progress_pct=40,
            loop_chip="Work",
            href="/agents?session=s1",
            loop_timeline_href="/agents?session=s1#agent-loop-timeline",
        ),
    ]
    with patch("app.application.services.mission_home_service.settings") as mock_settings:
        mock_settings.agent_loop_timeline_enabled = True
        strip = _compose_agent_loop_strip(sessions)

    assert strip.enabled is True
    assert strip.primary_session_id == "s1"
    assert strip.progress_pct == 40
    assert strip.loop_timeline_href.endswith("#agent-loop-timeline")


def test_compose_tool_outcome_strip_when_needs_input() -> None:
    sessions = [
        MissionActiveSessionOut(
            session_id="s1",
            goal="Approve publish",
            status="needs_input",
            progress_label="Awaiting input",
            progress_pct=80,
            loop_chip="Verify",
            href="/agents?session=s1",
            tool_outcome_href="/agents?session=s1#tool-outcome-panel",
        ),
    ]
    with patch("app.application.services.mission_home_service.settings") as mock_settings:
        mock_settings.tool_outcome_panel_enabled = True
        strip = _compose_tool_outcome_strip(sessions)

    assert strip.enabled is True
    assert strip.pending_count == 1
    assert strip.tool_outcome_href.endswith("#tool-outcome-panel")


def test_compose_tool_outcome_strip_disabled_without_needs_input() -> None:
    sessions = [
        MissionActiveSessionOut(
            session_id="s1",
            goal="Running",
            status="running",
            progress_label="Planning",
            progress_pct=20,
            loop_chip="Work",
            href="/agents?session=s1",
        ),
    ]
    with patch("app.application.services.mission_home_service.settings") as mock_settings:
        mock_settings.tool_outcome_panel_enabled = True
        strip = _compose_tool_outcome_strip(sessions)

    assert strip.enabled is False


@pytest.mark.asyncio
async def test_compose_loop_guardrails_strip_maps_policy() -> None:
    session = AsyncMock()
    tenant_id = uuid.uuid4()
    active = [
        MissionActiveSessionOut(
            session_id="s1",
            goal="Ship",
            status="running",
            progress_label="Planning",
            progress_pct=30,
            loop_chip="Work",
            href="/agents?session=s1",
        ),
    ]
    policy = type(
        "Policy",
        (),
        {
            "enabled": True,
            "max_turns": 4,
            "min_score": 0.8,
            "cost_cap_usd": 1.5,
        },
    )()

    with patch("app.application.services.mission_home_service.settings") as mock_settings:
        mock_settings.loop_guardrails_enabled = True
        with patch(
            "app.application.services.loop_guardrails_service.get_loop_guardrails_policy",
            AsyncMock(return_value=policy),
        ):
            strip = await _compose_loop_guardrails_strip(
                session,
                tenant_id=tenant_id,
                active_sessions=active,
            )

    assert strip.enabled is True
    assert strip.max_turns == 4
    assert strip.session_guardrails_href.endswith("#session-loop-guardrails")


@pytest.mark.asyncio
async def test_compose_goldmine_strip_maps_alerts() -> None:
    session = AsyncMock()
    tenant_id = uuid.uuid4()
    rows = [
        {
            "forager_id": "f1",
            "forager_name": "Jobs Monitor",
            "new_item_count": 3,
            "detail": "3 new listings",
        },
    ]

    with patch("app.application.services.mission_home_service.settings") as mock_settings:
        mock_settings.forager_goldmine_dispatch_enabled = True
        with patch(
            "app.application.services.forager_goldmine_dispatch_service.compose_goldmine_alert_inbox_items",
            AsyncMock(return_value=rows),
        ):
            strip = await _compose_goldmine_strip(session, tenant_id=tenant_id)

    assert strip.enabled is True
    assert strip.alert_count == 1
    assert strip.new_items_total == 3
    assert strip.foragers_href.endswith("#goldmine-alerts")


@pytest.mark.asyncio
async def test_compose_social_intel_strip_maps_weak_signals() -> None:
    session = AsyncMock()
    tenant_id = uuid.uuid4()
    weak = WeakSignalPreviewOut(
        enabled=True,
        signal_count=2,
        top_title="Agent loop hype",
        advisor_hint="hint",
    )
    roadmap = type(
        "Roadmap",
        (),
        {
            "enabled": True,
            "signal_count": 5,
            "window_days": 90,
            "due": False,
            "innovation_lab_href": "/innovation-lab",
        },
    )()

    with patch("app.application.services.mission_home_service.settings") as mock_settings:
        mock_settings.closed_loop_presets_enabled = True
        with patch(
            "app.application.services.social_intel_roadmap_refresh_service.compose_social_intel_roadmap_refresh_kpi",
            AsyncMock(return_value=roadmap),
        ):
            with patch(
                "app.application.services.closed_loop_presets_service.get_active_loop5_preset_for_tenant",
                AsyncMock(return_value=None),
            ):
                strip = await _compose_social_intel_strip(
                    session,
                    tenant_id=tenant_id,
                    weak_signal=weak,
                )

    assert strip.enabled is True
    assert strip.weekly_signal_count == 2
    assert strip.research_href.endswith("#research-bee")


@pytest.mark.asyncio
async def test_compose_data_monitor_strip_when_no_monitors() -> None:
    session = AsyncMock()
    tenant_id = uuid.uuid4()

    with patch("app.application.services.mission_home_service.settings") as mock_settings:
        mock_settings.data_monitor_wizard_enabled = True
        with patch(
            "app.application.services.mission_home_service._count_data_monitor_foragers",
            AsyncMock(return_value=0),
        ):
            with patch(
                "app.application.services.data_monitor_wizard_service.compose_data_monitor_wizard_snapshot",
                return_value=type(
                    "Snap",
                    (),
                    {
                        "enabled": True,
                        "examples": [type("Ex", (), {"intent": "Track EU remote jobs"})()],
                    },
                )(),
            ):
                strip = await _compose_data_monitor_strip(session, tenant_id=tenant_id)

    assert strip.enabled is True
    assert strip.monitor_count == 0
    assert strip.wizard_href.endswith("#data-monitor-wizard")


@pytest.mark.asyncio
async def test_compose_discovery_strip_when_keys_ready() -> None:
    session = AsyncMock()

    with patch("app.application.services.mission_home_service.settings") as mock_settings:
        mock_settings.forager_discovery_enabled = True
        with patch(
            "app.application.services.forager_discovery_service.compose_forager_discovery_wizard_snapshot",
            AsyncMock(
                return_value=type(
                    "Snap",
                    (),
                    {
                        "enabled": True,
                        "keys_configured": True,
                        "tavily_configured": True,
                        "serper_configured": False,
                        "operator_hint": "Discover public URLs via Serper/Tavily.",
                    },
                )(),
            ),
        ):
            strip = await _compose_discovery_strip(session)

    assert strip.enabled is True
    assert strip.keys_configured is True
    assert strip.wizard_href.endswith("#discovery-wizard")
