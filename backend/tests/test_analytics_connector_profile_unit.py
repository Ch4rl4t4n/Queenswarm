"""Unit tests for Track L DA7 analytics connector profile."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.application.services.analytics_connector_profile_service import (
    compose_analytics_connector_profile_snapshot,
    connector_slots_from_profiles,
)
from app.infrastructure.persistence.models.dynamic_connector import DynamicConnector


def _ga4_row(*, user_id: uuid.UUID) -> DynamicConnector:
    row = DynamicConnector(
        id=uuid.uuid4(),
        dashboard_user_id=user_id,
        slug="ga4_data",
        display_name="GA4 Data API",
        base_url="https://analyticsdata.googleapis.com/v1beta",
        auth_type="oauth2",
        mcp_manifest={"tools": []},
        allowed_manager_slugs=["execution_operations"],
        is_active=True,
        is_builtin=False,
        builtin_kind=None,
        secrets_cipher=b"sealed",
        last_tested_at=datetime.now(tz=UTC),
    )
    return row


@pytest.mark.asyncio
async def test_compose_analytics_connector_profile_snapshot_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.core import config

    monkeypatch.setattr(config.settings, "analytics_connector_profile_enabled", False)
    snap = await compose_analytics_connector_profile_snapshot(
        AsyncMock(),
        dashboard_user_id=uuid.uuid4(),
    )
    assert snap.enabled is False


@pytest.mark.asyncio
async def test_compose_analytics_connector_profile_snapshot_with_ga4_active(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.core import config

    monkeypatch.setattr(config.settings, "analytics_connector_profile_enabled", True)
    user_id = uuid.uuid4()
    ga4 = _ga4_row(user_id=user_id)
    session = AsyncMock()
    session.scalars = AsyncMock(return_value=MagicMock(all=MagicMock(return_value=[ga4])))
    svc = MagicMock()
    svc._secrets_dict.return_value = {"oauth2_access_token": "tok", "ga4_property_id": "123456789"}

    with patch(
        "app.application.services.analytics_connector_profile_service.DynamicConnectorService",
        return_value=svc,
    ):
        snap = await compose_analytics_connector_profile_snapshot(session, dashboard_user_id=user_id)

    assert snap.enabled is True
    ga4_profile = next(row for row in snap.profiles if row.id == "ga4")
    assert ga4_profile.ready is True
    assert ga4_profile.status == "active"
    assert ga4_profile.property_hint == "123456789"
    assert snap.ready_count >= 1


def test_connector_slots_from_profiles_maps_ready_flag() -> None:
    from app.application.services.analytics_connector_profile_service import AnalyticsConnectorProfileOut

    slots = connector_slots_from_profiles(
        [
            AnalyticsConnectorProfileOut(
                id="ga4",
                label="GA4 Data API",
                mode="read_only",
                ready=True,
                status="active",
                skill_slug="ga4-analytics-playbook",
                configure_href="/integrations",
                detail="Read-only GA4.",
            ),
        ],
    )
    assert slots[0].ready is True
    assert slots[0].id == "ga4"
