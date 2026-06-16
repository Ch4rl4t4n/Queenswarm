"""Unit tests for Track L analytics workspace snapshot."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest

from app.application.services.analytics_workspace_service import compose_analytics_workspace_snapshot
from app.core import config


@pytest.mark.asyncio
async def test_compose_analytics_workspace_snapshot_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config.settings, "analytics_workspace_enabled", False)
    snap = await compose_analytics_workspace_snapshot(AsyncMock(), tenant_id=uuid.uuid4())
    assert snap.enabled is False


@pytest.mark.asyncio
async def test_compose_analytics_workspace_snapshot_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config.settings, "analytics_workspace_enabled", True)
    with patch(
        "app.application.services.virtual_company_swarm_builder.list_built_wizard_templates",
        AsyncMock(return_value=["business-analytics-report"]),
    ):
        snap = await compose_analytics_workspace_snapshot(AsyncMock(), tenant_id=uuid.uuid4())
    assert snap.enabled is True
    assert snap.capability_key == "apps.analytics.decision_report.v1"
    assert snap.template_id == "business-analytics-report"
    assert snap.swarm_template_built is True
    assert "business-analytics-playbook" in snap.skill_slugs
    assert len(snap.panels) >= 4
    assert len(snap.connector_slots) >= 3
    assert any(action.id == "build_template" for action in snap.actions)


def test_module_policy_pack_includes_analytics_workspace() -> None:
    from app.application.services.module_policy_packs import get_module_policy_pack

    pack = get_module_policy_pack("analytics_workspace")
    assert pack is not None
    assert pack.risk_tier == "read"
    assert pack.requires_approval is True


def test_capability_registry_includes_analytics_workspace() -> None:
    from app.application.services.capability_registry import compose_capability_registry_snapshot

    snap = compose_capability_registry_snapshot(include_disabled=True)
    keys = {row.capability_key for row in snap.capabilities}
    assert "apps.analytics.decision_report.v1" in keys
    workspaces = {row.module_key for row in snap.workspaces}
    assert "analytics_workspace" in workspaces
