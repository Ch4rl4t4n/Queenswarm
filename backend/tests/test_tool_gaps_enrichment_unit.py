"""Unit tests for tool gaps API and forager enrichment."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from app.application.services.forager_intelligence_v2 import compose_forager_v2_snapshot
from app.application.services.self_extending_marketplace import build_enriched_intelligence_scan
from app.application.services.tool_gap_signal import integrations_href_for_template


def test_integrations_href_for_template() -> None:
    assert integrations_href_for_template("github_rest") == "/integrations?tab=marketplace&template=github_rest"
    assert integrations_href_for_template() == "/integrations?tab=marketplace"


@pytest.mark.asyncio
async def test_build_enriched_scan_merges_tool_gaps() -> None:
    tenant_id = uuid4()
    user_id = uuid4()
    fake_scan = {"proposal_count": 0, "proposals": []}
    fake_catalog = {"phase3_templates": [{"slug": "github_rest", "installed": False, "id": "github_rest"}]}
    fake_gaps = [
        {
            "kind": "connector_missing",
            "connector_slug": "github_rest",
            "tool_name": "invoke",
            "message": "dynamic_invoke_error: connector `github_rest` inactive or unknown",
            "suggested_template_id": "github_rest",
            "occurrences": 2,
        },
    ]

    with (
        patch(
            "app.application.services.self_extending_marketplace.run_intelligence_scan",
            return_value=fake_scan,
        ),
        patch(
            "app.application.services.self_extending_marketplace.marketplace_catalog",
            new=AsyncMock(return_value=fake_catalog),
        ),
        patch(
            "app.application.services.tool_gap_signal.list_tool_gaps",
            new=AsyncMock(return_value=fake_gaps),
        ),
    ):
        payload = await build_enriched_intelligence_scan(
            AsyncMock(),
            dashboard_user_id=user_id,
            tenant_id=tenant_id,
        )

    assert any(row.get("entry_id") == "github_rest" for row in payload["proposals"])
    assert payload["self_extending"]["installable_count"] >= 1


@pytest.mark.asyncio
async def test_forager_v2_includes_session_tool_gaps() -> None:
    tenant_id = uuid4()
    tenant = SimpleNamespace(id=tenant_id, operator_settings={})

    with (
        patch("app.application.services.forager_intelligence_v2.settings") as mock_settings,
        patch("app.application.services.forager_intelligence_v2.run_intelligence_scan") as scan_mock,
        patch(
            "app.application.services.prediction_market_trading.build_prediction_markets_status_snapshot",
            new=AsyncMock(return_value={"connectors_active": {}}),
        ),
        patch(
            "app.application.services.tool_gap_signal.list_tool_gaps",
            new=AsyncMock(
                return_value=[
                    {
                        "kind": "connector_missing",
                        "connector_slug": "github_rest",
                        "message": "missing connector",
                        "suggested_template_id": "github_rest",
                    },
                ],
            ),
        ),
    ):
        mock_settings.forager_intelligence_v2_enabled = True
        scan_mock.return_value = {"proposal_count": 0, "proposals": []}
        snapshot = await compose_forager_v2_snapshot(
            AsyncMock(),
            tenant=tenant,
            dashboard_user_id=uuid4(),
        )

    assert any("github_rest" in gap for gap in snapshot.connector_gaps)
    assert any(row.target == "github_rest" for row in snapshot.proposals)
