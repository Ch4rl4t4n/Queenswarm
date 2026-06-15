"""Unit tests for FP1 mission kanban recipe cosine matching."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.application.services.mission_kanban_recipe_match_service import (
    compose_mission_kanban_recipe_match,
)


@pytest.mark.asyncio
async def test_compose_mission_kanban_recipe_match_disabled() -> None:
    with patch("app.application.services.mission_kanban_recipe_match_service.settings") as mock_settings:
        mock_settings.mission_kanban_recipe_match_enabled = False
        result = await compose_mission_kanban_recipe_match(AsyncMock(), query="Ship Gumroad hero pack")
    assert result.enabled is False


@pytest.mark.asyncio
async def test_compose_mission_kanban_recipe_match_short_query() -> None:
    with patch("app.application.services.mission_kanban_recipe_match_service.settings") as mock_settings:
        mock_settings.mission_kanban_recipe_match_enabled = True
        result = await compose_mission_kanban_recipe_match(AsyncMock(), query="short")
    assert result.enabled is True
    assert result.hits == []


@pytest.mark.asyncio
async def test_compose_mission_kanban_recipe_match_returns_hits() -> None:
    from app.common.schemas.recipes_search import RecipeSemanticHit

    hit = RecipeSemanticHit(
        chroma_document_id="doc-1",
        similarity=0.91,
        vector_similarity=0.91,
        document_preview="Verified Gumroad listing workflow.",
        postgres_recipe_id=None,
    )
    with (
        patch("app.application.services.mission_kanban_recipe_match_service.settings") as mock_settings,
        patch(
            "app.application.services.mission_kanban_recipe_match_service.search_recipes_semantic",
            new_callable=AsyncMock,
            return_value=[hit],
        ),
    ):
        mock_settings.mission_kanban_recipe_match_enabled = True
        result = await compose_mission_kanban_recipe_match(
            AsyncMock(),
            query="Ship Gumroad hero pack listing",
        )
    assert result.enabled is True
    assert len(result.hits) == 1
    assert result.hits[0].similarity == 0.91
