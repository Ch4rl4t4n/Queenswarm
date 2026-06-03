"""Unit tests for Monid Skill Market Intel."""

from __future__ import annotations

import json

from app.application.services.skill_market_intel_monid import _parse_monid_discover_payload


def test_parse_monid_discover_payload_endpoints() -> None:
    raw = json.dumps(
        {
            "endpoints": [
                {
                    "provider": "social_intel",
                    "endpoint": "competitor_listings",
                    "description": "Gumroad skill pack marketplace competitor listings",
                },
                {
                    "provider": "weather",
                    "endpoint": "forecast",
                    "description": "Daily weather forecast",
                },
            ],
        },
    )
    refs = _parse_monid_discover_payload(raw, niche="cursor skills")
    assert len(refs) == 1
    assert refs[0]["kind"] == "external_monid_discover"
    assert "Gumroad" in refs[0]["excerpt"]


def test_parse_monid_discover_payload_empty() -> None:
    raw = json.dumps({"endpoints": []})
    assert _parse_monid_discover_payload(raw, niche="test") == []
