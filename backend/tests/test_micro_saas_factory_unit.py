"""Micro-SaaS Factory unit tests."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.application.services.micro_saas_factory import (
    build_public_micro_saas_blueprint,
    compose_micro_saas_factory_snapshot,
)


def test_build_public_micro_saas_blueprint_enabled() -> None:
    with patch("app.application.services.micro_saas_factory.settings") as mock_settings:
        mock_settings.micro_saas_factory_enabled = True
        blueprint = build_public_micro_saas_blueprint()

    assert blueprint.enabled is True
    assert len(blueprint.phases) == 5
    assert blueprint.stack.get("auth") == "JWT dashboard sessions"


@pytest.mark.asyncio
async def test_compose_micro_saas_factory_snapshot_progress() -> None:
    session = AsyncMock()
    tenant = SimpleNamespace(
        operator_settings={
            "virtual_company_profile": {
                "brand_name": "SaaS Co",
                "onboarded": True,
                "industry": "SaaS",
                "focus_areas": ["product"],
                "risk_tolerance": "medium",
                "primary_goal": "Ship MVP",
            },
        },
    )

    with (
        patch("app.application.services.micro_saas_factory.settings") as mock_settings,
        patch(
            "app.application.services.micro_saas_factory.DynamicConnectorService",
        ) as connector_cls,
    ):
        mock_settings.micro_saas_factory_enabled = True
        mock_settings.domain = "queenswarm.love"
        connector_cls.return_value.fetch_by_slug = AsyncMock(return_value=None)

        snap = await compose_micro_saas_factory_snapshot(session, tenant=tenant)

    assert snap.enabled is True
    assert snap.product_name == "SaaS Co"
    assert snap.progress_pct >= 50
    assert len(snap.steps) == 4


@pytest.mark.asyncio
async def test_compose_micro_saas_factory_disabled() -> None:
    with patch("app.application.services.micro_saas_factory.settings") as mock_settings:
        mock_settings.micro_saas_factory_enabled = False
        snap = await compose_micro_saas_factory_snapshot(AsyncMock(), tenant=None)

    assert snap.enabled is False
