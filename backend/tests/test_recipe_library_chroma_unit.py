"""Recipe Library cosine helpers + Chroma upsert stitching."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from app.models.recipe import Recipe


def test_recipe_embedding_document_includes_steps() -> None:
    from app.services.recipe_chroma_sync import recipe_embedding_document

    recipe = Recipe(
        name="test-recipe",
        description=None,
        topic_tags=["api"],
        workflow_template={
            "steps": [
                {"description": "scrape hive"},
                {"name": "verify", "title": ""},
            ],
        },
        success_count=0,
        fail_count=0,
        avg_pollen_earned=0.0,
        embedding_id=None,
        created_by_agent_id=None,
        verified_at=None,
        last_used_at=None,
        is_deprecated=False,
    )
    blob = recipe_embedding_document(recipe)
    assert "test-recipe" in blob
    assert "scrape hive" in blob
    assert '"verify"' in blob or "verify" in blob


@pytest.mark.asyncio
async def test_find_similar_recipes_uses_config_threshold(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.core.chroma_client.settings.recipe_library_match_threshold",
        0.99,
    )

    async def fake_semantic(
        _: str,
        __: str,
        n_results: int = 5,
    ) -> list[dict]:
        del n_results
        return [
            {
                "id": "chrom-1",
                "document": "body",
                "metadata": {},
                "distance": 0.05,
            },
        ]

    monkeypatch.setattr("app.core.chroma_client.semantic_search", fake_semantic)

    from app.core.chroma_client import find_similar_recipes

    assert await find_similar_recipes("any task narrative") is None


@pytest.mark.asyncio
async def test_upsert_recipe_into_chroma_replaces_prior_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.services import recipe_chroma_sync as sync_mod

    prior = str(uuid.uuid4())
    rid = uuid.uuid4()
    recipe = Recipe(
        id=rid,
        name="r1",
        description="d",
        topic_tags=["t"],
        workflow_template={"steps": [{"description": "s"}]},
        success_count=0,
        fail_count=0,
        avg_pollen_earned=0.0,
        embedding_id=prior,
        created_by_agent_id=None,
        verified_at=datetime.now(tz=timezone.utc),
        last_used_at=None,
        is_deprecated=False,
    )

    delete_mock = AsyncMock()
    coll = AsyncMock()
    coll.delete = delete_mock

    chroma_client = AsyncMock()
    chroma_client.get_collection = AsyncMock(return_value=coll)

    async def fake_client() -> AsyncMock:
        return chroma_client

    monkeypatch.setattr(sync_mod, "get_chroma_client", fake_client)

    embeddings: list[str] = []

    async def fake_embed(text: str, metadata: dict, collection: str) -> str:
        del text, metadata
        embeddings.append(collection)
        return "fresh-embedding-id"

    monkeypatch.setattr(sync_mod, "embed_and_store", fake_embed)

    new_id = await sync_mod.upsert_recipe_into_chroma_library(recipe)
    assert new_id == "fresh-embedding-id"
    delete_mock.assert_awaited_once_with(ids=[prior])
    assert embeddings and embeddings[-1] == sync_mod.RECIPE_LIBRARY_COLLECTION


@pytest.mark.asyncio
async def test_delete_recipe_embedding_from_chroma_calls_chroma_delete(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Best-effort delete uses the same collection as Recipe Library upserts."""

    from app.services import recipe_chroma_sync as sync_mod

    delete_mock = AsyncMock()
    coll = AsyncMock()
    coll.delete = delete_mock
    chroma_client = AsyncMock()
    chroma_client.get_collection = AsyncMock(return_value=coll)

    async def fake_client() -> AsyncMock:
        return chroma_client

    monkeypatch.setattr(sync_mod, "get_chroma_client", fake_client)
    await sync_mod.delete_recipe_embedding_from_chroma(embedding_id="emb-del-1")
    delete_mock.assert_awaited_once_with(ids=["emb-del-1"])


@pytest.mark.asyncio
async def test_delete_recipe_embedding_from_chroma_noop_when_missing_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.services import recipe_chroma_sync as sync_mod

    client_mock = AsyncMock()
    monkeypatch.setattr(sync_mod, "get_chroma_client", client_mock)
    await sync_mod.delete_recipe_embedding_from_chroma(embedding_id=None)
    client_mock.assert_not_called()

