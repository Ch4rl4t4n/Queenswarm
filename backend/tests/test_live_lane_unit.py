"""Live lane unit tests."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.application.services.live_lane import compose_live_lane_snapshot, preflight_live_lane


@pytest.mark.asyncio
async def test_compose_live_lane_snapshot_merges_lanes() -> None:
    session = AsyncMock()
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()

    with (
        patch("app.application.services.live_lane.settings") as mock_settings,
        patch(
            "app.application.services.live_lane.build_prediction_markets_status_snapshot",
            new_callable=AsyncMock,
        ) as pm_mock,
        patch(
            "app.application.services.live_lane.compose_publish_onboarding_snapshot",
            new_callable=AsyncMock,
        ) as pub_mock,
        patch(
            "app.application.services.live_lane.build_social_publish_snapshot",
            new_callable=AsyncMock,
        ) as social_mock,
        patch("app.application.services.live_lane._has_simulate_audit", return_value=False),
        patch("app.application.services.live_lane._has_live_audit", return_value=False),
    ):
        mock_settings.live_lane_snapshot_enabled = True
        mock_settings.prediction_markets_live_trading_enabled = False
        mock_settings.social_publish_live_enabled = False

        pm_mock.return_value = {
            "polymarket_readiness": {
                "progress_pct": 50,
                "ready": False,
                "steps": [{"id": "gamma", "label": "Gamma", "done": True, "detail": "ok"}],
            },
        }
        from app.application.services.publish_operator_onboarding import PublishOnboardingSnapshotOut

        pub_mock.return_value = PublishOnboardingSnapshotOut(
            generated_at=datetime.now(tz=UTC),
            progress_pct=40,
        )
        social_mock.return_value = SimpleNamespace(channels=[], ready_items=[])

        snap = await compose_live_lane_snapshot(
            session,
            tenant_id=tenant_id,
            dashboard_user_id=user_id,
            tenant=None,
        )

    assert snap.enabled is True
    assert snap.polymarket_prep_pct == 50
    assert snap.trading_live_flag is False
    assert any(step.lane == "trading" for step in snap.steps)
    assert any(step.lane == "publish" for step in snap.steps)


@pytest.mark.asyncio
async def test_preflight_live_lane_lists_blockers() -> None:
    session = AsyncMock()

    with (
        patch("app.application.services.live_lane.settings") as mock_settings,
        patch(
            "app.application.services.live_lane.compose_live_lane_snapshot",
            new_callable=AsyncMock,
        ) as snap_mock,
    ):
        mock_settings.live_lane_snapshot_enabled = True
        mock_settings.prediction_markets_enabled = True
        snap_mock.return_value = SimpleNamespace(
            polymarket_prep_pct=50,
            trading_live_flag=False,
            publish_live_flag=False,
            steps=[
                SimpleNamespace(id="social_oauth", status="pending"),
                SimpleNamespace(id="social_simulate", status="pending"),
            ],
        )

        result = await preflight_live_lane(
            session,
            tenant_id=uuid.uuid4(),
            dashboard_user_id=uuid.uuid4(),
            tenant=None,
        )

    assert result.enabled is True
    assert result.trading.allowed is False
    assert result.publish.allowed is False
    assert any("LIVE_TRADING" in b for b in result.trading.blockers)
