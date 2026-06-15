"""Unit tests for marketing product catalog."""

from __future__ import annotations

import json
from pathlib import Path

from app.application.services.marketing_product_catalog import (
    FEATURED_SLUGS,
    build_catalog,
    collect_catalog_products,
    find_product,
)


def _write_ready(tmp_path: Path, slug: str, *, score: int, kind: str = "skill_factory") -> None:
    package = tmp_path / "gumroad-ready" / slug
    package.mkdir(parents=True)
    (package / "manifest.json").write_text(
        json.dumps(
            {
                "slug": slug,
                "kind": kind,
                "score": score,
                "subtitle": f"Subtitle for {slug}",
                "price": "€9.00",
                "description": f"Description for {slug}",
            },
        ),
        encoding="utf-8",
    )
    (package / "GUMROAD_FIELDS.md").write_text(
        f"**Title:** Listing — {slug.replace('-', ' ').title()}\n",
        encoding="utf-8",
    )


def test_collect_catalog_products_dedupes_numbered_variants(tmp_path: Path) -> None:
    _write_ready(tmp_path, "newsletter-growth-automation", score=80)
    _write_ready(tmp_path, "newsletter-growth-automation-4", score=90)

    products = collect_catalog_products(tmp_path)

    assert len(products) == 1
    assert products[0].slug == "newsletter-growth-automation-4"
    assert products[0].score == 90


def test_build_catalog_marks_featured_slugs(tmp_path: Path) -> None:
    for slug in ("alpha-skill", FEATURED_SLUGS[0]):
        _write_ready(tmp_path, slug, score=100)

    catalog = build_catalog(tmp_path)

    featured = [product for product in catalog.products if product.featured]
    assert len(featured) == 1
    assert featured[0].slug == FEATURED_SLUGS[0]


def test_find_product_returns_none_for_missing_slug(tmp_path: Path) -> None:
    _write_ready(tmp_path, "alpha-skill", score=70)

    assert find_product("missing", tmp_path) is None
    assert find_product("alpha-skill", tmp_path) is not None


def test_collect_catalog_attaches_scorecard_fields(tmp_path: Path) -> None:
    _write_ready(tmp_path, "alpha-skill", score=80)
    (tmp_path / "GUMROAD_SCORECARD.md").write_text(
        "- `alpha-skill` — 100/100 ready (skill_factory)\n",
        encoding="utf-8",
    )
    products = collect_catalog_products(tmp_path)
    assert len(products) == 1
    assert products[0].score == 100
    assert products[0].scorecard_verdict == "ready"
    assert products[0].scorecard_clean is True
