"""Unit tests for Gumroad cover asset generation."""

from __future__ import annotations

from pathlib import Path

from scripts.gumroad_cover_asset import generate_cover_assets, render_cover_brief, render_cover_html, write_cover_assets
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


def test_generate_cover_assets_all_writes_each_qa_clean_product(tmp_path: Path) -> None:
    first_bundle = tmp_path / "first.tar.gz"
    second_bundle = tmp_path / "second.tar.gz"
    first_bundle.write_text("bundle", encoding="utf-8")
    second_bundle.write_text("bundle", encoding="utf-8")
    products = parse_shortlist(
        f"""# Gumroad Upload Shortlist

- [ ] `first` (content_pack, score 115)
  - **Subtitle:** A strong Gumroad subtitle for first product.
  - **Price:** EUR 19.00
  - **Description:** A concrete target buyer and outcome description.
  - **File:** `{first_bundle}`
  - **Listing:** `first/LISTING.md`

- [ ] `second` (content_pack, score 110)
  - **Subtitle:** A strong Gumroad subtitle for second product.
  - **Price:** EUR 29.00
  - **Description:** A concrete target buyer and outcome description.
  - **File:** `{second_bundle}`
  - **Listing:** `second/LISTING.md`

- [ ] `blocked` (content_pack, score 80)
  - **Subtitle:** Too short.
  - **Description:** Weak.
  - **File:** `/tmp/missing.tar.gz`
  - **Listing:** `blocked/LISTING.md`
""",
    )

    written = generate_cover_assets(tmp_path / "assets", products, state={"products": {}}, all_products=True)

    assert [path.name for path in written] == ["first", "second"]
    assert (tmp_path / "assets" / "first" / "cover.html").is_file()
    assert not (tmp_path / "assets" / "blocked").exists()
