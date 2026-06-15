"""API tests for MK6 catalog wave endpoint."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_marketing_catalog_wave_public() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/marketing/catalog-wave")
    assert response.status_code == 200
    body = response.json()
    assert body["mk6_target"] == 50
    assert "current_wave" in body
    assert "seed_total" in body
