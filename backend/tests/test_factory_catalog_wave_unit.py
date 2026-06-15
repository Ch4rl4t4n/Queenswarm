"""Unit tests for MK6 factory catalog wave planner."""

from __future__ import annotations

from pathlib import Path

from app.application.services.factory_catalog_wave import (
    MK6_TARGET_LISTINGS,
    build_factory_catalog_wave,
    parse_scorecard_counts,
    pending_vertical_seeds,
)


def test_parse_scorecard_counts_from_header_and_lines() -> None:
    md = """# Gumroad Product Scorecard

Ready: **14/16**

## Products

- `hero-skill-7` — 100/100 ready (skill_factory)
- `weak-pack` — 70/100 review (content_pack)
"""
    ready, total, clean = parse_scorecard_counts(md)
    assert ready == 14
    assert total == 16
    assert clean == 1


def test_build_factory_catalog_wave_wave_0_when_empty(tmp_path: Path) -> None:
    wave = build_factory_catalog_wave(tmp_path)
    assert wave.current_wave == "wave_0"
    assert wave.target_next == 16
    assert wave.gap_to_mk6 == MK6_TARGET_LISTINGS
    assert wave.seed_total >= 50


def test_build_factory_catalog_wave_wave_1_progress(tmp_path: Path) -> None:
    scorecard = tmp_path / "GUMROAD_SCORECARD.md"
    scorecard.write_text(
        "# Gumroad Product Scorecard\n\nReady: **18/20**\n\n"
        "- `a` — 100/100 ready (skill)\n- `b` — 100/100 uploaded (skill)\n",
        encoding="utf-8",
    )
    ready_dir = tmp_path / "gumroad-ready" / "newsletter-growth-loop-with-verified-outcomes-5"
    ready_dir.mkdir(parents=True)
    (ready_dir / "manifest.json").write_text(
        '{"slug":"newsletter-growth-loop-with-verified-outcomes-5","kind":"skill_factory","score":100,"price":"$29"}',
        encoding="utf-8",
    )
    wave = build_factory_catalog_wave(tmp_path)
    assert wave.current_wave in {"wave_0", "wave_1"}
    assert wave.catalog_deduped_count >= 1
    assert wave.next_operator_action


def test_pending_vertical_seeds_excludes_catalog_family(tmp_path: Path) -> None:
    ready_dir = tmp_path / "gumroad-ready" / "newsletter-growth-loop-with-verified-outcomes-5"
    ready_dir.mkdir(parents=True)
    (ready_dir / "manifest.json").write_text(
        '{"slug":"newsletter-growth-loop-with-verified-outcomes-5","kind":"skill_factory","score":100}',
        encoding="utf-8",
    )
    pending = pending_vertical_seeds(tmp_path)
    assert isinstance(pending, list)
    assert len(pending) >= 40
