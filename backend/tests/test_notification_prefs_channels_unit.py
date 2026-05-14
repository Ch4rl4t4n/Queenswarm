"""Unit checks for operator notification channel JSON normalization."""

from __future__ import annotations

from app.presentation.api.routers.dashboard_session import discord_webhook_url_ok, normalize_delivery_channels_blob


def test_normalize_delivery_channels_from_json_string_round_trip() -> None:
    raw = '{"email": {"enabled": true, "address": "a@b.co"}}'
    out = normalize_delivery_channels_blob(raw)
    assert out["email"]["enabled"] is True
    assert out["email"]["address"] == "a@b.co"


def test_normalize_delivery_channels_handles_nullish() -> None:
    assert normalize_delivery_channels_blob(None) == {}
    assert normalize_delivery_channels_blob("not-json") == {}
    assert normalize_delivery_channels_blob([1, 2]) == {}


def test_discord_webhook_url_accepts_known_hosts() -> None:
    assert discord_webhook_url_ok("https://discord.com/api/webhooks/1/token")
    assert discord_webhook_url_ok("https://ptb.discord.com/api/webhooks/1/token")
    assert discord_webhook_url_ok("https://canary.discord.com/api/webhooks/99/abc")
    assert discord_webhook_url_ok("https://discordapp.com/api/webhooks/1/token")


def test_discord_webhook_url_rejects_bad_inputs() -> None:
    assert not discord_webhook_url_ok("http://discord.com/api/webhooks/1/x")
    assert not discord_webhook_url_ok("https://discord.com/api/v10/channels/1")
    assert not discord_webhook_url_ok("https://fake-discord.com/api/webhooks/1/x")
    assert not discord_webhook_url_ok("https://evil.com/api/webhooks/%2f%2fdiscord.com")
