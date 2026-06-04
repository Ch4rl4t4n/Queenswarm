"""Unit tests for Gumroad product quality scorecards."""

from __future__ import annotations

from pathlib import Path

from scripts.gumroad_product_scorecard import ProductScore, render_scorecard_report, score_product
from scripts.gumroad_upload_tracker import parse_shortlist


def test_score_product_rewards_complete_listing_and_assets(tmp_path: Path) -> None:
    bundle = tmp_path / "good-pack.tar.gz"
    bundle.write_text("bundle", encoding="utf-8")
    asset_dir = tmp_path / "assets" / "good-pack"
    asset_dir.mkdir(parents=True)
    (asset_dir / "cover.html").write_text("<html></html>", encoding="utf-8")
    (asset_dir / "COVER_BRIEF.md").write_text("# Brief\n", encoding="utf-8")
    product = parse_shortlist(
        f"""# Gumroad Upload Shortlist

- [ ] `good-pack` (content_pack, score 115)
  - **Subtitle:** A strong Gumroad subtitle for a launch-ready product.
  - **Price:** EUR 29.00
  - **Description:** A concrete target buyer and outcome description.
  - **File:** `{bundle}`
  - **Listing:** `good-pack/LISTING.md`
""",
    )[0]

    score = score_product(product, asset_root=tmp_path / "assets")

    assert score.total >= 90
    assert score.verdict == "ready"
    assert score.fixes == []


def test_score_product_flags_missing_price_bundle_and_assets(tmp_path: Path) -> None:
    product = parse_shortlist(
        """# Gumroad Upload Shortlist

- [ ] `weak-pack` (content_pack, score 80)
  - **Subtitle:** Too short.
  - **Description:** Weak.
  - **File:** `/tmp/does-not-exist.tar.gz`
  - **Listing:** `weak-pack/LISTING.md`
""",
    )[0]

    score = score_product(product, asset_root=tmp_path / "assets")

    assert score.total < 70
    assert score.verdict == "fix_first"
    assert "Add explicit price" in score.fixes
    assert "Regenerate or locate upload bundle" in score.fixes
    assert "Generate cover assets" in score.fixes


def test_render_scorecard_report_groups_ready_and_fix_first() -> None:
    scores = [
        ProductScore(slug="ready-pack", kind="content_pack", total=96, verdict="ready", fixes=[]),
        ProductScore(slug="weak-pack", kind="content_pack", total=54, verdict="fix_first", fixes=["Add explicit price"]),
    ]

    report = render_scorecard_report(scores)

    assert "# Gumroad Product Scorecard" in report
    assert "Ready: **1/2**" in report
    assert "- `ready-pack` — 96/100 ready" in report
    assert "- `weak-pack` — 54/100 fix_first" in report
    assert "Add explicit price" in report
