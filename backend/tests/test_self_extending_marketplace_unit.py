"""Unit tests for self-extending tool marketplace flow."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from app.application.services.self_extending_marketplace import (
    SelfExtendingMarketplaceDisabledError,
    SelfExtendingUnsupportedProposalError,
    apply_intelligence_proposal,
    build_enriched_intelligence_scan,
    self_extending_marketplace_status,
)
from app.core import config as config_module
from app.infrastructure.connectors.dynamic.schemas import DynamicConnectorPublic


@pytest.mark.asyncio
async def test_build_enriched_intelligence_scan_adds_install_actions() -> None:
    user_id = uuid4()
    fake_scan = {
        "scanned_at": "2026-05-21T00:00:00+00:00",
        "proposal_count": 1,
        "proposals": [
            {
                "kind": "mcp_preset_skill",
                "target": "github_rest",
                "priority": "low",
                "rationale": "Consider preset doc.",
            },
        ],
    }
    fake_catalog = {
        "phase3_templates": [
            {"slug": "github_rest", "installed": False, "id": "github_rest"},
        ],
    }

    with patch(
        "app.application.services.self_extending_marketplace.run_intelligence_scan",
        return_value=fake_scan,
    ):
        with patch(
            "app.application.services.self_extending_marketplace.marketplace_catalog",
            new=AsyncMock(return_value=fake_catalog),
        ):
            with patch(
                "app.application.services.tool_gap_signal.list_tool_gaps",
                new=AsyncMock(return_value=[]),
            ):
                payload = await build_enriched_intelligence_scan(AsyncMock(), dashboard_user_id=user_id)

    proposal = payload["proposals"][0]
    assert proposal["action"] == "install_marketplace"
    assert proposal["entry_id"] == "github_rest"
    assert proposal["installed"] is False
    assert payload["self_extending"]["installable_count"] == 1


@pytest.mark.asyncio
async def test_apply_intelligence_proposal_installs_phase3_template() -> None:
    user_id = uuid4()
    connector = DynamicConnectorPublic.model_validate(
        {
            "id": str(uuid4()),
            "slug": "github_rest",
            "display_name": "GitHub REST",
            "base_url": "https://api.github.com",
            "auth_type": "bearer_token",
            "mcp_manifest": {"tools": []},
            "allowed_manager_slugs": [],
            "is_active": True,
            "is_builtin": False,
            "builtin_kind": None,
            "last_tested_at": None,
        },
    )

    with patch.object(config_module.settings, "self_extending_tool_marketplace_enabled", True):
        with patch(
            "app.application.services.self_extending_marketplace.install_marketplace_entry",
            new=AsyncMock(return_value=("installed", connector)),
        ):
            result = await apply_intelligence_proposal(
                AsyncMock(),
                dashboard_user_id=user_id,
                kind="mcp_preset_skill",
                target="github_rest",
            )

    assert result["status"] == "installed"
    assert result["target"] == "github_rest"
    assert result["connector"]["slug"] == "github_rest"


@pytest.mark.asyncio
async def test_apply_intelligence_proposal_rejects_unknown_kind() -> None:
    with patch.object(config_module.settings, "self_extending_tool_marketplace_enabled", True):
        with pytest.raises(SelfExtendingUnsupportedProposalError):
            await apply_intelligence_proposal(
                AsyncMock(),
                dashboard_user_id=uuid4(),
                kind="skill_keywords",
                target="foo",
            )


@pytest.mark.asyncio
async def test_apply_intelligence_proposal_when_disabled_raises() -> None:
    with patch.object(config_module.settings, "self_extending_tool_marketplace_enabled", False):
        with pytest.raises(SelfExtendingMarketplaceDisabledError):
            await apply_intelligence_proposal(
                AsyncMock(),
                dashboard_user_id=uuid4(),
                kind="mcp_preset_skill",
                target="github_rest",
            )


def test_self_extending_marketplace_status_shape() -> None:
    payload = self_extending_marketplace_status()
    assert payload["enabled"] is True
    assert "intelligence-apply" in payload["apply_path"]
