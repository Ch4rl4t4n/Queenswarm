"""Unit tests for publish media URL validation."""

from __future__ import annotations

import pytest

from app.application.services.publish_media import (
    classify_publish_media_url,
    is_safe_publish_media_url,
    validate_publish_media_url,
)


def test_is_safe_publish_media_url_https_only() -> None:
    assert is_safe_publish_media_url("https://cdn.example.com/post.jpg") is True
    assert is_safe_publish_media_url("http://cdn.example.com/post.jpg") is False
    assert is_safe_publish_media_url("https://user:pass@cdn.example.com/x.jpg") is False
    assert is_safe_publish_media_url("https://localhost/x.jpg") is False


def test_classify_publish_media_url_extensions() -> None:
    assert classify_publish_media_url("https://cdn.example.com/a.jpg") == "image"
    assert classify_publish_media_url("https://cdn.example.com/reel.mp4") == "video"


def test_validate_instagram_rejects_video_file() -> None:
    ok, message, kind = validate_publish_media_url(
        "https://cdn.example.com/reel.mp4",
        channel="instagram",
    )
    assert ok is False
    assert "image" in message.lower()
    assert kind == "video"


def test_validate_tiktok_allows_missing_media_at_archive() -> None:
    ok, message, kind = validate_publish_media_url(None, channel="tiktok", required=False)
    assert ok is True
    assert message == ""
    assert kind is None


def test_validate_tiktok_requires_video_url_at_publish() -> None:
    ok, message, _ = validate_publish_media_url(None, channel="tiktok", required=True)
    assert ok is False
    assert "video" in message.lower()

    ok2, _, kind = validate_publish_media_url(
        "https://cdn.example.com/reel.mp4",
        channel="tiktok",
        required=True,
    )
    assert ok2 is True
    assert kind == "video"


def test_validate_tiktok_rejects_image() -> None:
    ok, message, _ = validate_publish_media_url(
        "https://cdn.example.com/thumb.png",
        channel="tiktok",
        required=True,
    )
    assert ok is False
    assert "video" in message.lower()


@pytest.mark.parametrize(
    "url",
    [
        "https://cdn.example.com/post.webp",
        "https://storage.googleapis.com/bucket/key.png",
    ],
)
def test_validate_instagram_accepts_image(url: str) -> None:
    ok, message, kind = validate_publish_media_url(url, channel="instagram")
    assert ok is True, message
    assert kind in {"image", "unknown"}
