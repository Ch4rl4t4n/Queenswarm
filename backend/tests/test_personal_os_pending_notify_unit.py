"""Unit tests for POS-L Personal OS pending approval Telegram pings."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.application.services.personal_os_pending_notify_service import (
    notify_email_drafts_pending,
    notify_weekly_compound_draft_pending,
)


@pytest.mark.asyncio
async def test_notify_weekly_compound_skips_when_disabled() -> None:
    with patch("app.application.services.personal_os_pending_notify_service.settings") as mock_settings:
        mock_settings.operator_zero_ui_notify_enabled = False
        result = await notify_weekly_compound_draft_pending(
            AsyncMock(),
            tenant_id=uuid.uuid4(),
            dashboard_user_id=uuid.uuid4(),
            week_key="2026-W23",
            draft_title="Weekly compound",
        )
    assert result == {"telegram": False}


@pytest.mark.asyncio
async def test_notify_weekly_compound_dedupes_by_week() -> None:
    tenant_id = uuid.uuid4()
    tenant = MagicMock()
    tenant.operator_settings = {
        "weekly_compound_gardener": {"last_telegram_notify_week": "2026-W23"},
    }

    session = AsyncMock()
    session.get = AsyncMock(return_value=tenant)

    with patch("app.application.services.personal_os_pending_notify_service.settings") as mock_settings:
        mock_settings.operator_zero_ui_notify_enabled = True
        result = await notify_weekly_compound_draft_pending(
            session,
            tenant_id=tenant_id,
            dashboard_user_id=uuid.uuid4(),
            week_key="2026-W23",
            draft_title="Weekly compound",
        )
    assert result == {"telegram": False}


@pytest.mark.asyncio
async def test_notify_weekly_compound_sends_ping() -> None:
    tenant_id = uuid.uuid4()
    tenant = MagicMock()
    tenant.operator_settings = {"weekly_compound_gardener": {}}

    session = AsyncMock()
    session.get = AsyncMock(return_value=tenant)
    ping_mock = AsyncMock(return_value={"telegram": True})

    with patch("app.application.services.personal_os_pending_notify_service.settings") as mock_settings:
        mock_settings.operator_zero_ui_notify_enabled = True
        with patch(
            "app.application.services.personal_os_pending_notify_service.notify_zero_ui_ping",
            ping_mock,
        ):
            result = await notify_weekly_compound_draft_pending(
                session,
                tenant_id=tenant_id,
                dashboard_user_id=uuid.uuid4(),
                week_key="2026-W24",
                draft_title="Weekly compound · week 24",
            )

    assert result == {"telegram": True}
    ping_mock.assert_awaited_once()
    session.flush.assert_awaited()


@pytest.mark.asyncio
async def test_notify_email_drafts_respects_daily_dedupe() -> None:
    tenant_id = uuid.uuid4()
    tenant = MagicMock()
    tenant.operator_settings = {
        "email_draft_outer_loop": {"last_telegram_notify_day": "2026-06-18"},
    }

    session = AsyncMock()
    session.get = AsyncMock(return_value=tenant)

    with patch("app.application.services.personal_os_pending_notify_service.settings") as mock_settings:
        mock_settings.operator_zero_ui_notify_enabled = True
        mock_settings.email_draft_outer_loop_enabled = True
        with patch(
            "app.application.services.personal_os_pending_notify_service.datetime"
        ) as mock_dt:
            mock_dt.now.return_value.date.return_value.isoformat.return_value = "2026-06-18"
            result = await notify_email_drafts_pending(
                session,
                tenant_id=tenant_id,
                dashboard_user_id=uuid.uuid4(),
                created_count=2,
            )
    assert result == {"telegram": False}
