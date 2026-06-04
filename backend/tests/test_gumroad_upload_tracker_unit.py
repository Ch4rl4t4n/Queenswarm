"""Unit tests for manual Gumroad upload tracking."""

from __future__ import annotations

import json

from scripts.gumroad_upload_tracker import (
    apply_uploaded_mark,
    cover_checklist,
    parse_shortlist,
    qa_product,
    render_progress_report,
)


SHORTLIST_MD = """# Gumroad Upload Shortlist

Use this checklist for manual Gumroad product creation.

- [ ] `facebook-local-pack` (content_pack, score 115)
  - **Subtitle:** Book more local jobs.
  - **Price:** EUR 19.00
  - **Description:** Local service owners.
  - **File:** `/exports/facebook-local-pack.tar.gz`
  - **Listing:** `facebook-local-pack/LISTING.md`

- [ ] `seo-skill` (skill_factory, score 85)
  - **Subtitle:** Ship SEO workflows.
  - **Price:** EUR 29.00
  - **Description:** SEO workflow operators.
  - **File:** `/exports/seo-skill.tar.gz`
  - **Listing:** `seo-skill/LISTING.md`
"""


def test_parse_shortlist_reads_ranked_products() -> None:
    products = parse_shortlist(SHORTLIST_MD)

    assert [product.slug for product in products] == ["facebook-local-pack", "seo-skill"]
    assert products[0].kind == "content_pack"
    assert products[0].score == 115
    assert products[0].bundle == "/exports/facebook-local-pack.tar.gz"
    assert products[1].listing_path == "seo-skill/LISTING.md"


def test_apply_uploaded_mark_records_url_and_preserves_existing_status() -> None:
    state = {
        "products": {
            "facebook-local-pack": {
                "status": "uploaded",
                "gumroad_url": "https://gum.co/facebook",
            },
        },
    }

    updated = apply_uploaded_mark(state, slug="seo-skill", gumroad_url="https://gum.co/seo")

    assert updated["products"]["facebook-local-pack"]["gumroad_url"] == "https://gum.co/facebook"
    assert updated["products"]["seo-skill"]["status"] == "uploaded"
    assert updated["products"]["seo-skill"]["gumroad_url"] == "https://gum.co/seo"


def test_render_progress_report_prioritizes_pending_products() -> None:
    products = parse_shortlist(SHORTLIST_MD)
    state = apply_uploaded_mark({"products": {}}, slug="facebook-local-pack", gumroad_url="https://gum.co/facebook")

    report = render_progress_report(products, state, next_limit=1)

    assert "Uploaded: **1/2**" in report
    assert "- [x] `facebook-local-pack`" in report
    assert "- [ ] `seo-skill` (skill_factory, score 85)" in report
    assert "https://gum.co/facebook" in report


def test_qa_product_flags_missing_price_short_hook_and_missing_bundle() -> None:
    product = parse_shortlist(
        """# Gumroad Upload Shortlist

- [ ] `weak-pack` (content_pack, score 80)
  - **Subtitle:** Too short.
  - **Description:** Good target.
  - **File:** `/tmp/does-not-exist.tar.gz`
  - **Listing:** `weak-pack/LISTING.md`
""",
    )[0]

    issues = qa_product(product)

    assert "missing_price" in issues
    assert "weak_hook" in issues
    assert "bundle_missing" in issues


def test_render_progress_report_includes_listing_qa_warnings() -> None:
    product = parse_shortlist(
        """# Gumroad Upload Shortlist

- [ ] `weak-pack` (content_pack, score 80)
  - **Subtitle:** Too short.
  - **Description:** Good target.
  - **File:** `/tmp/does-not-exist.tar.gz`
  - **Listing:** `weak-pack/LISTING.md`
""",
    )[0]

    report = render_progress_report([product], {"products": {}}, next_limit=1)

    assert "**QA:** missing_price, weak_hook, weak_description, bundle_missing" in report


def test_cover_checklist_is_product_type_specific() -> None:
    products = parse_shortlist(SHORTLIST_MD)

    content_items = cover_checklist(products[0])
    skill_items = cover_checklist(products[1])

    assert "pack preview screenshot" in content_items
    assert "sample output screenshot" in content_items
    assert "SKILL.md preview screenshot" in skill_items
    assert "simulate-first proof screenshot" in skill_items


def test_render_progress_report_includes_cover_checklist() -> None:
    products = parse_shortlist(SHORTLIST_MD)

    report = render_progress_report(products, {"products": {}}, next_limit=1)

    assert "**Cover:** pack preview screenshot; sample output screenshot; Queenswarm neon cover" in report


def test_tracker_state_is_json_serializable() -> None:
    state = apply_uploaded_mark({"products": {}}, slug="seo-skill", gumroad_url="")

    assert json.loads(json.dumps(state))["products"]["seo-skill"]["status"] == "uploaded"
