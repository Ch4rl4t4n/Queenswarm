"""Tests for UGC skill marketplace policy and service helpers."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest

from app.application.services.skill_marketplace_policy import (
    apply_ugc_premium_tags,
    platform_cut_display,
    price_tag_for_cents,
    resolve_skill_price_cents,
)
from app.application.services.skill_marketplace_ugc import compute_platform_fee_cents
from app.infrastructure.persistence.models.recipe import Recipe


def test_price_tag_for_cents_maps_tiers() -> None:
    assert price_tag_for_cents(900) == "premium-9"
    assert price_tag_for_cents(1900) == "premium-19"


def test_apply_ugc_premium_tags_adds_required_tags() -> None:
    recipe = Recipe(
        name="ugc-test",
        workflow_template={"steps": []},
        topic_tags=["verified"],
    )
    apply_ugc_premium_tags(recipe, price_eur_cents=2900)
    tags = {t.lower() for t in recipe.topic_tags}
    assert "ugc" in tags
    assert "premium" in tags
    assert "premium-29" in tags


def test_resolve_skill_price_cents_reads_premium_19() -> None:
    recipe = Recipe(
        name="priced",
        workflow_template={"steps": []},
        topic_tags=["premium", "premium-19"],
    )
    assert resolve_skill_price_cents(recipe) == 1900


def test_compute_platform_fee_cents_default_cut() -> None:
    assert compute_platform_fee_cents(amount_cents=1900, cut_bps=2500) == 475


def test_platform_cut_display() -> None:
    assert platform_cut_display(2500) == "25%"
