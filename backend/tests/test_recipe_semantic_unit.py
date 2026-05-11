"""Unit tests for Chroma → Postgres recipe semantic bridge."""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.schemas.recipes_catalog import RecipeCatalogItem


@pytest.mark.asyncio
async def test_search_recipes_semantic_filters_by_min_similarity(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.services.recipe_chroma_bridge.settings.recipe_chroma_min_similarity",
        0.9,
    )
    monkeypatch.setattr(
        "app.services.recipe_chroma_bridge.settings.recipe_chroma_search_limit_cap",
        10,
    )

    async def fake_semantic(
        _: str,
        __: str,
        n_results: int = 5,
    ) -> list[dict]:
        del n_results
        return [
            {"id": "weak", "document": "hello", "metadata": {}, "distance": 0.2},
            {"id": "strong", "document": "bye", "metadata": {}, "distance": 0.04},
        ]

    monkeypatch.setattr("app.services.recipe_chroma_bridge.semantic_search", fake_semantic)

    session = AsyncMock()
    from app.services.recipe_chroma_bridge import search_recipes_semantic

    hits = await search_recipes_semantic(session, query="task", limit=5)
    assert len(hits) == 1
    assert hits[0].chroma_document_id == "strong"
    assert abs(hits[0].similarity - 0.96) < 1e-6


@pytest.mark.asyncio
async def test_search_recipes_semantic_joins_postgres_when_metadata_uuid_present(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.services.recipe_chroma_bridge.settings.recipe_chroma_min_similarity",
        0.0,
    )
    monkeypatch.setattr(
        "app.services.recipe_chroma_bridge.settings.recipe_chroma_search_limit_cap",
        10,
    )
    pid = uuid.uuid4()

    async def fake_semantic(
        _: str,
        __: str,
        n_results: int = 5,
    ) -> list[dict]:
        del n_results
        return [
            {
                "id": "chrom-1",
                "document": "steps",
                "metadata": {"postgres_recipe_id": str(pid)},
                "distance": 0.1,
            },
        ]

    monkeypatch.setattr("app.services.recipe_chroma_bridge.semantic_search", fake_semantic)

    attrs = RecipeCatalogItem(
        id=pid,
        name="join-test-recipe",
        description="desc",
        topic_tags=["t"],
        success_count=2,
        fail_count=1,
        avg_pollen_earned=3.5,
        embedding_id=None,
        verified_at=None,
        last_used_at=None,
        is_deprecated=False,
    ).model_dump(mode="python")
    stub = SimpleNamespace(**attrs)

    exec_result = MagicMock()
    exec_result.scalar_one_or_none.return_value = stub

    session = AsyncMock()
    session.execute = AsyncMock(return_value=exec_result)

    from app.services.recipe_chroma_bridge import search_recipes_semantic

    hits = await search_recipes_semantic(session, query="x", limit=3)
    assert len(hits) == 1
    assert hits[0].postgres_recipe_id == pid
    assert hits[0].postgres_row is not None
    assert hits[0].postgres_row.name == "join-test-recipe"
