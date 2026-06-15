"""API tests for public marketing eval endpoint (REV2)."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app

_VALID_MD = (
    "---\nname: test-workflow\ndescription: Eval test harness\n---\n\n"
    "# Title\n\nWhen to use: testing.\n\n1. Step one\n2. Step two\n3. Step three\n\n"
    "## Guardrails\n\nSimulate-first only.\n"
)


@pytest.mark.asyncio
async def test_marketing_public_eval_success() -> None:
    with patch(
        "app.presentation.api.routers.marketing.check_marketing_public_eval_rate_limit",
        AsyncMock(return_value=(True, "")),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/marketing/eval",
                json={"title": "Test", "workflow_markdown": _VALID_MD},
            )
    assert response.status_code == 200
    body = response.json()
    assert "eval_report_md" in body
    assert "passed" in body


@pytest.mark.asyncio
async def test_marketing_public_eval_rate_limited() -> None:
    with patch(
        "app.presentation.api.routers.marketing.check_marketing_public_eval_rate_limit",
        AsyncMock(return_value=(False, "Free eval limit reached.")),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/marketing/eval",
                json={"title": "Test", "workflow_markdown": _VALID_MD},
            )
    assert response.status_code == 429


@pytest.mark.asyncio
async def test_marketing_public_eval_validates_min_length() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/marketing/eval",
            json={"title": "T", "workflow_markdown": "short"},
        )
    assert response.status_code == 422
