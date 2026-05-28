"""Authentication coverage for paper trading router."""

from __future__ import annotations

from collections.abc import AsyncIterator
from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.presentation.api.deps import get_db, require_dashboard_session
from app.presentation.api.routers import paper_trading as paper_trading_router


@pytest.fixture
def restore_app_overrides() -> None:
    """Clear dependency overrides after each case."""

    yield
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_paper_trading_summary_requires_dashboard_auth(restore_app_overrides: None) -> None:
    """Paper trading routes reject anonymous callers."""

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/paper-trading/summary")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_paper_trading_summary_allows_dashboard_session(
    restore_app_overrides: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Paper trading routes accept dashboard sessions."""

    async def _db() -> AsyncIterator[AsyncMock]:
        yield AsyncMock()

    app.dependency_overrides[require_dashboard_session] = lambda: {"sub": "dash:operator"}
    app.dependency_overrides[get_db] = _db
    monkeypatch.setattr(paper_trading_router, "_ensure_paper_trading_enabled", lambda: None)

    async def _fake_summary(_db: object) -> dict[str, object]:
        return {"ok": True, "projects": 0}

    monkeypatch.setattr(paper_trading_router, "build_dashboard_paper_summary", _fake_summary)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/paper-trading/summary")

    assert response.status_code == 200
    assert response.json() == {"ok": True, "projects": 0}
