"""ASGI tests for POST /api/v1/recipes/{id}/routine."""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from types import SimpleNamespace

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import settings
from app.main import app
from app.presentation.api.deps import get_db, require_dashboard_user_with_tenant_role
from app.presentation.api.routers import recipes as recipes_router


@pytest.fixture
def restore_app_overrides() -> None:
    """Reset DI overrides between tests."""

    app.dependency_overrides[require_dashboard_user_with_tenant_role] = lambda: {
        "user": SimpleNamespace(id=uuid.uuid4()),
        "tenant_id": uuid.uuid4(),
        "tenant_role": "owner",
        "permissions": ["*"],
        "membership": SimpleNamespace(role="owner"),
        "session": {"sub": "dash:test"},
    }
    yield
    app.dependency_overrides.clear()


def _mk_recipe() -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid.uuid4(),
        name="Verified — Lead Gen Lane",
        verified_at="2026-01-01T00:00:00Z",
    )


def _mk_routine(recipe_id: uuid.UUID) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid.uuid4(),
        name="recipe-lead-gen-lane",
        schedule_kind="cron",
    )


@pytest.mark.asyncio
async def test_recipe_routine_create_when_enabled_returns_201(
    restore_app_overrides: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Recipe → routine endpoint returns routine metadata."""

    recipe = _mk_recipe()
    routine = _mk_routine(recipe.id)

    async def mock_db() -> AsyncIterator[SimpleNamespace]:
        async def _scalar(_stmt):  # noqa: ANN001
            return recipe

        async def _commit() -> None:
            return None

        yield SimpleNamespace(scalar=_scalar, commit=_commit)

    async def _fake_create(*args, **kwargs):  # noqa: ANN002, ANN003
        del args
        return routine, {"roles": ["researcher", "critic"], "webhook_token": None}

    app.dependency_overrides[get_db] = mock_db
    monkeypatch.setattr(settings, "recipes_enabled", True)
    monkeypatch.setattr(settings, "routines_enabled", True)
    monkeypatch.setattr(recipes_router, "create_routine_from_recipe", _fake_create)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            f"/api/v1/recipes/{recipe.id}/routine",
            json={"schedule_kind": "cron", "cron_expr": "0 9 * * *", "enable_webhook": False},
            headers={"Authorization": "Bearer x"},
        )

    assert res.status_code == 201
    body = res.json()
    assert body["routine_id"] == str(routine.id)
    assert body["recipe_id"] == str(recipe.id)
    assert body["schedule_kind"] == "cron"
    assert body["roles"] == ["researcher", "critic"]
    assert body["webhook_token"] is None


@pytest.mark.asyncio
async def test_recipe_routine_create_when_routines_disabled_returns_403(
    restore_app_overrides: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Routine creation is blocked when ROUTINES_ENABLED=false."""

    recipe = _mk_recipe()

    async def mock_db() -> AsyncIterator[SimpleNamespace]:
        async def _scalar(_stmt):  # noqa: ANN001
            return recipe

        yield SimpleNamespace(scalar=_scalar, commit=lambda: None)

    app.dependency_overrides[get_db] = mock_db
    monkeypatch.setattr(settings, "recipes_enabled", True)
    monkeypatch.setattr(settings, "routines_enabled", False)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            f"/api/v1/recipes/{recipe.id}/routine",
            json={},
            headers={"Authorization": "Bearer x"},
        )

    assert res.status_code == 403


@pytest.mark.asyncio
async def test_recipe_routine_create_with_webhook_returns_token_once(
    restore_app_overrides: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """enable_webhook=true surfaces token in create response."""

    recipe = _mk_recipe()
    routine = _mk_routine(recipe.id)
    token = "qs-wh-test-token"

    async def mock_db() -> AsyncIterator[SimpleNamespace]:
        async def _scalar(_stmt):  # noqa: ANN001
            return recipe

        async def _commit() -> None:
            return None

        yield SimpleNamespace(scalar=_scalar, commit=_commit)

    async def _fake_create(*args, **kwargs):  # noqa: ANN002, ANN003
        del args, kwargs
        return routine, {"roles": ["researcher"], "webhook_token": token}

    app.dependency_overrides[get_db] = mock_db
    monkeypatch.setattr(settings, "recipes_enabled", True)
    monkeypatch.setattr(settings, "routines_enabled", True)
    monkeypatch.setattr(recipes_router, "create_routine_from_recipe", _fake_create)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            f"/api/v1/recipes/{recipe.id}/routine",
            json={"schedule_kind": "event", "enable_webhook": True},
            headers={"Authorization": "Bearer x"},
        )

    assert res.status_code == 201
    body = res.json()
    assert body["webhook_token"] == token
    assert body["webhook_url"] is not None
