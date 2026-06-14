"""Unit tests for Mission Home snapshot (Track Q UX2)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest

from app.application.services.mission_home_service import (
    PROCESS_STEPS,
    _brief_bullets_from_morning,
    _resolve_process_step,
    compose_mission_home_snapshot,
)
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

    with patch("app.application.services.mission_home_service.settings") as mock_settings:
        mock_settings.solo_mode_enabled = True
        mock_settings.operator_loop_enabled = True
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
                            snapshot = await compose_mission_home_snapshot(
                                session,
                                tenant_id=tenant_id,
                                dashboard_user_id=user_id,
                                tenant=None,
                            )

    assert snapshot.enabled is True
    assert snapshot.current_step == "setup"
    assert snapshot.first_run_complete is False
    assert len(snapshot.brief_bullets) >= 1
