"""Unit tests for Operator Telegram gateway (Zero-UI mode)."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

from datetime import UTC, datetime

import pytest

from app.application.services.operator_control_plane import OperatorCockpitSnapshotOut
from app.application.services.operator_telegram_gateway import (
    build_operator_telegram_webhook_url,
    format_cockpit_status_text,
    parse_telegram_command,
    verify_operator_telegram_webhook_secret,
)


def test_parse_telegram_command_start_day() -> None:
    parsed = parse_telegram_command("/day")
    assert parsed.kind == "act"
    assert parsed.action is not None
    assert parsed.action.action == "start_day"


def test_parse_telegram_command_status() -> None:
    parsed = parse_telegram_command("/status")
    assert parsed.kind == "status"


def test_parse_telegram_command_hotline_requires_text() -> None:
    parsed = parse_telegram_command("/hotline hi")
    assert parsed.kind == "help"


def test_parse_telegram_command_plain_hotline() -> None:
    parsed = parse_telegram_command("Research competitor pricing for Q2")
    assert parsed.kind == "act"
    assert parsed.action is not None
    assert parsed.action.action == "hotline"


def test_verify_webhook_secret() -> None:
    with patch("app.application.services.operator_telegram_gateway.settings") as mock_settings:
        mock_settings.operator_telegram_webhook_secret = "hive-secret"
        assert verify_operator_telegram_webhook_secret(path_secret="hive-secret") is True
        assert verify_operator_telegram_webhook_secret(path_secret="wrong") is False


def test_build_webhook_url() -> None:
    with patch("app.application.services.operator_telegram_gateway.settings") as mock_settings:
        mock_settings.operator_telegram_webhook_secret = "abc123"
        mock_settings.domain = "queenswarm.love"
        url = build_operator_telegram_webhook_url()
        assert url == "https://queenswarm.love/api/v1/operator/telegram/webhook/abc123"


def test_format_cockpit_status_text() -> None:
    snap = OperatorCockpitSnapshotOut(
        enabled=True,
        generated_at=datetime.now(tz=UTC),
        phase="morning",
        trio={"lanes_bound": 2},
        innovation_lab={"pending_count": 1},
        operator_loop={"publish_pipeline": {"pending_publish_count": 3}},
        now_actions=[],
    )
    text = format_cockpit_status_text(snapshot=snap, base_url="https://queenswarm.love")
    assert "3 Bees: 2/3" in text
    assert "/cockpit" in text


@pytest.mark.asyncio
async def test_handle_telegram_update_unknown_chat() -> None:
    from app.application.services.operator_telegram_gateway import handle_telegram_update

    db = AsyncMock()
    with patch(
        "app.application.services.operator_telegram_gateway.find_tenant_by_telegram_chat_id",
        AsyncMock(return_value=None),
    ):
        with patch("app.application.services.operator_telegram_gateway.settings") as mock_settings:
            mock_settings.operator_telegram_inbound_enabled = True
            mock_settings.operator_control_plane_enabled = True
            reply = await handle_telegram_update(
                db,
                update={"message": {"chat": {"id": 999}, "text": "/status"}},
            )
    assert "Neznámy chat" in reply
