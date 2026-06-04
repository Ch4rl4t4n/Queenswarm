"""Unit tests for Gumroad cover asset generation."""

from __future__ import annotations

from pathlib import Path

from scripts.gumroad_cover_asset import render_cover_brief, render_cover_html, write_cover_assets
from scripts.gumroad_upload_tracker import parse_shortlist


def _product():
    return parse_shortlist(
        """# Gumroad Upload Shortlist

- [ ] `seo-pack` (content_pack, score 115)
  - **Subtitle:** Turn one blog post into many useful social snippets.
  - **Price:** EUR 19.00
  - **Description:** SEO agencies that need faster social repurposing.
  - **File:** `/tmp/seo-pack.tar.gz`
  - **Listing:** `seo-pack/LISTING.md`
""",
    )[0]


def test_render_cover_html_contains_brand_and_product_copy() -> None:
    html = render_cover_html(_product(), title="SEO Repurpose Pack", hook="Turn one blog post into social snippets.")

    assert "<!doctype html>" in html
    assert "Queenswarm" in html
    assert "SEO Repurpose Pack" in html
    assert "Turn one blog post into social snippets." in html
    assert "#FFB800" in html


def test_render_cover_brief_lists_required_screenshot_assets() -> None:
    brief = render_cover_brief(_product(), title="SEO Repurpose Pack")

    assert "# Gumroad Cover Brief" in brief
    assert "pack preview screenshot" in brief
    assert "sample output screenshot" in brief
    assert "Queenswarm neon cover" in brief


def test_write_cover_assets_creates_html_and_brief(tmp_path: Path) -> None:
    out = write_cover_assets(tmp_path, _product(), title="SEO Repurpose Pack", hook="Turn one blog post into social snippets.")

    assert out == tmp_path / "seo-pack"
    assert (out / "cover.html").is_file()
    assert (out / "COVER_BRIEF.md").is_file()
    assert "SEO Repurpose Pack" in (out / "cover.html").read_text(encoding="utf-8")
