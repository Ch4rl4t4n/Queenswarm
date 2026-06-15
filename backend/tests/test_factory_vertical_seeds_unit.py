"""Factory vertical seeds unit tests."""

from __future__ import annotations

from app.application.services.factory_vertical_seeds import (
    CONTENT_PACK_VERTICAL_SEEDS,
    SKILL_FACTORY_VERTICAL_SEEDS,
    starter_seeds_for_lane,
    vertical_seeds_payload,
)


def test_vertical_seeds_payload_shape() -> None:
    payload = vertical_seeds_payload()
    assert len(payload["skill_factory"]) >= 25
    assert len(payload["content_pack_factory"]) >= 25
    assert payload["skill_factory_starter"] == list(SKILL_FACTORY_VERTICAL_SEEDS[:8])


def test_starter_seeds_subset_of_vertical() -> None:
    skill_starter = starter_seeds_for_lane("skill")
    pack_starter = starter_seeds_for_lane("content_pack")
    assert all(item in SKILL_FACTORY_VERTICAL_SEEDS for item in skill_starter)
    assert all(item in CONTENT_PACK_VERTICAL_SEEDS for item in pack_starter)
