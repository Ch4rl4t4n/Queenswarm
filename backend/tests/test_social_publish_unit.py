"""Unit tests for Social Publish Phase C helpers."""

from __future__ import annotations

from app.application.services.social_publish import (
    build_social_publish_arguments,
    compose_social_caption,
    normalize_social_channel,
)


def test_normalize_social_channel_aliases() -> None:
    assert normalize_social_channel("Instagram") == "instagram"
    assert normalize_social_channel("x-twitter") == "twitter"
    assert normalize_social_channel("tik-tok") == "tiktok"
    assert normalize_social_channel("linkedin") is None
    assert normalize_social_channel("unknown-channel") is None


def test_compose_social_caption() -> None:
    caption = compose_social_caption(
        body="Hello hive",
        hashtags=["Queenswarm", "AI"],
        cta="Learn more",
    )
    assert "Hello hive" in caption
    assert "#Queenswarm" in caption
    assert "Learn more" in caption


def test_build_social_publish_arguments_instagram() -> None:
    tool, args = build_social_publish_arguments(
        channel="instagram",
        structured={
            "body": "Launch day",
            "hashtags": ["launch"],
            "cta": "",
            "media_url": "https://cdn.example.com/post.jpg",
        },
        context={"ig_user_id": "12345"},
    )
    assert tool == "media_create"
    assert args["ig_user_id"] == "12345"
    assert args["image_url"] == "https://cdn.example.com/post.jpg"
    assert "Launch day" in args["caption"]


def test_build_social_publish_arguments_twitter_truncates() -> None:
    long_body = "x" * 400
    tool, args = build_social_publish_arguments(
        channel="twitter",
        structured={"body": long_body, "hashtags": [], "cta": ""},
        context={},
    )
    assert tool == "tweets_create"
    assert len(args["text"]) <= 280


def test_build_social_publish_arguments_facebook_text_only() -> None:
    tool, args = build_social_publish_arguments(
        channel="facebook",
        structured={"body": "Text only update", "hashtags": [], "cta": ""},
        context={"page_id": "page-99"},
    )
    assert tool == "page_feed_publish"
    assert args["page_id"] == "page-99"
    assert args["message"] == "Text only update"


def test_build_social_publish_arguments_tiktok() -> None:
    tool, args = build_social_publish_arguments(
        channel="tiktok",
        structured={
            "title": "Reel title",
            "body": "Caption here",
            "hashtags": [],
            "cta": "",
            "media_url": "https://cdn.example.com/reel.mp4",
        },
        context={},
    )
    assert tool == "video_publish_init"
    assert args["source_info"]["video_url"] == "https://cdn.example.com/reel.mp4"
