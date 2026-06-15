"""Unit tests for marketing scorecard badge metadata (REV3)."""

from __future__ import annotations

from pathlib import Path

from app.application.services.marketing_scorecard import (
    is_scorecard_clean,
    load_scorecard_index,
    parse_scorecard_index,
    scorecard_fields_for_slug,
)


def test_parse_scorecard_index_maps_slugs() -> None:
    md = "# Scorecard\n\n- `hero-skill-7` — 100/100 ready (skill)\n- `weak` — 70/100 review (pack)\n"
    index = parse_scorecard_index(md)
    assert index["hero-skill-7"] == (100, "ready")
    assert index["weak"] == (70, "review")


def test_is_scorecard_clean_requires_100_and_ready() -> None:
    assert is_scorecard_clean(score=100, verdict="ready") is True
    assert is_scorecard_clean(score=100, verdict="uploaded") is True
    assert is_scorecard_clean(score=99, verdict="ready") is False


def test_scorecard_fields_for_slug_uses_index(tmp_path: Path) -> None:
    (tmp_path / "GUMROAD_SCORECARD.md").write_text(
        "- `alpha-skill` — 100/100 uploaded (skill)\n",
        encoding="utf-8",
    )
    score, verdict, clean = scorecard_fields_for_slug("alpha-skill", manifest_score=80, export_root=tmp_path)
    assert score == 100
    assert verdict == "uploaded"
    assert clean is True


def test_load_scorecard_index_empty_when_missing(tmp_path: Path) -> None:
    assert load_scorecard_index(tmp_path) == {}
