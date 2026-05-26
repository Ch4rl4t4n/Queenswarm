"""Solo daily plan unit tests."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest

from app.application.services.solo_daily_plan import compose_solo_daily_plan


@pytest.mark.asyncio
async def test_compose_solo_daily_plan_includes_po_and_trio() -> None:
    session = AsyncMock()
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()

    loop_mock = AsyncMock()
    loop_mock.return_value = type(
        "Loop",
        (),
        {
            "phase": "morning",
            "actions": [],
            "publish_onboarding": {"progress_pct": 36},
            "links": {"ballroom": "/ballroom"},
        },
    )()

    with (
        patch("app.application.services.solo_daily_plan.settings") as mock_settings,
        patch(
            "app.application.services.solo_daily_plan.compose_operator_loop_snapshot",
            loop_mock,
        ),
        patch(
            "app.application.services.solo_daily_plan.get_solo_trio_status",
            new_callable=AsyncMock,
        ) as trio_mock,
    ):
        mock_settings.solo_mode_enabled = True
        mock_settings.operator_loop_enabled = True
        trio_mock.return_value = {"bound_lane_count": 2}

        plan = await compose_solo_daily_plan(
            session,
            tenant_id=tenant_id,
            dashboard_user_id=user_id,
            tenant=None,
        )

    assert plan.enabled is True
    lanes = {item.lane for item in plan.items}
    assert "po" in lanes
    assert "ops" in lanes
    assert any(item.id == "trio_cycle" for item in plan.items)


@pytest.mark.asyncio
async def test_compose_solo_daily_plan_disabled_when_flags_off() -> None:
    with patch("app.application.services.solo_daily_plan.settings") as mock_settings:
        mock_settings.solo_mode_enabled = False
        mock_settings.operator_loop_enabled = False
        plan = await compose_solo_daily_plan(
            AsyncMock(),
            tenant_id=uuid.uuid4(),
            dashboard_user_id=uuid.uuid4(),
            tenant=None,
        )
    assert plan.enabled is False
    assert plan.items == []
