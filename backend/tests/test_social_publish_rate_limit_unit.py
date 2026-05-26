"""Unit tests for social publish live rate limits."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest

from app.application.services.social_publish_rate_limit import check_social_publish_rate_limit


@pytest.mark.asyncio
async def test_rate_limit_simulate_always_allowed() -> None:
    allowed, msg = await check_social_publish_rate_limit(
        dashboard_user_id=uuid.uuid4(),
        channel="instagram",
        mode="simulate",
    )
    assert allowed is True
    assert msg == ""


@pytest.mark.asyncio
async def test_rate_limit_live_blocks_when_exceeded() -> None:
    with patch(
        "app.application.services.social_publish_rate_limit.sliding_window_reserve",
        new_callable=AsyncMock,
        return_value=False,
    ):
        allowed, msg = await check_social_publish_rate_limit(
            dashboard_user_id=uuid.uuid4(),
            channel="instagram",
            mode="live",
        )
    assert allowed is False
    assert "rate limit" in msg.lower()


@pytest.mark.asyncio
async def test_rate_limit_live_allowed_when_under_limit() -> None:
    with patch(
        "app.application.services.social_publish_rate_limit.sliding_window_reserve",
        new_callable=AsyncMock,
        return_value=True,
    ):
        allowed, msg = await check_social_publish_rate_limit(
            dashboard_user_id=uuid.uuid4(),
            channel="instagram",
            mode="live",
        )
    assert allowed is True


@pytest.mark.asyncio
async def test_rate_limit_snapshot_builds_channel_rows() -> None:
    from app.application.services.social_publish_rate_limit import build_social_publish_rate_limit_snapshot

    with patch(
        "app.application.services.social_publish_rate_limit.sliding_window_count",
        new_callable=AsyncMock,
        side_effect=[2, 1, 0, 0, 0, 0],
    ):
        snapshot = await build_social_publish_rate_limit_snapshot(dashboard_user_id=uuid.uuid4())
    assert snapshot.global_used == 2
    assert snapshot.global_remaining == snapshot.global_max - 2
    assert len(snapshot.channels) >= 1
    assert snapshot.channels[0].used == 1
