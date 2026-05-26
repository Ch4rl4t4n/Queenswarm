"""Unit tests for operator social OAuth status snapshot."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.application.services.operator_social_oauth_status import compose_operator_social_oauth_status


@pytest.mark.asyncio
async def test_compose_operator_social_oauth_status_disabled() -> None:
    with patch("app.application.services.operator_social_oauth_status.settings") as mock_settings:
        mock_settings.social_publish_enabled = False
        out = await compose_operator_social_oauth_status(
            AsyncMock(),
            dashboard_user_id=uuid.uuid4(),
            tenant=None,
        )
    assert out.enabled is False


@pytest.mark.asyncio
async def test_compose_operator_social_oauth_status_blockers() -> None:
    channel = SimpleNamespace(
        channel="instagram",
        label="Instagram",
        installed=True,
        active=False,
        credentials_ok=False,
    )
    audit = SimpleNamespace(count=2)
    snapshot = SimpleNamespace(channels=[channel], ready_items=[], audit=audit)

    with (
        patch("app.application.services.operator_social_oauth_status.settings") as mock_settings,
        patch(
            "app.application.services.operator_social_oauth_status.build_social_publish_snapshot",
            new_callable=AsyncMock,
            return_value=snapshot,
        ),
    ):
        mock_settings.social_publish_enabled = True
        mock_settings.social_publish_live_enabled = False
        mock_settings.oauth_meta_client_id = ""
        mock_settings.oauth_meta_client_secret = ""
        mock_settings.oauth_x_client_id = ""
        mock_settings.oauth_x_client_secret = ""
        mock_settings.oauth_tiktok_client_key = ""
        mock_settings.oauth_tiktok_client_secret = ""

        out = await compose_operator_social_oauth_status(
            AsyncMock(),
            dashboard_user_id=uuid.uuid4(),
            tenant=None,
        )

    assert out.enabled is True
    assert out.env_configured_count == 0
    assert out.active_channel_count == 0
    assert len(out.blockers) >= 2
    assert out.simulate_count == 2


@pytest.mark.asyncio
async def test_compose_operator_social_oauth_status_active_channel() -> None:
    channel = SimpleNamespace(
        channel="twitter",
        label="X",
        installed=True,
        active=True,
        credentials_ok=True,
    )
    audit = SimpleNamespace(count=5)
    snapshot = SimpleNamespace(channels=[channel], ready_items=[SimpleNamespace()], audit=audit)

    with (
        patch("app.application.services.operator_social_oauth_status.settings") as mock_settings,
        patch(
            "app.application.services.operator_social_oauth_status.build_social_publish_snapshot",
            new_callable=AsyncMock,
            return_value=snapshot,
        ),
    ):
        mock_settings.social_publish_enabled = True
        mock_settings.social_publish_live_enabled = True
        mock_settings.oauth_meta_client_id = ""
        mock_settings.oauth_meta_client_secret = ""
        mock_settings.oauth_x_client_id = "id"
        mock_settings.oauth_x_client_secret = "sec"
        mock_settings.oauth_tiktok_client_key = ""
        mock_settings.oauth_tiktok_client_secret = ""

        out = await compose_operator_social_oauth_status(
            AsyncMock(),
            dashboard_user_id=uuid.uuid4(),
            tenant=None,
        )

    assert out.env_configured_count == 1
    assert out.active_channel_count == 1
    assert out.ready_items_count == 1
    assert out.live_publish_enabled is True
