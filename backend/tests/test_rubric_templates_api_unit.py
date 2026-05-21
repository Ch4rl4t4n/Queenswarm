"""API coverage for rubric template harness routes."""

from __future__ import annotations

import uuid
from collections.abc import Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.presentation.api.deps import require_dashboard_user_with_tenant_role, require_subject


@pytest.fixture
def rubric_auth_fixture() -> Generator[None, None, None]:
    """Tenant-scoped dashboard principal."""

    actor = uuid.uuid4()
    tenant = uuid.uuid4()
    app.dependency_overrides[require_subject] = lambda: f"dash:{actor}"
    app.dependency_overrides[require_dashboard_user_with_tenant_role] = lambda: {
        "tenant_id": tenant,
        "tenant_role": "owner",
        "permissions": [],
        "user": MagicMock(),
    }
    try:
        yield
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_rubric_templates_list_route(rubric_auth_fixture: None) -> None:
    """List endpoint returns curated rubric catalog."""

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/harness/rubric-templates")

    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list)
    assert any(row["id"] == "design-ux" for row in body)


@pytest.mark.asyncio
async def test_rubric_templates_apply_route(rubric_auth_fixture: None) -> None:
    """Apply endpoint merges template metadata into criteria."""

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/harness/rubric-templates/apply",
            json={"template_id": "product-spec", "base_criteria": {}},
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["evaluation_criteria"]["rubric_template_id"] == "product-spec"


@pytest.mark.asyncio
async def test_rubric_templates_evaluate_route(
    rubric_auth_fixture: None,
) -> None:
    """Evaluate endpoint delegates to rubric service."""

    with patch(
        "app.presentation.api.routers.harness.evaluate_text_with_rubric",
        new=AsyncMock(
            return_value={
                "is_valid": True,
                "confidence": 0.9,
                "feedback": "Strong.",
                "rubric_template_id": "copy-marketing",
            },
        ),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/harness/rubric-templates/evaluate",
                json={
                    "template_id": "copy-marketing",
                    "text": "Ship verified agent swarms with pollen rewards.",
                },
            )

    assert resp.status_code == 200
    assert resp.json()["is_valid"] is True
