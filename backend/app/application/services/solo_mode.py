"""Solo operator deployment preset — one operator, full revenue stack, no multi-tenant B2B."""

from __future__ import annotations

from typing import Final

# Multi-tenant B2B platform only — NOT operator monetization (checkout, marketplace, UGC stay on).
SOLO_HIDDEN_FEATURES: Final[frozenset[str]] = frozenset(
    {
        "team_rbac",
        "enterprise_workspace",
        "accounts_admin",
    },
)

# Operator revenue + daily stack — forced ON in solo (env kill-switch still applies).
SOLO_CORE_FEATURES: Final[frozenset[str]] = frozenset(
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
        "skills_export_factory",
        # Operator monetization — available in solo for admin to earn
        "billing_settings",
        "sharing_settings",
        "skills_marketplace",
        "ugc_content_engine",
        "product_mission",
        "self_extending_tool_marketplace",
        "bee_gamification",
        "leaderboard",
        "design_system",
    },
)

# Extra modules — default ON for admin unless environment column overrides off.
SOLO_OPTIONAL_FEATURES: Final[frozenset[str]] = frozenset(
    {
        "foragers",
        "simulations",
        "jobs",
        "external_projects",
        "episodic_memory",
        "slack_harness_trainer",
        "lsp_mcp_bridge",
        "rubric_templates",
        "venice_mcp_preset",
    },
)


def apply_solo_mode_overrides(
    resolved: dict[str, bool],
    *,
    policy_overrides: dict[tuple[str, str], bool] | None = None,
    is_admin: bool = True,
) -> dict[str, bool]:
    """Merge solo preset: hide multi-tenant B2B; enable operator revenue + config for admin."""

    overrides = dict(policy_overrides or {})
    out = dict(resolved)

    for key in SOLO_HIDDEN_FEATURES:
        out[key] = False

    for key in SOLO_CORE_FEATURES:
        env_key = (key, "environment")
        if env_key in overrides and not overrides[env_key]:
            out[key] = False
        else:
            out[key] = True

    for key in SOLO_OPTIONAL_FEATURES:
        env_key = (key, "environment")
        if env_key in overrides:
            out[key] = bool(overrides[env_key])
        else:
            out[key] = bool(is_admin)

    out["platform_features_admin"] = bool(is_admin)
    out["accounts_admin"] = False
    out["command_center_admin"] = bool(is_admin)
    return out


__all__ = [
    "SOLO_CORE_FEATURES",
    "SOLO_HIDDEN_FEATURES",
    "SOLO_OPTIONAL_FEATURES",
    "apply_solo_mode_overrides",
]
