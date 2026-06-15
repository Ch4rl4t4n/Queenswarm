"""Unit tests for DG2 forager structured extract templates."""

from __future__ import annotations

import pytest

from app.application.services.forager_structured_extract_service import (
    normalize_ingest_record_for_schema,
)
from app.core import config
from app.domain.forager.extract_templates import (
    embed_structured_payload,
    heuristic_structured_row,
    parse_structured_payload,
    validate_structured_row,
)


def test_heuristic_job_row_from_rss_body() -> None:
    body = (
        "# Senior Python Engineer at Acme Corp\n\n"
        "Feed: https://jobs.example.com/feed.xml\n"
        "Published: 2026-06-01\n"
        "URL: https://jobs.example.com/role/1\n\n"
        "Remote EU role with strong Python focus."
    )
    row = heuristic_structured_row(schema="jobs", content_text=body, source_url=None)
    validated = validate_structured_row("jobs", row)
    assert validated is not None
    assert validated["title"] == "Senior Python Engineer"
    assert validated["employer"] == "Acme Corp"
    assert validated["apply_url"] == "https://jobs.example.com/role/1"


def test_embed_and_parse_structured_round_trip() -> None:
    row = {"title": "Listing", "price": "1200", "listing_url": "https://example.com/a"}
    embedded = embed_structured_payload("raw body", row)
    parsed = parse_structured_payload(embedded)
    assert parsed == row
    assert embedded.startswith("raw body")


def test_normalize_ingest_record_adds_structured_block(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config.settings, "forager_structured_extract_enabled", True)
    record = {
        "content_text": "# Product X\n\nURL: https://shop.example/p\n\nPrice EUR 99",
        "source_url": "https://shop.example/p",
        "topic_tags": ["prices"],
    }
    out = normalize_ingest_record_for_schema(record, extract_schema="prices")
    assert "structured-extract" in out["topic_tags"]
    assert parse_structured_payload(out["content_text"]) is not None


def test_normalize_ingest_skipped_when_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config.settings, "forager_structured_extract_enabled", False)
    record = {"content_text": "# Title\n\nBody", "topic_tags": []}
    out = normalize_ingest_record_for_schema(record, extract_schema="jobs")
    assert out["content_text"] == "# Title\n\nBody"
    assert "structured-extract" not in out.get("topic_tags", [])
