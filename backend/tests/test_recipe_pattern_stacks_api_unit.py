"""API coverage for recipe orchestration pattern stacks route."""

from __future__ import annotations

import uuid
from collections.abc import Generator

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.presentation.api.deps import require_dashboard_session


@pytest.fixture
def recipe_auth_fixture() -> Generator[None, None, None]:
    """Dashboard session for recipe catalog routes."""

    app.dependency_overrides[require_dashboard_session] = lambda: {"sub": f"dash:{uuid.uuid4()}"}
    try:
        yield
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_recipe_pattern_stacks_route(
    monkeypatch: pytest.MonkeyPatch,
    recipe_auth_fixture: None,
) -> None:
    """Pattern stacks endpoint returns orchestration templates."""

    monkeypatch.setattr("app.presentation.api.routers.recipes.settings.recipes_enabled", True)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/recipes/pattern-stacks")

    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list)
    ids = {row["id"] for row in body}
    assert "exec_assistant" in ids
    assert "life_os" in ids
    exec_row = next(row for row in body if row["id"] == "exec_assistant")
    assert "planning" in exec_row["pattern_tags"]
