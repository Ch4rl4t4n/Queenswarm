"""Personal OS deployment preset — solo operator daily stack without revenue/commercial noise."""

from __future__ import annotations

from typing import Final

# Surfaces removed from Personal OS — commercial, revenue funnel, beta labs, legacy VC.
PERSONAL_OS_HIDDEN_FEATURES: Final[frozenset[str]] = frozenset(
    {
        # Multi-tenant B2B (also in solo hidden)
        "team_rbac",
        "enterprise_workspace",
        "accounts_admin",
        "skills_marketplace",
        "ugc_content_engine",
        # Operator monetization / Gumroad funnel — not used in Personal OS
        "billing_settings",
        "sharing_settings",
        "product_mission",
        "self_extending_tool_marketplace",
        "bee_gamification",
        "leaderboard",
        "content_pack_factory",
        "skills_export_factory",
        # Beta / frozen labs — reachable later via direct URL if needed
        "simulations",
        "jobs",
        "external_projects",
    },
)

# Daily Personal OS stack — agents, memory, integrations, harness meta.
PERSONAL_OS_CORE_FEATURES: Final[frozenset[str]] = frozenset(
    {
        "dashboard",
        "operator_cockpit",
        "swarms",
        "agents",
        "tasks",
        "workflows",
        "knowledge",
        "integrations",
        "connectors",
        "execution_studio",
        "ballroom",
        "recipes",
        "settings",
        "llm_keys_settings",
        "api_keys_settings",
        "ai_harness_dashboard",
        "pattern_explorer",
        "costs",
        "audit_settings",
        "platform_features_admin",
        "command_center_admin",
        "manual",
        "monitoring",
        "plugins",
        "free_first_routing",
        "sub_swarm_mind_ui",
        "dump_sleep",
        "overnight_voice_report",
        "auto_graphify",
        "selective_recall",
        "skill_factory",
        "design_system",
    },
)

PERSONAL_OS_OPTIONAL_FEATURES: Final[frozenset[str]] = frozenset(
    {
        "foragers",
        "episodic_memory",
        "slack_harness_trainer",
        "lsp_mcp_bridge",
        "rubric_templates",
        "venice_mcp_preset",
    },
)


def apply_personal_os_overrides(
    resolved: dict[str, bool],
    *,
    policy_overrides: dict[tuple[str, str], bool] | None = None,
    is_admin: bool = True,
) -> dict[str, bool]:
    """Merge Personal OS preset: hide commercial/revenue; enable daily operator stack."""

    overrides = dict(policy_overrides or {})
    out = dict(resolved)

    for key in PERSONAL_OS_HIDDEN_FEATURES:
        out[key] = False

    for key in PERSONAL_OS_CORE_FEATURES:
        env_key = (key, "environment")
        if env_key in overrides and not overrides[env_key]:
            out[key] = False
        else:
            out[key] = True

    for key in PERSONAL_OS_OPTIONAL_FEATURES:
        env_key = (key, "environment")
        if env_key in overrides:
            out[key] = bool(overrides[env_key])
        else:
            out[key] = bool(is_admin)

    out["platform_features_admin"] = bool(is_admin)
    out["accounts_admin"] = False
    out["command_center_admin"] = bool(is_admin)
    return out


def personal_os_mission_home_revenue_widgets_enabled() -> bool:
    """Return False when Personal OS strips Gumroad/catalog/revenue Mission Home widgets."""

    from app.core.config import settings

    if not settings.personal_os_mode_enabled:
        return True
    return False


def personal_os_skill_factory_commercial_enabled() -> bool:
    """Return False when Personal OS hides Gumroad launch/commercial Skill Factory tabs."""

    from app.core.config import settings

    if not settings.personal_os_mode_enabled:
        return True
    return False


__all__ = [
    "PERSONAL_OS_CORE_FEATURES",
    "PERSONAL_OS_HIDDEN_FEATURES",
    "PERSONAL_OS_OPTIONAL_FEATURES",
    "apply_personal_os_overrides",
    "personal_os_mission_home_revenue_widgets_enabled",
    "personal_os_skill_factory_commercial_enabled",
]
