"""Unit tests for Gumroad publish API."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.application.services.skill_factory_gumroad_listing import (
    persist_gumroad_listing_ref,
    publish_gumroad_listing_for_skill,
    read_gumroad_listing_ref,
)


def test_read_gumroad_listing_ref() -> None:
    opp = SimpleNamespace(
        source_refs=[{"kind": "gumroad_listing", "product_id": "abc", "published": False}],
    )
    ref = read_gumroad_listing_ref(opp)  # type: ignore[arg-type]
    assert ref is not None
    assert ref["product_id"] == "abc"


def test_persist_gumroad_listing_ref_replaces_existing() -> None:
    opp = SimpleNamespace(source_refs=[{"kind": "gumroad_listing", "product_id": "old"}])
    persist_gumroad_listing_ref(opp, product_id="new", product_url="https://gum.co/x", published=True)  # type: ignore[arg-type]
    assert opp.source_refs[-1]["product_id"] == "new"
    assert opp.source_refs[-1]["published"] is True


@pytest.mark.asyncio
async def test_publish_gumroad_listing_uses_stored_product_id(monkeypatch) -> None:
    tenant_id = uuid4()
    skill_id = uuid4()
    opportunity = SimpleNamespace(
        tenant_id=tenant_id,
        tenant_skill_id=skill_id,
        source_refs=[{"kind": "gumroad_listing", "product_id": "prod-123", "product_url": "https://gum.co/x"}],
    )
    skill = SimpleNamespace(id=skill_id, tenant_id=tenant_id)

    monkeypatch.setattr(
        "app.application.services.skill_factory_gumroad_listing.settings",
        SimpleNamespace(skill_factory_gumroad_publish_enabled=True),
    )

    session = AsyncMock()
    session.get = AsyncMock(return_value=skill)
    session.scalar = AsyncMock(return_value=opportunity)

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "success": True,
        "product": {"published": True, "short_url": "https://gum.co/live", "id": "prod-123"},
    }
    mock_client = MagicMock()
    mock_client.put = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with (
        patch(
            "app.application.services.skill_factory_gumroad_listing._gumroad_token_for_session",
            new_callable=AsyncMock,
            return_value="token",
        ),
        patch("app.application.services.skill_factory_gumroad_listing.httpx.AsyncClient", return_value=mock_client),
    ):
        out = await publish_gumroad_listing_for_skill(session, tenant_id=tenant_id, skill_id=skill_id)

    assert out["ok"] is True
    assert out["short_url"] == "https://gum.co/live"
    session.flush.assert_awaited_once()
