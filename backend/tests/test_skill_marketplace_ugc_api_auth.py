"""Authentication coverage for skill marketplace UGC router."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.presentation.api.deps import require_dashboard_session
from app.presentation.api.routers import skill_marketplace_ugc as ugc_router


@pytest.fixture
def restore_app_overrides() -> None:
    """Clear dependency overrides after each case."""

    yield
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_skill_marketplace_config_requires_dashboard_auth(restore_app_overrides: None) -> None:
    """Marketplace config route rejects anonymous callers."""

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/recipes/marketplace/config")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_skill_marketplace_config_allows_dashboard_session(
    restore_app_overrides: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Marketplace config route accepts dashboard sessions."""

    app.dependency_overrides[require_dashboard_session] = lambda: {"sub": "dash:operator"}
    monkeypatch.setattr(
        ugc_router,
        "build_marketplace_config",
        lambda: {
            "enabled": True,
            "platform_cut_bps": 2500,
            "platform_cut_display": "25%",
            "price_tiers_cents": [900, 1900, 2900],
        },
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/recipes/marketplace/config")

    assert response.status_code == 200
    assert response.json()["enabled"] is True
