"""Unit tests for BA3 Background Business Team."""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.application.services.background_business_team import (
    compose_background_business_team,
    run_background_business_team_heartbeat,
)


@pytest.mark.asyncio
async def test_compose_background_team_disabled() -> None:
    session = AsyncMock()
    with patch("app.application.services.background_business_team.settings") as mock_settings:
        mock_settings.business_background_team_enabled = False
        out = await compose_background_business_team(session, tenant_id=uuid.uuid4(), tenant=None)
    assert out.enabled is False


@pytest.mark.asyncio
async def test_heartbeat_persists_bee_state() -> None:
    session = AsyncMock()
    tenant = SimpleNamespace(operator_settings={})
    marketing_snap = SimpleNamespace(
        lanes=[
            SimpleNamespace(
                lane_id="marketing_najman",
                pending_digest_count=2,
                promote_ready_count=1,
                routine=SimpleNamespace(is_active=True),
            ),
        ],
    )
    factory_snap = SimpleNamespace(
        queue_count=1,
        building_count=0,
        launch_readiness=SimpleNamespace(sellable_count=3),
    )

    with (
        patch("app.application.services.background_business_team.settings") as mock_settings,
        patch(
            "app.application.services.solo_operator_four_lanes.compose_four_lane_snapshot",
            new=AsyncMock(return_value=marketing_snap),
        ),
        patch(
            "app.application.services.skill_factory_service.compose_skill_factory_snapshot",
            new=AsyncMock(return_value=factory_snap),
        ),
        patch("app.application.services.background_business_team.build_catalog") as mock_catalog,
        patch(
            "app.application.services.background_business_team.compose_revenue_summary",
            return_value=SimpleNamespace(missing_reports=[], next_operator_action="ok"),
        ),
    ):
        mock_settings.business_background_team_enabled = True
        mock_settings.skill_factory_enabled = True
        mock_catalog.return_value = SimpleNamespace(
            product_count=2,
            products=[SimpleNamespace(gumroad_url=None), SimpleNamespace(gumroad_url="x")],
        )
        out = await run_background_business_team_heartbeat(session, tenant_id=uuid.uuid4(), tenant=tenant)

    assert out.enabled is True
    assert len(out.bees) == 3
    assert tenant.operator_settings.get("business_background_team")
