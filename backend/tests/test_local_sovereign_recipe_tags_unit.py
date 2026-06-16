"""Unit tests for Track M LOC14 local sovereign recipe tags."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.application.services.local_sovereign_recipe_tags_service import (
    LOCAL_ADAPTER_TOPIC_TAG,
    apply_local_adapter_tag_to_recipe,
    compose_sovereign_imitation_hints_snapshot,
    ensure_local_adapter_topic_tag,
    recipe_has_local_adapter_tag,
    sovereign_recipe_similarity_boost,
    tenant_uses_local_sovereign,
)
from app.core.config import settings
from app.infrastructure.persistence.models.recipe import Recipe


def test_ensure_local_adapter_topic_tag_idempotent() -> None:
    tags = ensure_local_adapter_topic_tag(["finance", LOCAL_ADAPTER_TOPIC_TAG])
    assert LOCAL_ADAPTER_TOPIC_TAG in tags
    assert tags.count(LOCAL_ADAPTER_TOPIC_TAG) == 1


def test_recipe_has_local_adapter_tag() -> None:
    recipe = Recipe(
        id=uuid.uuid4(),
        name="r",
        workflow_template={},
        topic_tags=["local-adapter"],
    )
    assert recipe_has_local_adapter_tag(recipe) is True


def test_sovereign_recipe_similarity_boost(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "local_sovereign_recipe_tags_enabled", True)
    monkeypatch.setattr(settings, "local_sovereign_recipe_imitation_boost", 0.1)
    recipe = Recipe(
        id=uuid.uuid4(),
        name="r",
        workflow_template={},
        topic_tags=[LOCAL_ADAPTER_TOPIC_TAG],
    )
    assert sovereign_recipe_similarity_boost(recipe=recipe, sovereign_mode=True) == 0.1
    assert sovereign_recipe_similarity_boost(recipe=recipe, sovereign_mode=False) == 0.0


@pytest.mark.asyncio
async def test_tenant_uses_local_sovereign_airgap(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "llm_airgap", True)
    assert await tenant_uses_local_sovereign(AsyncMock(), tenant_id=uuid.uuid4()) is True


@pytest.mark.asyncio
async def test_tenant_uses_local_sovereign_routing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "llm_airgap", False)
    with patch(
        "app.application.services.local_sovereign_recipe_tags_service.load_routing_config",
        new=AsyncMock(return_value={"routing_mode": "local_sovereign"}),
    ):
        assert await tenant_uses_local_sovereign(AsyncMock(), tenant_id=uuid.uuid4()) is True


@pytest.mark.asyncio
async def test_apply_local_adapter_tag_to_recipe(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "local_sovereign_recipe_tags_enabled", True)
    recipe_id = uuid.uuid4()
    recipe = Recipe(id=recipe_id, name="ops", workflow_template={}, topic_tags=["finance"])
    session = AsyncMock()
    session.get = AsyncMock(return_value=recipe)
    session.commit = AsyncMock()
    session.refresh = AsyncMock()

    out = await apply_local_adapter_tag_to_recipe(session, recipe_id=recipe_id)
    assert out is not None
    assert LOCAL_ADAPTER_TOPIC_TAG in out.topic_tags


@pytest.mark.asyncio
async def test_compose_sovereign_imitation_hints_snapshot(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "local_llm_enabled", True)
    monkeypatch.setattr(settings, "local_sovereign_recipe_tags_enabled", True)
    monkeypatch.setattr(settings, "llm_airgap", True)
    recipe = Recipe(
        id=uuid.uuid4(),
        name="local ops",
        workflow_template={},
        topic_tags=[LOCAL_ADAPTER_TOPIC_TAG],
        success_count=5,
        fail_count=1,
    )
    session = AsyncMock()
    with patch(
        "app.application.services.local_sovereign_recipe_tags_service.list_local_adapter_tagged_recipes",
        new=AsyncMock(return_value=[recipe]),
    ):
        snap = await compose_sovereign_imitation_hints_snapshot(session, tenant_id=uuid.uuid4())
    assert snap.enabled is True
    assert snap.sovereign_mode is True
    assert len(snap.hints) == 1


@pytest.mark.asyncio
async def test_list_local_adapter_tagged_recipes_query() -> None:
    from app.application.services.local_sovereign_recipe_tags_service import list_local_adapter_tagged_recipes

    recipe = Recipe(
        id=uuid.uuid4(),
        name="tagged",
        workflow_template={},
        topic_tags=[LOCAL_ADAPTER_TOPIC_TAG],
    )
    scalar_result = MagicMock()
    scalar_result.all.return_value = [recipe]
    session = AsyncMock()
    session.scalars = AsyncMock(return_value=scalar_result)
    rows = await list_local_adapter_tagged_recipes(session, limit=5)
    assert len(rows) == 1
