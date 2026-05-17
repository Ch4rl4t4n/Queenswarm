"""Request-context middleware enterprise correlation headers."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.presentation.api.middleware import request_context as request_ctx_mod


@pytest.mark.asyncio
async def test_request_context_sets_correlation_and_trace_headers(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        request_ctx_mod,
        "decode_jwt_optional_typ",
        lambda _token: {
            "sub": "dash:11111111-1111-4111-8111-111111111111",
            "tenant_id": "22222222-2222-4222-8222-222222222222",
        },
    )
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/health/live",
            headers={
                "Authorization": "Bearer stub-token",
                "X-Correlation-ID": "corr-123",
            },
        )
    assert response.status_code == 200
    assert response.headers.get("X-Correlation-ID") == "corr-123"
    assert response.headers.get("X-Request-ID")
    assert response.headers.get("Traceparent")
