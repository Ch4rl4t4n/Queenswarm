"""Skill hot tier bee unit tests."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.application.services.skill_hot_tier_bee import _score_recipe, render_skill_hot_tier_block
from app.infrastructure.persistence.models.recipe import Recipe


def _recipe(name: str, description: str) -> Recipe:
    return Recipe(
        name=name,
        description=description,
        topic_tags=["digest", "marketing"],
        workflow_template={"steps": []},
        verified_at=datetime.now(tz=UTC),
        success_count=5,
    )


def test_score_recipe_overlap() -> None:
    recipe = _recipe("Marketing digest lane", "Cron digest for Najman marketing campaigns.")
    score = _score_recipe({"marketing", "digest", "campaign"}, recipe)
    assert score > 0.1


@pytest.mark.asyncio
async def test_render_skill_hot_tier_block_disabled() -> None:
    session = AsyncMock()
    with patch("app.application.services.skill_hot_tier_bee.settings") as mock_settings:
        mock_settings.skill_hot_tier_enabled = False
        block = await render_skill_hot_tier_block(
            session,
            tenant_id=uuid.uuid4(),
            goal="Marketing digest for Najman shop",
        )
    assert block == ""


@pytest.mark.asyncio
async def test_render_skill_hot_tier_block_matches_goal() -> None:
    session = AsyncMock()
    recipe = _recipe("Marketing digest lane", "Weekly Najman marketing digest with competitor scan.")
    with patch("app.application.services.skill_hot_tier_bee.settings") as mock_settings:
        mock_settings.skill_hot_tier_enabled = True
        mock_settings.skill_hot_tier_max_recipes = 2
        mock_settings.skill_hot_tier_pool_size = 12
        mock_settings.skill_hot_tier_min_score = 0.1
        with patch(
            "app.application.services.skill_hot_tier_bee.fetch_verified_recipes",
            new=AsyncMock(return_value=[recipe]),
        ):
            block = await render_skill_hot_tier_block(
                session,
                tenant_id=uuid.uuid4(),
                goal="Run Najman marketing digest with competitor intel",
            )
    assert "SKILL HOT TIER" in block
    assert "Marketing digest lane" in block
