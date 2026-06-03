"""Unit tests for RSS forager scraping."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.application.services.forager_rss_scraper import (
    rss_item_to_ingest_record,
    scrape_rss_forager_feeds,
)


def test_rss_item_to_ingest_record_includes_tags() -> None:
    """Ingest record should carry default tags and readable body."""

    record = rss_item_to_ingest_record(
        feed_url="https://example.com/feed.xml",
        title="Promo week",
        summary="15% off honey jars.",
        link="https://example.com/promo",
        published="2026-06-01",
        default_tags=["najman-eshop"],
    )
    assert "Promo week" in record["content_text"]
    assert "najman-eshop" in record["topic_tags"]
    assert record["source_url"] == "https://example.com/promo"


@pytest.mark.asyncio
async def test_scrape_rss_forager_feeds_returns_records() -> None:
    """Scraper should map feedparser entries into ingest payloads."""

    forager = SimpleNamespace(
        source_config={"feeds": ["https://example.com/rss"]},
        filter_config={"default_tags": ["najman-eshop"]},
    )
    fake_entry = SimpleNamespace(
        title="New product",
        summary="<p>Fresh comb honey</p>",
        link="https://example.com/p/1",
        published="Mon, 02 Jun 2026",
    )
    fake_parsed = SimpleNamespace(entries=[fake_entry])

    with patch(
        "app.application.services.forager_rss_scraper.fetch_rss_feed_records",
        new=AsyncMock(
            return_value=[
                {
                    "source_url": "https://example.com/p/1",
                    "content_text": "# New product\n\nFresh comb honey",
                    "confidence_score": 0.7,
                    "topic_tags": ["najman-eshop"],
                },
            ],
        ),
    ) as mock_fetch:
        records = await scrape_rss_forager_feeds(forager)
        mock_fetch.assert_awaited_once()
    assert len(records) == 1
    assert records[0]["source_url"] == "https://example.com/p/1"
