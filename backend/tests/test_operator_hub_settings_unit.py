"""Operator hub settings unit tests."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest

from app.application.services.operator_hub_settings import compose_operator_hub_snapshot


@pytest.mark.asyncio
async def test_compose_operator_hub_snapshot_enabled() -> None:
    session = AsyncMock()
    with (
        patch("app.application.services.operator_hub_settings.settings") as mock_settings,
        patch(
            "app.application.services.operator_hub_settings.compose_live_lane_snapshot",
            new_callable=AsyncMock,
        ) as lane_mock,
    ):
        mock_settings.operator_hub_settings_enabled = True
        mock_settings.live_lane_snapshot_enabled = True
        mock_settings.agent_os_enabled = True
        mock_settings.operator_loop_enabled = True
        mock_settings.publish_performance_enabled = True
        mock_settings.research_bee_enabled = True
        mock_settings.media_agency_in_a_box_enabled = True
        mock_settings.micro_saas_factory_enabled = True
        mock_settings.trading_cockpit_enabled = True
        mock_settings.supervisor_pattern_router_llm_enabled = False
        mock_settings.prediction_markets_live_trading_enabled = False
        mock_settings.social_publish_live_enabled = False
        mock_settings.social_publish_enabled = True
        mock_settings.solo_mode_enabled = False

        from app.application.services.live_lane import LiveLaneSnapshotOut
        from app.application.services.publish_operator_onboarding import PublishOnboardingSnapshotOut

        lane_mock.return_value = LiveLaneSnapshotOut(
            enabled=True,
            generated_at=datetime.now(tz=UTC),
            progress_pct=40,
        )

        with patch(
            "app.application.services.operator_hub_settings.compose_publish_onboarding_snapshot",
            new_callable=AsyncMock,
        ) as onboard_mock:
            onboard_mock.return_value = PublishOnboardingSnapshotOut(
                generated_at=datetime.now(tz=UTC),
                progress_pct=36,
                steps=[],
            )

            with patch(
                "app.application.services.operator_hub_settings.compose_operator_social_oauth_status",
                new_callable=AsyncMock,
            ) as oauth_mock:
                from app.application.services.operator_social_oauth_status import OperatorSocialOAuthStatusOut

                oauth_mock.return_value = OperatorSocialOAuthStatusOut(
                    enabled=True,
                    generated_at=datetime.now(tz=UTC),
                    active_channel_count=0,
                    env_configured_count=0,
                )

                with patch(
                    "app.application.services.operator_hub_settings.resolve_operator_next_action",
                ) as next_mock:
                    from app.application.services.operator_next_action import OperatorNextActionOut

                    next_mock.return_value = OperatorNextActionOut(
                        title="Add OAuth vendor keys",
                        why="test",
                        doc="docs/OPERATOR_FIRST_LIVE_POST.md",
                    )

                    snap = await compose_operator_hub_snapshot(
                        session,
                        tenant_id=uuid.uuid4(),
                        dashboard_user_id=uuid.uuid4(),
                        tenant=None,
                    )

    assert snap.enabled is True
    assert len(snap.modules) >= 8
    assert snap.live_lane is not None
    assert snap.publish_onboarding is not None
    assert snap.publish_onboarding.progress_pct == 36
    assert snap.social_oauth is not None
    assert snap.next_action is not None
    assert snap.next_action.title == "Add OAuth vendor keys"
    assert all(not flag.active for flag in snap.env_flags if "LIVE" in flag.key)


@pytest.mark.asyncio
async def test_compose_operator_hub_disabled() -> None:
    with patch("app.application.services.operator_hub_settings.settings") as mock_settings:
        mock_settings.operator_hub_settings_enabled = False
        snap = await compose_operator_hub_snapshot(
            AsyncMock(),
            tenant_id=uuid.uuid4(),
            dashboard_user_id=uuid.uuid4(),
            tenant=None,
        )
    assert snap.enabled is False
