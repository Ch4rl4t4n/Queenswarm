"""Unit helpers for generic external orchestrator pull feed."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.services.external_output_feed import normalize_tag_filter, parse_since_iso


def test_parse_since_iso_accepts_z_suffix() -> None:
    dt = parse_since_iso("2026-05-12T14:22:01Z")
    assert dt is not None
    assert dt.year == 2026
    assert dt.tzinfo is not None


def test_parse_since_iso_none_for_empty() -> None:
    assert parse_since_iso(None) is None
    assert parse_since_iso("   ") is None


def test_parse_since_iso_naive_assumes_utc() -> None:
    dt = parse_since_iso("2026-01-01T00:00:00")
    assert dt is not None
    assert dt.tzinfo == UTC


def test_parse_since_iso_bad_raises() -> None:
    with pytest.raises(ValueError, match="ISO"):
        parse_since_iso("not-a-date")


def test_normalize_tag_filter_splits() -> None:
    assert normalize_tag_filter("a, b ,") == ["a", "b"]
    assert normalize_tag_filter("") == []
