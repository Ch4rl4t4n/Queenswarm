"""Unit tests for tenant-scoped super tool routers."""

from __future__ import annotations

import uuid
from types import SimpleNamespace

import pytest

from app.application.services.super_tool_router import (
    SuperToolRouterCreateBody,
    create_super_tool_router,
    list_super_tool_routers,
    resolve_router_connector_slugs,
)


@pytest.mark.asyncio
async def test_super_router_crud_and_resolve() -> None:
    """Create router and resolve slugs for matching manager lane."""

    tenant = SimpleNamespace(
        id=uuid.uuid4(),
        operator_settings={},
    )

    async def _commit() -> None:
        return None

    session = SimpleNamespace(commit=_commit)

    body = SuperToolRouterCreateBody(
        name="Deep Research Stack",
        slug="deep_research_stack",
        description="Monid + Apify for research lane.",
        is_active=True,
        routing_mode="research_then_action",
        manager_slugs=["research_intelligence"],
        connector_slugs=["monid_mcp", "apify_store"],
    )
    created = await create_super_tool_router(session, tenant=tenant, body=body)  # type: ignore[arg-type]
    assert created.slug == "deep_research_stack"
    assert tenant.operator_settings["super_tool_routers"]["items"]

    rows = list_super_tool_routers(tenant)  # type: ignore[arg-type]
    assert len(rows) == 1

    slugs = resolve_router_connector_slugs(tenant, manager_slug="research_intelligence")  # type: ignore[arg-type]
    assert slugs == ("monid_mcp", "apify_store")

    empty = resolve_router_connector_slugs(tenant, manager_slug="personal_life")  # type: ignore[arg-type]
    assert empty == ()
