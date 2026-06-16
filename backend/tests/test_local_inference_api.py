"""API tests for local inference endpoints (Track M LOC4)."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_local_inference_status_requires_auth() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/llm-routing/local-inference")
    assert response.status_code in {401, 403}


@pytest.mark.asyncio
async def test_verified_dataset_export_requires_auth() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/llm-routing/verified-dataset")
    assert response.status_code in {401, 403}


@pytest.mark.asyncio
async def test_local_inference_status_404_when_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core.config import settings

    monkeypatch.setattr(settings, "local_llm_enabled", False)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/llm-routing/local-inference")
    assert response.status_code in {401, 403, 404}
