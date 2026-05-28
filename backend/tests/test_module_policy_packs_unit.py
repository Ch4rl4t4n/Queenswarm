"""Unit tests for module policy pack composition."""

from __future__ import annotations

from unittest.mock import patch

from app.application.services.module_policy_packs import (
    compose_module_policy_pack_snapshot,
    get_module_policy_pack,
)


def test_module_policy_packs_filter_disabled_by_default() -> None:
    """Snapshot returns only enabled module packs unless include_disabled is set."""

    with patch("app.application.services.module_policy_packs.settings") as mock_settings:
        mock_settings.social_publish_enabled = True
        mock_settings.publish_queue_enabled = True
        mock_settings.daily_budget_usd = 10.0
        mock_settings.dynamic_connector_tool_timeout_ms = 12_000
        mock_settings.social_publish_rate_limit_window_sec = 86_400.0
        mock_settings.social_publish_live_daily_max_global = 30
        mock_settings.social_publish_trusted_auto_min_simulates = 5
        mock_settings.trading_cockpit_enabled = False
        mock_settings.prediction_markets_rate_limit_window_sec = 86_400.0
        mock_settings.prediction_markets_live_daily_max_global = 50
        mock_settings.prediction_markets_max_order_usd = 2500.0
        mock_settings.browser_harness_enabled = False
        mock_settings.alert_dispatch_cooldown_sec = 60
        mock_settings.browser_action_timeout_sec = 20
        mock_settings.browser_max_actions_per_session = 24
        mock_settings.micro_saas_factory_enabled = False
        mock_settings.publish_performance_enabled = False
        mock_settings.research_bee_enabled = False
        mock_settings.live_lane_snapshot_enabled = False
        mock_settings.execution_studio_enabled = False
        snapshot = compose_module_policy_pack_snapshot()

    keys = {row.module_key for row in snapshot.modules}
    assert "marketing_automation" in keys
    assert "trading_automation" not in keys
    assert all(row.enabled for row in snapshot.modules)


def test_module_policy_pack_detail_uses_limits_from_settings() -> None:
    """Trading policy pack carries configured financial guardrail limits."""

    with patch("app.application.services.module_policy_packs.settings") as mock_settings:
        mock_settings.social_publish_enabled = True
        mock_settings.publish_queue_enabled = True
        mock_settings.daily_budget_usd = 25.0
        mock_settings.dynamic_connector_tool_timeout_ms = 9_000
        mock_settings.social_publish_rate_limit_window_sec = 86_400.0
        mock_settings.social_publish_live_daily_max_global = 40
        mock_settings.social_publish_trusted_auto_min_simulates = 7
        mock_settings.trading_cockpit_enabled = True
        mock_settings.prediction_markets_rate_limit_window_sec = 43_200.0
        mock_settings.prediction_markets_live_daily_max_global = 70
        mock_settings.prediction_markets_max_order_usd = 1500.0
        mock_settings.browser_harness_enabled = True
        mock_settings.alert_dispatch_cooldown_sec = 90
        mock_settings.browser_action_timeout_sec = 30
        mock_settings.browser_max_actions_per_session = 15
        mock_settings.micro_saas_factory_enabled = True
        mock_settings.publish_performance_enabled = False
        mock_settings.research_bee_enabled = True
        mock_settings.live_lane_snapshot_enabled = True
        mock_settings.execution_studio_enabled = True

        pack = get_module_policy_pack("trading_automation")

    assert pack is not None
    assert pack.risk_tier == "financial"
    assert pack.rate_limit_window_sec == 43_200
    assert pack.rate_limit_max_global == 70
    assert any("Max live order notional" in note for note in pack.notes)


def test_module_policy_snapshot_includes_mcp_ops_studio_when_execution_studio_enabled() -> None:
    """Policy snapshot exposes MCP Ops Studio governance pack when runtime is enabled."""

    with patch("app.application.services.module_policy_packs.settings") as mock_settings:
        mock_settings.social_publish_enabled = True
        mock_settings.publish_queue_enabled = True
        mock_settings.daily_budget_usd = 25.0
        mock_settings.dynamic_connector_tool_timeout_ms = 9_000
        mock_settings.social_publish_rate_limit_window_sec = 86_400.0
        mock_settings.social_publish_live_daily_max_global = 40
        mock_settings.social_publish_trusted_auto_min_simulates = 7
        mock_settings.trading_cockpit_enabled = False
        mock_settings.prediction_markets_rate_limit_window_sec = 43_200.0
        mock_settings.prediction_markets_live_daily_max_global = 70
        mock_settings.prediction_markets_max_order_usd = 1500.0
        mock_settings.browser_harness_enabled = False
        mock_settings.alert_dispatch_cooldown_sec = 90
        mock_settings.browser_action_timeout_sec = 30
        mock_settings.browser_max_actions_per_session = 15
        mock_settings.micro_saas_factory_enabled = False
        mock_settings.publish_performance_enabled = False
        mock_settings.research_bee_enabled = False
        mock_settings.live_lane_snapshot_enabled = False
        mock_settings.execution_studio_enabled = True

        snapshot = compose_module_policy_pack_snapshot()

    keys = {row.module_key for row in snapshot.modules}
    assert "mcp_ops_studio" in keys
