"""API unit tests for public marketing catalog routes."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.application.services.marketing_product_catalog import MarketingCatalogOut, MarketingProductOut
from app.main import app


@pytest.mark.asyncio
async def test_marketing_products_list() -> None:
    catalog = MarketingCatalogOut(
        generated_from="/exports",
        product_count=1,
        products=[
            MarketingProductOut(
                slug="alpha-skill",
                kind="skill_factory",
                title="Alpha Skill",
                subtitle="Test",
                price="€9",
                score=90,
                featured=True,
            ),
        ],
    )

    with patch(
        "app.presentation.api.routers.marketing.build_catalog",
        return_value=catalog,
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/marketing/products")

    assert response.status_code == 200
    body = response.json()
    assert body["product_count"] == 1
    assert body["products"][0]["slug"] == "alpha-skill"


@pytest.mark.asyncio
async def test_marketing_product_detail_when_found_then_200() -> None:
    product = MarketingProductOut(
        slug="alpha-skill",
        kind="skill_factory",
        title="Alpha Skill",
        subtitle="Test",
        price="€9",
        score=90,
        featured=True,
    )

    with patch("app.presentation.api.routers.marketing.find_product", return_value=product):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/marketing/products/alpha-skill")

    assert response.status_code == 200
    assert response.json()["slug"] == "alpha-skill"

    with patch("app.presentation.api.routers.marketing.find_product", return_value=None):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/marketing/products/missing-slug")

    assert response.status_code == 404
