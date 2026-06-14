"""Unit tests for Gumroad catalog sync (MK7)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.application.services.gumroad_catalog_sync import (
    match_gumroad_product_to_slug,
    resolve_slug_for_gumroad_product_id,
    sync_gumroad_urls_to_state,
)


def test_match_gumroad_product_to_slug_when_permalink_matches() -> None:
    slug_index = {"newsletter-growth-loop": "newsletter-growth-loop-with-verified-outcomes-5"}
    row = {"custom_permalink": "newsletter-growth-loop", "short_url": "https://seller.gumroad.com/l/x"}
    assert match_gumroad_product_to_slug(row, slug_index) == "newsletter-growth-loop-with-verified-outcomes-5"


def test_sync_gumroad_urls_to_state_writes_product_ids(tmp_path: Path) -> None:
    ready = tmp_path / "gumroad-ready" / "hero-skill-7"
    ready.mkdir(parents=True)
    (ready / "manifest.json").write_text(
        json.dumps({"slug": "hero-skill-7", "kind": "skill_factory", "score": 88}),
        encoding="utf-8",
    )
    result = sync_gumroad_urls_to_state(
        access_token="token",
        export_root=tmp_path,
        products=[
            {
                "id": "prod_abc",
                "custom_permalink": "hero-skill",
                "short_url": "https://seller.gumroad.com/l/hero-skill",
            },
        ],
    )
    assert result.ok is True
    assert result.synced_count == 1
    state = json.loads((tmp_path / "gumroad-upload-status.json").read_text(encoding="utf-8"))
    record = state["products"]["hero-skill-7"]
    assert record["gumroad_product_id"] == "prod_abc"
    assert record["gumroad_url"].startswith("https://")
    assert resolve_slug_for_gumroad_product_id("prod_abc", export_root=tmp_path) == "hero-skill-7"
