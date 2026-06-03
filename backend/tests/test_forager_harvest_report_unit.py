"""Unit tests for forager harvest report builders."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest

from app.application.services.forager_harvest_report import (
    _executive_summary,
    _finding_title,
    build_forager_harvest_report_markdown,
    build_forager_harvest_report_print_html,
)


def test_finding_title_prefers_first_line() -> None:
    """Title should come from the first content line when readable."""

    title = _finding_title("# Competitor price drop\nDetails here", "https://example.com/a")
    assert "Competitor price drop" in title


def test_executive_summary_includes_description_and_highlights() -> None:
    """Summary should merge forager description with recent item highlights."""

    text = _executive_summary(
        forager={
            "name": "RSS Scout",
            "description": "Track beekeeping e-shops.",
            "source_type": "rss",
            "items_total": 4,
        },
        items=[{"body": "New promo on honey jars\nMore detail"}],
    )
    assert "Track beekeeping e-shops." in text
    assert "4" in text
    assert "New promo on honey jars" in text


def test_build_markdown_contains_findings() -> None:
    """Markdown export should include executive summary and numbered findings."""

    report = {
        "forager_id": str(uuid.uuid4()),
        "name": "Najman E-shop Intel",
        "description": "CZ/SK e-shops",
        "source_type": "rss",
        "items_total": 2,
        "executive_summary": "Two signals indexed.",
        "generated_at": datetime.now(tz=UTC),
        "items": [
            {
                "title": "Promo detected",
                "body": "Competitor launched 15% discount.",
                "source_url": "https://example.com/promo",
                "scraped_at": datetime.now(tz=UTC),
                "confidence": 0.82,
                "source_type": "forager:rss",
            },
        ],
    }
    md = build_forager_harvest_report_markdown(report)
    assert "# Forager Intelligence Report" in md
    assert "Executive summary" in md
    assert "Promo detected" in md
    assert "Competitor launched 15% discount." in md


def test_build_print_html_is_non_empty() -> None:
    """Print HTML should render without raising."""

    report = {
        "forager_id": str(uuid.uuid4()),
        "name": "Test Forager",
        "description": "",
        "source_type": "rss",
        "items_total": 0,
        "executive_summary": "No items yet.",
        "generated_at": datetime.now(tz=UTC),
        "items": [],
    }
    html = build_forager_harvest_report_print_html(report)
    assert "Forager Intelligence Report" in html
    assert "No harvested items" in html
