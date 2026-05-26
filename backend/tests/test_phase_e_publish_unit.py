"""Unit tests for Phase E scheduled publish and channel extensions."""

from __future__ import annotations

from datetime import UTC, datetime

from app.application.services.scheduled_publish import _parse_scheduled_at, _already_published
from app.application.services.social_publish import (
    build_social_publish_arguments,
    normalize_social_channel,
)


def test_parse_scheduled_at_iso() -> None:
    due = _parse_scheduled_at("2026-05-22T09:00:00Z")
    assert due is not None
    assert due.tzinfo is not None


def test_parse_scheduled_at_invalid() -> None:
    assert _parse_scheduled_at("not-a-date") is None
    assert _parse_scheduled_at("") is None


def test_already_published_tags() -> None:
    assert _already_published(["social-publish-live"]) is True
    assert _already_published(["social-publish-simulated"]) is False
    assert _already_published(["publish-queue-approved"]) is False


def test_normalize_newsletter() -> None:
    assert normalize_social_channel("newsletter") == "newsletter"
    assert normalize_social_channel("gmail") == "newsletter"
    assert normalize_social_channel("linkedin") is None


def test_build_newsletter_arguments() -> None:
    tool, args = build_social_publish_arguments(
        channel="newsletter",
        structured={"title": "Weekly", "body": "Hello subscribers", "hashtags": [], "cta": ""},
        context={"newsletter_to": "ops@queenswarm.love"},
    )
    assert tool == "drafts_send"
    assert args["to"] == "ops@queenswarm.love"
    assert "Hello subscribers" in args["body_text"]
