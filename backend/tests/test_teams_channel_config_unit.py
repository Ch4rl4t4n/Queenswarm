"""Unit tests for Microsoft Teams delivery channel config."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.presentation.api.routers.dashboard_session import TeamsChannelConfig


def test_teams_channel_config_accepts_office_webhook() -> None:
    cfg = TeamsChannelConfig.model_validate(
        {
            "enabled": True,
            "webhook_url": "https://contoso.webhook.office.com/webhook/abc/def",
        },
    )
    assert cfg.enabled is True
    assert cfg.webhook_url is not None


def test_teams_channel_config_rejects_invalid_webhook() -> None:
    with pytest.raises(ValidationError):
        TeamsChannelConfig.model_validate(
            {"enabled": True, "webhook_url": "https://evil.example/webhook/x"},
        )
