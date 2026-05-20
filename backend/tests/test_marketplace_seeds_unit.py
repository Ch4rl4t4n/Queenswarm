"""Tests for premium marketplace recipe seeds."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.application.services.skill_marketplace_policy import is_premium_recipe, resolve_skill_price_cents
from app.domain.recipes.marketplace_seeds import FACTORY_RECIPE_SEEDS, PREMIUM_MARKETPLACE_SEEDS, load_premium_marketplace_seeds
from app.infrastructure.persistence.models.recipe import Recipe


@pytest.mark.asyncio
async def test_load_premium_marketplace_seeds_when_empty_then_inserts_all() -> None:
    session = AsyncMock()
    session.scalar = AsyncMock(return_value=0)
    session.add = MagicMock()
    session.flush = AsyncMock()

    expected = len(PREMIUM_MARKETPLACE_SEEDS) + len(FACTORY_RECIPE_SEEDS)
    inserted = await load_premium_marketplace_seeds(session)

    assert inserted == expected
    assert session.add.call_count == expected
    session.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_load_premium_marketplace_seeds_when_present_then_skips() -> None:
    session = AsyncMock()
    session.scalar = AsyncMock(return_value=1)
    session.add = MagicMock()
    session.flush = AsyncMock()

    inserted = await load_premium_marketplace_seeds(session)

    assert inserted == 0
    session.add.assert_not_called()
    session.flush.assert_not_awaited()


def test_premium_marketplace_seed_tags_resolve_prices() -> None:
    for spec in PREMIUM_MARKETPLACE_SEEDS:
        recipe = Recipe(
            name=str(spec["name"]),
            description=str(spec["description"]),
            topic_tags=list(spec["topic_tags"]),  # type: ignore[arg-type]
            workflow_template={"steps": []},
            success_count=5,
            fail_count=0,
            avg_pollen_earned=10.0,
            verified_at=datetime.now(tz=UTC),
        )
        assert is_premium_recipe(recipe) is True
        assert resolve_skill_price_cents(recipe) > 0
