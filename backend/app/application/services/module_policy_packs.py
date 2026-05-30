"""Read-only module policy packs for Apps & Tools governance."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.core.config import settings

ModuleKey = Literal[
    "marketing_automation",
    "ecommerce_workspace",
    "mcp_ops_studio",
    "trading_automation",
    "browser_automation",
    "content_factory",
    "research_workspace",
    "live_lane",
]
ModuleRiskTier = Literal["read", "write", "publish", "financial"]


class ModulePolicyPackOut(BaseModel):
    """Policy limits and approval metadata for one workspace module."""

    model_config = ConfigDict(extra="ignore")

    module_key: ModuleKey
    label: str
    enabled: bool
    risk_tier: ModuleRiskTier
    requires_approval: bool
    cooldown_sec: int | None = None
    spend_cap_usd_24h: float | None = None
    time_limit_sec: int | None = None
    rate_limit_window_sec: int | None = None
    rate_limit_max_global: int | None = None
    notes: list[str] = Field(default_factory=list)


class ModulePolicyPackSnapshotOut(BaseModel):
    """Full policy-pack snapshot consumed by Apps & Tools headers."""

    model_config = ConfigDict(extra="ignore")

    generated_at: datetime
    version: str = "v1"
    modules: list[ModulePolicyPackOut] = Field(default_factory=list)


def _module_policy_catalog() -> list[ModulePolicyPackOut]:
    """Compose static policy packs from environment-driven settings."""

    return [
        ModulePolicyPackOut(
            module_key="marketing_automation",
            label="Marketing Automation",
            enabled=bool(settings.social_publish_enabled and settings.publish_queue_enabled),
            risk_tier="publish",
            requires_approval=True,
            spend_cap_usd_24h=float(settings.daily_budget_usd),
            time_limit_sec=max(1, int(settings.dynamic_connector_tool_timeout_ms / 1000)),
            rate_limit_window_sec=int(settings.social_publish_rate_limit_window_sec),
            rate_limit_max_global=settings.social_publish_live_daily_max_global,
            notes=[
                "Live publish is always simulation-first until explicit operator confirmation.",
                "Trusted auto-live still requires minimum successful simulate history.",
            ],
        ),
        ModulePolicyPackOut(
            module_key="ecommerce_workspace",
            label="E-commerce Ops",
            enabled=bool(settings.execution_studio_enabled),
            risk_tier="financial",
            requires_approval=True,
            spend_cap_usd_24h=float(settings.daily_budget_usd),
            time_limit_sec=max(1, int(settings.dynamic_connector_tool_timeout_ms / 1000)),
            notes=[
                "Shopify/Stripe live mutations require operator approval (real-money-risk-gate).",
                "Webhook ingress is verify-first; order sync is idempotent by event_id.",
            ],
        ),
        ModulePolicyPackOut(
            module_key="mcp_ops_studio",
            label="MCP Ops Studio",
            enabled=bool(settings.execution_studio_enabled),
            risk_tier="write",
            requires_approval=True,
            cooldown_sec=int(settings.alert_dispatch_cooldown_sec),
            time_limit_sec=max(1, int(settings.dynamic_connector_tool_timeout_ms / 1000)),
            rate_limit_window_sec=int(settings.social_publish_rate_limit_window_sec),
            rate_limit_max_global=settings.social_publish_live_daily_max_global,
            notes=[
                "MCP provider installation and lifecycle operations are approval-gated.",
                "Catalog discovery and health checks remain read-oriented but audited.",
            ],
        ),
        ModulePolicyPackOut(
            module_key="trading_automation",
            label="Trading Automation",
            enabled=bool(settings.trading_cockpit_enabled),
            risk_tier="financial",
            requires_approval=True,
            spend_cap_usd_24h=float(settings.daily_budget_usd),
            rate_limit_window_sec=int(settings.prediction_markets_rate_limit_window_sec),
            rate_limit_max_global=settings.prediction_markets_live_daily_max_global,
            notes=[
                f"Max live order notional: ${settings.prediction_markets_max_order_usd:.0f}.",
                "Prediction-market live mode remains off by default.",
            ],
        ),
        ModulePolicyPackOut(
            module_key="browser_automation",
            label="Browser Automation",
            enabled=bool(settings.browser_harness_enabled),
            risk_tier="write",
            requires_approval=True,
            cooldown_sec=int(settings.alert_dispatch_cooldown_sec),
            time_limit_sec=settings.browser_action_timeout_sec,
            rate_limit_max_global=settings.browser_max_actions_per_session,
            notes=[
                "Browser actions are bounded by per-session action caps and domain allowlists.",
                "Live browser steps require operator confirmation in approval lane.",
            ],
        ),
        ModulePolicyPackOut(
            module_key="content_factory",
            label="Content Factory",
            enabled=bool(settings.micro_saas_factory_enabled or settings.publish_performance_enabled),
            risk_tier="write",
            requires_approval=True,
            spend_cap_usd_24h=float(settings.daily_budget_usd),
            time_limit_sec=max(1, int(settings.dynamic_connector_tool_timeout_ms / 1000)),
            notes=[
                "Content factory runs reuse connector and simulation guardrails.",
            ],
        ),
        ModulePolicyPackOut(
            module_key="research_workspace",
            label="Research Workspace",
            enabled=bool(settings.research_bee_enabled),
            risk_tier="write",
            requires_approval=True,
            spend_cap_usd_24h=float(settings.daily_budget_usd),
            time_limit_sec=max(1, int(settings.dynamic_connector_tool_timeout_ms / 1000)),
            notes=[
                "Research outputs are structured briefs; optional persistence is operator-controlled.",
            ],
        ),
        ModulePolicyPackOut(
            module_key="live_lane",
            label="Live Lane",
            enabled=bool(settings.live_lane_snapshot_enabled),
            risk_tier="financial",
            requires_approval=True,
            cooldown_sec=int(settings.alert_dispatch_cooldown_sec),
            rate_limit_window_sec=int(settings.prediction_markets_rate_limit_window_sec),
            rate_limit_max_global=settings.prediction_markets_live_daily_max_global,
            notes=[
                "Final lane before high-risk live operations.",
            ],
        ),
    ]


def compose_module_policy_pack_snapshot(*, include_disabled: bool = False) -> ModulePolicyPackSnapshotOut:
    """Return module policy packs for Apps & Tools workspace headers."""

    modules = _module_policy_catalog()
    if not include_disabled:
        modules = [row for row in modules if row.enabled]
    return ModulePolicyPackSnapshotOut(
        generated_at=datetime.now(tz=UTC),
        modules=modules,
    )


def get_module_policy_pack(module_key: ModuleKey) -> ModulePolicyPackOut | None:
    """Return one module policy pack by key."""

    for row in _module_policy_catalog():
        if row.module_key == module_key:
            return row
    return None


__all__ = [
    "ModuleKey",
    "ModulePolicyPackOut",
    "ModulePolicyPackSnapshotOut",
    "compose_module_policy_pack_snapshot",
    "get_module_policy_pack",
]
