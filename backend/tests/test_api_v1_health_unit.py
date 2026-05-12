"""Versioned liveness surface under /api/v1."""

from __future__ import annotations

import pytest

from app.api.v1 import api_v1_health


@pytest.mark.asyncio
async def test_api_v1_health_payload() -> None:
    """Mirrors GET /api/v1/health without booting the full app lifespan."""

    payload = await api_v1_health()
    assert payload["status"] == "healthy"
    assert payload["service"] == "queenswarm-api"
    assert "domain" in payload
