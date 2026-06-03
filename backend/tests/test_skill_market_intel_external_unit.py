"""Unit tests for external Skill Market Intel."""

from __future__ import annotations

import json

from app.application.services.skill_market_intel_external import (
    _parse_apify_search_results,
    _parse_serper_lines,
    _parse_tavily_blob,
)


def test_parse_serper_lines_extracts_market_signals() -> None:
    raw = (
        "- Cursor Skills Pack :: Sell on Gumroad with workflow templates (https://gumroad.com/x)\n"
        "- Unrelated page :: nothing here (https://example.com)\n"
    )
    refs = _parse_serper_lines(raw)
    assert len(refs) == 1
    assert refs[0]["kind"] == "external_serper"


def test_parse_tavily_blob_extracts_market_signals() -> None:
    raw = "GitHub marketplace for n8n workflow templates priced at €19 for agencies"
    refs = _parse_tavily_blob(raw)
    assert len(refs) == 1
    assert refs[0]["kind"] == "external_tavily"


def test_parse_apify_search_results_extracts_organic() -> None:
    raw = json.dumps(
        [
            {
                "title": "Cursor Skill Pack",
                "description": "Gumroad workflow template for AI agents priced at $19",
                "url": "https://gumroad.com/l/example",
            },
        ],
    )
    refs = _parse_apify_search_results(raw)
    assert len(refs) == 1
    assert refs[0]["kind"] == "external_apify_scrape"
    assert "Gumroad" in refs[0]["excerpt"]


def test_parse_apify_search_results_skips_irrelevant() -> None:
    raw = json.dumps([{"title": "Weather today", "description": "Sunny skies", "url": "https://example.com"}])
    assert _parse_apify_search_results(raw) == []
