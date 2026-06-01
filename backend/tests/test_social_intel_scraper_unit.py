"""Unit tests for social intel scraper helpers."""

from __future__ import annotations

from app.application.services.social_intel_scraper import (
    normalize_x_source_key,
    normalize_youtube_source_key,
    scraped_item_to_ingest_record,
    ScrapedIntelItem,
)


def test_normalize_youtube_source_key_handle() -> None:
    assert normalize_youtube_source_key("@Naval") == "@naval"
    assert normalize_youtube_source_key("https://www.youtube.com/@mkbhd") == "@mkbhd"


def test_normalize_x_source_key_url() -> None:
    assert normalize_x_source_key("https://x.com/naval") == "naval"
    assert normalize_x_source_key("@Naval") == "naval"


def test_scraped_item_to_ingest_record_tags() -> None:
    item = ScrapedIntelItem(
        platform="youtube",
        source_key="@test",
        external_id="vid123",
        title="Test video",
        summary="Summary body",
        source_url="https://youtube.com/watch?v=vid123",
    )
    record = scraped_item_to_ingest_record(item, default_tags=["intel"])
    assert "pending-grok-verification" in record["topic_tags"]
    assert "hivemind-candidate" not in record["topic_tags"]
    assert "platform:youtube" in record["topic_tags"]
    assert "intel" in record["topic_tags"]
    assert "vid123" in record["content_text"] or "Test video" in record["content_text"]
