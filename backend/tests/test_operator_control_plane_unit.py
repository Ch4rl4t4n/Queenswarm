"""Unit tests for Operator Control Plane compose and actions."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.application.services.intent_crystallizer import crystallize_intent
from app.application.services.operator_control_plane import (
    OperatorActRequest,
    compose_operator_cockpit_snapshot,
    execute_operator_action,
)


def test_crystallize_intent_factory_template() -> None:
    plan = crystallize_intent("Build micro SaaS landing for PDF tool")
    assert "micro-saas-factory" in plan.suggested_templates
    assert plan.trust_lane == "simulate"


def test_crystallize_intent_research_auto_lane() -> None:
    plan = crystallize_intent("Research competitor pricing brief")
    assert plan.trust_lane == "auto"


@pytest.mark.asyncio
async def test_compose_operator_cockpit_disabled() -> None:
    with patch("app.application.services.operator_control_plane.settings") as mock_settings:
        mock_settings.operator_control_plane_enabled = False
        snap = await compose_operator_cockpit_snapshot(
            AsyncMock(),
            tenant_id=uuid.uuid4(),
            dashboard_user_id=uuid.uuid4(),
            tenant=None,
        )
    assert snap.enabled is False


@pytest.mark.asyncio
async def test_execute_operator_action_disabled() -> None:
    with patch("app.application.services.operator_control_plane.settings") as mock_settings:
        mock_settings.operator_control_plane_enabled = False
        result = await execute_operator_action(
            AsyncMock(),
            tenant_id=uuid.uuid4(),
            dashboard_user_id=uuid.uuid4(),
            tenant=None,
            reviewer_subject="op@test",
            body=OperatorActRequest(action="start_day"),
        )
    assert result.ok is False


@pytest.mark.asyncio
async def test_execute_start_day_triggers_trio(monkeypatch: pytest.MonkeyPatch) -> None:
    trio_mock = AsyncMock(return_value={"sessions": []})
    monkeypatch.setattr(
        "app.application.services.solo_operator_trio.run_solo_trio_cycle",
        trio_mock,
    )
    with patch("app.application.services.operator_control_plane.settings") as mock_settings:
        mock_settings.operator_control_plane_enabled = True
        result = await execute_operator_action(
            AsyncMock(),
            tenant_id=uuid.uuid4(),
            dashboard_user_id=uuid.uuid4(),
            tenant=MagicMock(),
            reviewer_subject="op@test",
            body=OperatorActRequest(action="start_day"),
        )
    assert result.ok is True
    trio_mock.assert_awaited_once()
