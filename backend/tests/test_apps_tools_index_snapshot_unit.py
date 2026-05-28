"""Unit tests for unified Apps & Tools index snapshot."""

from __future__ import annotations

from unittest.mock import patch

from app.application.services.apps_tools_index_snapshot import compose_apps_tools_index_snapshot


def test_apps_tools_snapshot_returns_apps_tools_layers_only() -> None:
    """Snapshot keeps only apps_tools workspaces and their capabilities."""

    with patch("app.application.services.capability_registry.settings") as cap_settings, patch(
        "app.application.services.module_policy_packs.settings"
    ) as policy_settings:
        cap_settings.operator_control_plane_enabled = True
        cap_settings.agent_os_enabled = True
        cap_settings.hive_mind_enabled = True
        cap_settings.execution_studio_enabled = True
        cap_settings.social_publish_enabled = True
        cap_settings.publish_queue_enabled = True
        cap_settings.micro_saas_factory_enabled = False
        cap_settings.publish_performance_enabled = False
        cap_settings.trading_cockpit_enabled = False
        cap_settings.prediction_markets_enabled = False
        cap_settings.research_bee_enabled = False
        cap_settings.browser_harness_enabled = False
        cap_settings.live_lane_snapshot_enabled = False

        policy_settings.social_publish_enabled = True
        policy_settings.publish_queue_enabled = True
        policy_settings.daily_budget_usd = 10.0
        policy_settings.dynamic_connector_tool_timeout_ms = 12_000
        policy_settings.social_publish_rate_limit_window_sec = 86_400.0
        policy_settings.social_publish_live_daily_max_global = 30
        policy_settings.social_publish_trusted_auto_min_simulates = 5
        policy_settings.trading_cockpit_enabled = False
        policy_settings.prediction_markets_rate_limit_window_sec = 86_400.0
        policy_settings.prediction_markets_live_daily_max_global = 50
        policy_settings.prediction_markets_max_order_usd = 2500.0
        policy_settings.browser_harness_enabled = False
        policy_settings.alert_dispatch_cooldown_sec = 60
        policy_settings.browser_action_timeout_sec = 20
        policy_settings.browser_max_actions_per_session = 24
        policy_settings.micro_saas_factory_enabled = False
        policy_settings.publish_performance_enabled = False
        policy_settings.research_bee_enabled = False
        policy_settings.live_lane_snapshot_enabled = False

        snapshot = compose_apps_tools_index_snapshot()

    assert all(workspace.layer == "apps_tools" for workspace in snapshot.workspaces)
    module_keys = {workspace.module_key for workspace in snapshot.workspaces}
    assert module_keys
    assert all(capability.owner_module in module_keys for capability in snapshot.capabilities)
    assert all(policy.module_key in module_keys for policy in snapshot.policies)
