"""Unit tests for capability registry snapshot composition."""

from __future__ import annotations

from unittest.mock import patch

from app.application.services.capability_registry import compose_capability_registry_snapshot


def test_capability_registry_filters_disabled_by_default() -> None:
    """Default snapshot exposes only enabled capabilities/workspaces."""

    with patch("app.application.services.capability_registry.settings") as mock_settings:
        mock_settings.operator_control_plane_enabled = True
        mock_settings.agent_os_enabled = True
        mock_settings.hive_mind_enabled = True
        mock_settings.execution_studio_enabled = True
        mock_settings.social_publish_enabled = False
        mock_settings.publish_queue_enabled = False
        mock_settings.micro_saas_factory_enabled = False
        mock_settings.publish_performance_enabled = False
        mock_settings.trading_cockpit_enabled = False
        mock_settings.prediction_markets_enabled = False
        mock_settings.research_bee_enabled = False
        mock_settings.browser_harness_enabled = False
        mock_settings.live_lane_snapshot_enabled = False
        snapshot = compose_capability_registry_snapshot()

    capability_keys = {row.capability_key for row in snapshot.capabilities}
    assert "swarm.orchestrate.v1" in capability_keys
    assert "knowledge.hivemind.query.v1" in capability_keys
    assert "apps.marketing.publish_pipeline.v1" not in capability_keys
    assert all(row.enabled for row in snapshot.capabilities)
    assert all(row.enabled or row.capability_keys for row in snapshot.workspaces)


def test_capability_registry_includes_disabled_when_requested() -> None:
    """Explicit include_disabled returns complete catalog."""

    with patch("app.application.services.capability_registry.settings") as mock_settings:
        mock_settings.operator_control_plane_enabled = False
        mock_settings.agent_os_enabled = False
        mock_settings.hive_mind_enabled = False
        mock_settings.execution_studio_enabled = False
        mock_settings.social_publish_enabled = False
        mock_settings.publish_queue_enabled = False
        mock_settings.micro_saas_factory_enabled = False
        mock_settings.publish_performance_enabled = False
        mock_settings.trading_cockpit_enabled = False
        mock_settings.prediction_markets_enabled = False
        mock_settings.research_bee_enabled = False
        mock_settings.browser_harness_enabled = False
        mock_settings.live_lane_snapshot_enabled = False
        snapshot = compose_capability_registry_snapshot(include_disabled=True)

    assert len(snapshot.capabilities) >= 10
    assert any(not row.enabled for row in snapshot.capabilities)
    assert any(not row.enabled for row in snapshot.workspaces)


def test_capability_registry_includes_mcp_and_omni_publish_contract_drafts() -> None:
    """Registry exposes E36 draft contracts for MCP Ops Studio and omni publish extension."""

    with patch("app.application.services.capability_registry.settings") as mock_settings:
        mock_settings.operator_control_plane_enabled = True
        mock_settings.agent_os_enabled = True
        mock_settings.hive_mind_enabled = True
        mock_settings.execution_studio_enabled = True
        mock_settings.social_publish_enabled = True
        mock_settings.publish_queue_enabled = True
        mock_settings.micro_saas_factory_enabled = False
        mock_settings.publish_performance_enabled = False
        mock_settings.trading_cockpit_enabled = False
        mock_settings.prediction_markets_enabled = False
        mock_settings.research_bee_enabled = False
        mock_settings.browser_harness_enabled = False
        mock_settings.live_lane_snapshot_enabled = False
        snapshot = compose_capability_registry_snapshot(include_disabled=True)

    keys = {row.capability_key for row in snapshot.capabilities}
    assert "apps.mcp.catalog.discover.v1" in keys
    assert "apps.mcp.catalog.install.v1" in keys
    assert "apps.mcp.catalog.healthcheck.v1" in keys
    assert "apps.mcp.catalog.lifecycle.v1" in keys
    assert "apps.marketing.omni_publish.compose.v1" in keys
    assert "apps.marketing.omni_publish.schedule.v1" in keys
    assert "apps.marketing.omni_publish.receipts.v1" in keys

    workspace_keys = {row.module_key for row in snapshot.workspaces}
    assert "mcp_ops_studio" in workspace_keys
