"""Unit tests for factory product presets."""

from __future__ import annotations

from app.application.services.factory_product_presets import factory_product_presets, preset_by_id


def test_factory_product_presets_include_pigford_and_middleton() -> None:
    rows = factory_product_presets()
    ids = {row.id for row in rows}
    assert "pigford_solo_founder" in ids
    assert "middleton_local_biz_5_workers" in ids
    middleton = preset_by_id("middleton_local_biz_5_workers")
    assert middleton is not None
    assert len(middleton.niche_seeds) == 5
