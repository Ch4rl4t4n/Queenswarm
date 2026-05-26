"""Unit tests for Trust Autopilot Zero-UI notifications."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.application.services.trust_autopilot_notify import (
    _trust_ping_already_sent,
    notify_publish_pack_simulate_ready,
    notify_publish_queue_approved,
)


def test_trust_ping_dedup() -> None:
    row = MagicMock()
    row.structured_json = {"trust_autopilot_pings": {"simulate_ready": "2026-01-01T00:00:00Z"}}
    assert _trust_ping_already_sent(row, key="simulate_ready") is True
    assert _trust_ping_already_sent(row, key="other") is False


@pytest.mark.asyncio
async def test_notify_publish_pack_simulate_ready_skips_when_deduped() -> None:
    row = MagicMock()
    row.id = uuid.uuid4()
    row.title = "Test pack"
    row.markdown_body = "body"
    row.structured_json = {"trust_autopilot_pings": {"simulate_ready": "x"}, "channel": "twitter"}

    with patch("app.application.services.trust_autopilot_notify.settings") as mock_settings:
        mock_settings.publish_queue_enabled = True
        mock_settings.operator_zero_ui_notify_enabled = True
        result = await notify_publish_pack_simulate_ready(
            AsyncMock(),
            row=row,
            dashboard_user_id=uuid.uuid4(),
        )
    assert result == {"telegram": False}


@pytest.mark.asyncio
async def test_notify_publish_pack_simulate_ready_sends_ping() -> None:
    row = MagicMock()
    row.id = uuid.uuid4()
    row.title = "Morning brief"
    row.markdown_body = "Hello world"
    row.structured_json = {"channel": "instagram"}

    send_mock = AsyncMock(return_value={"telegram": True})
    mark_mock = AsyncMock()
    tenant = MagicMock()
    tenant.id = uuid.uuid4()

    with patch("app.application.services.trust_autopilot_notify.settings") as mock_settings:
        mock_settings.publish_queue_enabled = True
        mock_settings.operator_zero_ui_notify_enabled = True
        with patch(
            "app.application.services.trust_autopilot_notify._resolve_tenant_for_user",
            AsyncMock(return_value=tenant),
        ):
            with patch(
                "app.application.services.trust_autopilot_notify._send_trust_ping",
                send_mock,
            ):
                with patch(
                    "app.application.services.trust_autopilot_notify._mark_trust_ping_sent",
                    mark_mock,
                ):
                    result = await notify_publish_pack_simulate_ready(
                        AsyncMock(),
                        row=row,
                        dashboard_user_id=uuid.uuid4(),
                    )

    assert result == {"telegram": True}
    send_mock.assert_awaited_once()
    mark_mock.assert_awaited_once()


@pytest.mark.asyncio
async def test_notify_publish_queue_approved_respects_flag() -> None:
    row = MagicMock()
    row.id = uuid.uuid4()
    row.title = "Pack"
    row.structured_json = {"channel": "tiktok"}

    with patch("app.application.services.trust_autopilot_notify.settings") as mock_settings:
        mock_settings.publish_queue_telegram_notify_enabled = False
        result = await notify_publish_queue_approved(
            AsyncMock(),
            row=row,
            dashboard_user_id=uuid.uuid4(),
        )
    assert result == {"telegram": False}
