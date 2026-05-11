"""Unit + ASGI tests for Phase E Learning Engine (rewards, learning API, recipes facade)."""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.deps import get_db
from app.core.jwt_tokens import create_access_token
from app.learning.reward_tracker import (
    allocate_pollen_pool,
    maynard_cross_weights,
    merge_confidence_with_performance,
)
from app.main import app
from app.services.recipe_write import RecipeWriteConflictError


@pytest.fixture
def restore_app_overrides() -> None:
    yield
    app.dependency_overrides.clear()


def test_maynard_cross_weights_uniform_when_all_zero() -> None:
    a, b = uuid.uuid4(), uuid.uuid4()
    w = maynard_cross_weights({a: 0.0, b: 0.0})
    assert abs(w[a] - 0.5) < 1e-9
    assert abs(w[b] - 0.5) < 1e-9


def test_maynard_cross_weights_proportional_when_positive() -> None:
    a, b = uuid.uuid4(), uuid.uuid4()
    w = maynard_cross_weights({a: 1.0, b: 3.0})
    assert abs(w[a] - 0.25) < 1e-9
    assert abs(w[b] - 0.75) < 1e-9


def test_allocate_pollen_pool_empty_weights_or_zero_pool() -> None:
    aid = uuid.uuid4()
    assert allocate_pollen_pool(10.0, {}) == {}
    assert allocate_pollen_pool(0.0, {aid: 1.0}) == {}


def test_merge_confidence_with_performance_blends_signals() -> None:
    aid = uuid.uuid4()
    agent = SimpleNamespace(performance_score=1.0, pollen_points=100.0)
    out = merge_confidence_with_performance({aid: agent}, {aid: 1.0})
    assert aid in out
    assert out[aid] > 0.9


@pytest.mark.asyncio
async def test_learning_rewards_allocate_requires_bearer(restore_app_overrides: None) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/learning/rewards/allocate",
            json={
                "pool": 10.0,
                "signals": [{"agent_id": str(uuid.uuid4()), "signal": 0.5}],
            },
        )
    assert response.status_code in {401, 403}


@pytest.mark.asyncio
async def test_learning_autosave_returns_409_on_name_conflict(
    restore_app_overrides: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def boom(*args, **kwargs):  # noqa: ANN002,ANN003
        del args, kwargs
        raise RecipeWriteConflictError("dup-name")

    monkeypatch.setattr("app.api.routers.learning.autosave_verified_workflow", boom)

    async def mock_db() -> AsyncIterator[AsyncMock]:
        session = AsyncMock()
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        yield session

    app.dependency_overrides[get_db] = mock_db
    token, _ = create_access_token(subject="pytest")
    headers = {"Authorization": f"Bearer {token}"}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/learning/recipes/autosave",
            headers=headers,
            json={
                "name": "x",
                "workflow_template": {"steps": []},
            },
        )

    assert response.status_code == 409
    assert "dup-name" in response.json()["detail"]

