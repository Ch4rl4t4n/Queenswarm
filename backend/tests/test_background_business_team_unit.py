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
        patch("app.application.services.marketing_product_catalog.build_catalog") as mock_catalog,
        patch(
            "app.application.services.business_operator.compose_revenue_summary",
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


@pytest.mark.asyncio
async def test_heartbeat_factory_bee_disabled_when_skill_factory_off() -> None:
    session = AsyncMock()
    tenant = SimpleNamespace(operator_settings={})
    marketing_snap = SimpleNamespace(lanes=[])

    with (
        patch("app.application.services.background_business_team.settings") as mock_settings,
        patch(
            "app.application.services.solo_operator_four_lanes.compose_four_lane_snapshot",
            new=AsyncMock(return_value=marketing_snap),
        ),
        patch("app.application.services.marketing_product_catalog.build_catalog") as mock_catalog,
        patch(
            "app.application.services.business_operator.compose_revenue_summary",
            return_value=SimpleNamespace(missing_reports=[], next_operator_action="idle"),
        ),
    ):
        mock_settings.business_background_team_enabled = True
        mock_settings.skill_factory_enabled = False
        mock_catalog.return_value = SimpleNamespace(product_count=0, products=[])
        out = await run_background_business_team_heartbeat(session, tenant_id=uuid.uuid4(), tenant=tenant)

    factory = next(bee for bee in out.bees if bee.bee_id == "factory_ops")
    assert factory.status == "disabled"


@pytest.mark.asyncio
async def test_heartbeat_revenue_bee_attention_when_reports_missing() -> None:
    session = AsyncMock()
    tenant = SimpleNamespace(operator_settings={})

    with (
        patch("app.application.services.background_business_team.settings") as mock_settings,
        patch(
            "app.application.services.solo_operator_four_lanes.compose_four_lane_snapshot",
            new=AsyncMock(return_value=SimpleNamespace(lanes=[])),
        ),
        patch("app.application.services.marketing_product_catalog.build_catalog") as mock_catalog,
        patch(
            "app.application.services.business_operator.compose_revenue_summary",
            return_value=SimpleNamespace(missing_reports=["gumroad"], next_operator_action="sync"),
        ),
    ):
        mock_settings.business_background_team_enabled = True
        mock_settings.skill_factory_enabled = False
        mock_catalog.return_value = SimpleNamespace(product_count=1, products=[SimpleNamespace(gumroad_url="x")])
        out = await run_background_business_team_heartbeat(session, tenant_id=uuid.uuid4(), tenant=tenant)

    revenue = next(bee for bee in out.bees if bee.bee_id == "revenue_ops")
    assert revenue.status == "attention"


@pytest.mark.asyncio
async def test_compose_background_team_reads_cached_bee_rows() -> None:
    session = AsyncMock()
    tenant = SimpleNamespace(
        operator_settings={
            "business_background_team": {
                "marketing_ops": {
                    "status": "attention",
                    "summary": "2 pending",
                    "pending_count": 2,
                    "last_run_at": "2026-06-05T12:00:00+00:00",
                },
            },
        },
    )

    with patch("app.application.services.background_business_team.settings") as mock_settings:
        mock_settings.business_background_team_enabled = True
        out = await compose_background_business_team(
            session,
            tenant_id=uuid.uuid4(),
            tenant=tenant,
            refresh=False,
        )

    marketing = next(bee for bee in out.bees if bee.bee_id == "marketing_ops")
    assert marketing.status == "attention"
    assert out.attention_count == 1


@pytest.mark.asyncio
async def test_compose_background_team_refresh_runs_heartbeat() -> None:
    session = AsyncMock()
    tenant = SimpleNamespace(operator_settings={})
    heartbeat = AsyncMock(
        return_value=SimpleNamespace(
            enabled=True,
            generated_at=None,
            bees=[],
            active_bee_count=0,
            attention_count=0,
        ),
    )

    with (
        patch("app.application.services.background_business_team.settings") as mock_settings,
        patch(
            "app.application.services.background_business_team.run_background_business_team_heartbeat",
            heartbeat,
        ),
    ):
        mock_settings.business_background_team_enabled = True
        await compose_background_business_team(
            session,
            tenant_id=uuid.uuid4(),
            tenant=tenant,
            refresh=True,
        )

    heartbeat.assert_awaited_once()
