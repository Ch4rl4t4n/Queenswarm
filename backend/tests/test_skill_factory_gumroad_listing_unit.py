"""Unit tests for Skill Factory Gumroad draft listing."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.application.services.skill_factory_gumroad_listing import (
    _markdown_to_gumroad_html,
    create_gumroad_draft_from_skill,
    gumroad_listing_ready,
)


def test_markdown_to_gumroad_html_wraps_paragraphs() -> None:
    html_out = _markdown_to_gumroad_html("## Hook\n\nShort description.")
    assert "<h3>Hook</h3>" in html_out
    assert "<p>Short description.</p>" in html_out


@pytest.mark.asyncio
async def test_gumroad_listing_ready_requires_enabled(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.application.services.skill_factory_gumroad_listing.settings",
        SimpleNamespace(
            skill_factory_gumroad_listing_enabled=False,
            skill_factory_gumroad_access_token="token",
        ),
    )
    assert await gumroad_listing_ready(AsyncMock()) is False


@pytest.mark.asyncio
async def test_create_gumroad_draft_happy_path(monkeypatch) -> None:
    tenant_id = uuid4()
    skill_id = uuid4()
    skill = SimpleNamespace(
        id=skill_id,
        tenant_id=tenant_id,
        slug="newsletter-growth",
        title="Newsletter Growth",
        description="Automate loops",
        markdown_body="# Newsletter Growth\n",
        version="1.0.0",
        roles=["coder"],
        keywords=["newsletter"],
        source="verified_skill_forge",
        verified_at=None,
    )

    monkeypatch.setattr(
        "app.application.services.skill_factory_gumroad_listing.settings",
        SimpleNamespace(
            skill_factory_gumroad_listing_enabled=True,
            skill_factory_gumroad_access_token="test-token",
            skill_export_premium_price_eur_cents=1900,
            skill_factory_gumroad_attach_bundle_enabled=False,
            skill_factory_gumroad_cover_from_preview_enabled=False,
        ),
    )

    session = AsyncMock()
    session.get = AsyncMock(return_value=skill)
    session.scalar = AsyncMock(return_value=None)

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "success": True,
        "product": {"short_url": "https://gum.co/example", "id": "abc"},
    }

    mock_client = MagicMock()
    mock_client.post = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with (
        patch(
            "app.application.services.skill_factory_gumroad_listing._gumroad_token_for_session",
            new_callable=AsyncMock,
            return_value="test-token",
        ),
        patch(
            "app.application.services.skill_factory_gumroad_assets.enrich_gumroad_product_assets",
            new_callable=AsyncMock,
            return_value={},
        ),
        patch("app.application.services.skill_factory_gumroad_listing.httpx.AsyncClient", return_value=mock_client),
    ):
        out = await create_gumroad_draft_from_skill(session, tenant_id=tenant_id, skill_id=skill_id)

    assert out["ok"] is True
    assert out["product_url"] == "https://gum.co/example"
    mock_client.post.assert_awaited_once()
