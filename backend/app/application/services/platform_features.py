"""Platform mode feature catalog — internal operator vs commercial customer surfaces."""

from __future__ import annotations

from typing import Any, Literal

from app.application.services.billing import (
    TIER_ENTERPRISE,
    TIER_FREE,
    TIER_PRO,
    resolve_plan_features,
)
from app.infrastructure.persistence.models.billing import TenantSubscription

PlatformMode = Literal["internal", "commercial"]
FeatureRule = bool | Literal["admin"]
ProfileKey = Literal[
    "environment",
    "internal",
    "commercial_free",
    "commercial_pro",
    "commercial_enterprise",
]

_TIER_RANK: dict[str, int] = {
    TIER_FREE: 0,
    TIER_PRO: 1,
    TIER_ENTERPRISE: 2,
}

PROFILE_COLUMNS: list[dict[str, str]] = [
    {"key": "environment", "label": "Prostredie", "description": "Globálny kill-switch pre celé nasadenie", "tone": "cyan"},
    {"key": "internal", "label": "Operator · internal", "description": "Admin / revenue factory hive", "tone": "amber"},
    {"key": "commercial_free", "label": "Commercial · Free", "description": "Zákaznícky workspace — free tier", "tone": "zinc"},
    {"key": "commercial_pro", "label": "Commercial · Pro", "description": "Zákaznícky workspace — pro tier", "tone": "green"},
    {"key": "commercial_enterprise", "label": "Commercial · Enterprise", "description": "Zákaznícky workspace — enterprise", "tone": "purple"},
]

FEATURE_SECTIONS: list[dict[str, Any]] = [
    {
        "id": "overview",
        "label": "Overview",
        "tone": "cyan",
        "features": ["dashboard", "swarms", "costs", "monitoring", "leaderboard"],
    },
    {
        "id": "agents",
        "label": "Agents",
        "tone": "amber",
        "features": ["agents", "foragers"],
    },
    {
        "id": "execution",
        "label": "Execution",
        "tone": "magenta",
        "features": ["tasks", "workflows", "jobs", "simulations", "recipes"],
    },
    {
        "id": "knowledge",
        "label": "Knowledge",
        "tone": "green",
        "features": ["knowledge"],
    },
    {
        "id": "integrations",
        "label": "Integrations",
        "tone": "purple",
        "features": [
            "integrations",
            "connectors",
            "plugins",
            "external_projects",
            "skills_marketplace",
            "skills_export_factory",
            "product_mission",
            "ugc_content_engine",
            "sub_swarm_mind_ui",
            "bee_gamification",
        ],
    },
    {
        "id": "ballroom",
        "label": "Ballroom",
        "tone": "pollen",
        "features": ["ballroom", "dump_sleep", "free_first_routing", "auto_graphify"],
    },
    {
        "id": "settings",
        "label": "Settings",
        "tone": "zinc",
        "features": [
            "settings",
            "billing_settings",
            "team_rbac",
            "sharing_settings",
            "llm_keys_settings",
            "api_keys_settings",
            "audit_settings",
            "enterprise_workspace",
        ],
    },
    {
        "id": "system",
        "label": "System",
        "tone": "red",
        "features": ["manual", "design_system", "platform_features_admin", "accounts_admin", "command_center_admin"],
    },
]

FEATURE_LABELS: dict[str, str] = {
    "dashboard": "Dashboard",
    "swarms": "Swarms",
    "costs": "Costs & usage",
    "monitoring": "Advanced monitoring",
    "leaderboard": "Leaderboard",
    "agents": "Agents hub",
    "foragers": "Foragers",
    "tasks": "Tasks",
    "workflows": "Workflows",
    "jobs": "Async jobs",
    "simulations": "Simulations",
    "recipes": "Recipes",
    "knowledge": "Knowledge hub",
    "integrations": "Integrations hub",
    "connectors": "Connectors / MCP",
    "plugins": "Plugins lattice",
    "external_projects": "External projects",
    "skills_marketplace": "Skills marketplace",
    "skills_export_factory": "Skills export factory",
    "product_mission": "Product Mission factory",
    "ugc_content_engine": "UGC lead magnets",
    "sub_swarm_mind_ui": "Sub-swarm local hive mind",
    "bee_gamification": "Bee badges & gamification",
    "dump_sleep": "Dump & Sleep overnight ingest",
    "free_first_routing": "Free-First LLM routing + Cost Guardian",
    "auto_graphify": "Auto-Graphify folder ingest",
    "ballroom": "Realtime Ballroom",
    "settings": "Settings shell",
    "billing_settings": "Billing · usage",
    "team_rbac": "Team · RBAC",
    "sharing_settings": "Public sharing",
    "llm_keys_settings": "AI · voice keys",
    "api_keys_settings": "API · external keys",
    "audit_settings": "Audit log",
    "enterprise_workspace": "Enterprise · white-label",
    "manual": "Operator manual",
    "design_system": "Design system",
    "platform_features_admin": "Platform feature matrix",
    "accounts_admin": "Accounts CMS",
    "command_center_admin": "Command center",
}

# Single source of truth — keep in sync with frontend/lib/platform-features.ts
_FEATURE_CATALOG: dict[str, dict[str, Any]] = {
    "dashboard": {"internal": True, "commercial": True},
    "swarms": {"internal": True, "commercial": True},
    "agents": {"internal": True, "commercial": True},
    "foragers": {"internal": True, "commercial": True, "min_tier": TIER_PRO},
    "tasks": {"internal": True, "commercial": True},
    "knowledge": {"internal": True, "commercial": True},
    "integrations": {"internal": True, "commercial": True},
    "ballroom": {"internal": True, "commercial": True, "min_tier": TIER_PRO},
    "costs": {"internal": True, "commercial": True},
    "leaderboard": {"internal": True, "commercial": True, "min_tier": TIER_PRO},
    "manual": {"internal": True, "commercial": True},
    "settings": {"internal": True, "commercial": True},
    "monitoring": {"internal": "admin", "commercial": False},
    "workflows": {"internal": True, "commercial": True},
    "jobs": {"internal": True, "commercial": False},
    "simulations": {"internal": True, "commercial": False},
    "recipes": {"internal": True, "commercial": True, "min_tier": TIER_PRO},
    "external_projects": {"internal": True, "commercial": True, "min_tier": TIER_PRO},
    "plugins": {"internal": True, "commercial": True},
    "connectors": {"internal": True, "commercial": True},
    "skills_marketplace": {"internal": True, "commercial": True, "min_tier": TIER_PRO},
    "skills_export_factory": {"internal": True, "commercial": False},
    "product_mission": {"internal": True, "commercial": False},
    "ugc_content_engine": {"internal": True, "commercial": True, "min_tier": TIER_PRO},
    "sub_swarm_mind_ui": {"internal": True, "commercial": True},
    "bee_gamification": {"internal": True, "commercial": True, "min_tier": TIER_PRO},
    "dump_sleep": {"internal": True, "commercial": True, "min_tier": TIER_PRO},
    "free_first_routing": {"internal": True, "commercial": True},
    "auto_graphify": {"internal": True, "commercial": True, "min_tier": TIER_PRO},
    "team_rbac": {"internal": False, "commercial": True},
    "billing_settings": {"internal": False, "commercial": True},
    "sharing_settings": {"internal": False, "commercial": True},
    "llm_keys_settings": {"internal": True, "commercial": True},
    "api_keys_settings": {"internal": True, "commercial": True},
    "audit_settings": {"internal": "admin", "commercial": True},
    "enterprise_workspace": {"internal": True, "commercial": True, "min_tier": TIER_ENTERPRISE},
    "design_system": {"internal": "admin", "commercial": False},
    "platform_features_admin": {"internal": "admin", "commercial": False},
    "accounts_admin": {"internal": "admin", "commercial": False},
    "command_center_admin": {"internal": "admin", "commercial": False},
}

ROUTE_FEATURE_KEYS: dict[str, str] = {
    "/": "dashboard",
    "/swarms": "swarms",
    "/agents": "agents",
    "/foragers": "foragers",
    "/tasks": "tasks",
    "/knowledge": "knowledge",
    "/integrations": "integrations",
    "/ballroom": "ballroom",
    "/costs": "costs",
    "/leaderboard": "leaderboard",
    "/manual": "manual",
    "/monitoring": "monitoring",
    "/workflows": "workflows",
    "/jobs": "jobs",
    "/simulations": "simulations",
    "/recipes": "recipes",
    "/external-projects": "external_projects",
    "/plugins": "plugins",
    "/connectors": "connectors",
    "/hive-mind": "knowledge",
    "/outputs": "knowledge",
    "/learning": "knowledge",
    "/settings/billing": "billing_settings",
    "/settings/team": "team_rbac",
    "/settings/sharing": "sharing_settings",
    "/settings/llm-keys": "llm_keys_settings",
    "/settings/api-keys": "api_keys_settings",
    "/settings/audit": "audit_settings",
    "/settings/enterprise": "enterprise_workspace",
    "/settings/platform": "platform_features_admin",
    "/settings/accounts": "accounts_admin",
    "/settings/command-center": "command_center_admin",
    "/settings/capabilities": "settings",
    "/design-system": "design_system",
}


def normalize_platform_mode(raw: str | None) -> PlatformMode:
    """Coerce stored tenant mode to a supported literal."""

    key = str(raw or "internal").strip().lower()
    if key == "commercial":
        return "commercial"
    return "internal"


def profile_key_for(platform_mode: str, subscription_tier: str) -> str:
    """Map active tenant mode + tier to a matrix profile column."""

    mode = normalize_platform_mode(platform_mode)
    tier = str(subscription_tier or TIER_FREE).strip().lower()
    if mode == "internal":
        return "internal"
    if tier == TIER_ENTERPRISE:
        return "commercial_enterprise"
    if tier == TIER_PRO:
        return "commercial_pro"
    return "commercial_free"


def _tier_at_least(current: str, required: str) -> bool:
    """Return True when ``current`` tier meets or exceeds ``required``."""

    return _TIER_RANK.get(current, 0) >= _TIER_RANK.get(required, 0)


def _rule_for_mode(rule: FeatureRule, *, is_admin: bool) -> bool:
    """Evaluate catalog rule for one platform mode column."""

    if rule == "admin":
        return is_admin
    return bool(rule)


def catalog_default_for_profile(
    feature_key: str,
    profile_key: str,
    *,
    is_admin: bool = True,
) -> bool:
    """Return catalog-derived default for one matrix cell."""

    spec = _FEATURE_CATALOG.get(feature_key)
    if spec is None:
        return True
    if profile_key == "environment":
        return True
    if profile_key == "internal":
        return _rule_for_mode(spec.get("internal", False), is_admin=is_admin)  # type: ignore[arg-type]
    if profile_key.startswith("commercial_"):
        tier = profile_key.removeprefix("commercial_")
        enabled = _rule_for_mode(spec.get("commercial", False), is_admin=False)  # type: ignore[arg-type]
        min_tier = spec.get("min_tier")
        if enabled and isinstance(min_tier, str) and not _tier_at_least(tier, min_tier):
            enabled = False
        return enabled
    return True


def resolve_platform_features(
    *,
    platform_mode: str,
    is_admin: bool,
    subscription_tier: str = TIER_FREE,
    tier_features: dict[str, bool] | None = None,
    policy_overrides: dict[tuple[str, str], bool] | None = None,
) -> dict[str, bool]:
    """Merge catalog defaults with admin policy matrix and subscription gates."""

    mode = normalize_platform_mode(platform_mode)
    tier = str(subscription_tier or TIER_FREE).strip().lower()
    profile = profile_key_for(mode, tier)
    merged_tier_features = dict(tier_features or {})
    overrides = dict(policy_overrides or {})
    resolved: dict[str, bool] = {}

    for feature_key in _FEATURE_CATALOG:
        env_key = (feature_key, "environment")
        profile_key = (feature_key, profile)

        if env_key in overrides and not overrides[env_key]:
            enabled = False
        elif profile_key in overrides:
            enabled = bool(overrides[profile_key])
        else:
            enabled = catalog_default_for_profile(feature_key, profile, is_admin=is_admin)

        tier_flag = merged_tier_features.get(feature_key)
        if tier_flag is False:
            enabled = False
        resolved[feature_key] = enabled

    resolved["platform_features_admin"] = bool(is_admin and mode == "internal")
    resolved["accounts_admin"] = bool(is_admin and mode == "internal")
    resolved["command_center_admin"] = bool(is_admin and mode == "internal")
    return resolved


def resolve_platform_features_for_subscription(
    *,
    platform_mode: str,
    is_admin: bool,
    subscription: TenantSubscription,
    policy_overrides: dict[tuple[str, str], bool] | None = None,
) -> dict[str, bool]:
    """Resolve feature map from a tenant subscription row."""

    tier_features = resolve_plan_features(subscription)
    return resolve_platform_features(
        platform_mode=platform_mode,
        is_admin=is_admin,
        subscription_tier=str(subscription.tier),
        tier_features=tier_features,
        policy_overrides=policy_overrides,
    )


def build_feature_matrix(
    *,
    policy_overrides: dict[tuple[str, str], bool] | None = None,
) -> dict[str, Any]:
    """Build admin matrix payload with defaults and override sources."""

    overrides = dict(policy_overrides or {})
    rows: list[dict[str, Any]] = []
    for section in FEATURE_SECTIONS:
        for feature_key in section["features"]:
            cells: dict[str, dict[str, Any]] = {}
            for profile in PROFILE_COLUMNS:
                pk = str(profile["key"])
                override = overrides.get((feature_key, pk))
                default_enabled = catalog_default_for_profile(feature_key, pk, is_admin=True)
                cells[pk] = {
                    "enabled": bool(override) if override is not None else default_enabled,
                    "source": "override" if override is not None else "default",
                    "default_enabled": default_enabled,
                }
            rows.append(
                {
                    "section_id": str(section["id"]),
                    "section_label": str(section["label"]),
                    "section_tone": str(section["tone"]),
                    "feature_key": feature_key,
                    "label": FEATURE_LABELS.get(feature_key, feature_key),
                    "cells": cells,
                },
            )
    return {
        "profiles": PROFILE_COLUMNS,
        "sections": FEATURE_SECTIONS,
        "rows": rows,
    }


_PREVIEW_TIER_BY_PROFILE: dict[str, str] = {
    "internal": TIER_PRO,
    "commercial_free": TIER_FREE,
    "commercial_pro": TIER_PRO,
    "commercial_enterprise": TIER_ENTERPRISE,
}


def preview_features_for_profile(
    profile_key: str,
    *,
    policy_overrides: dict[tuple[str, str], bool] | None = None,
) -> dict[str, Any]:
    """Simulate effective feature map for one matrix profile column."""

    valid_profiles = {str(row["key"]) for row in PROFILE_COLUMNS}
    key = profile_key.strip()
    if key not in valid_profiles:
        msg = f"Unknown profile_key: {profile_key}"
        raise ValueError(msg)
    if key == "environment":
        msg = "Environment column is a global kill-switch — preview a tenant profile instead."
        raise ValueError(msg)

    platform_mode: PlatformMode = "internal" if key == "internal" else "commercial"
    tier = _PREVIEW_TIER_BY_PROFILE.get(key, TIER_FREE)
    is_admin = key == "internal"
    features = resolve_platform_features(
        platform_mode=platform_mode,
        is_admin=is_admin,
        subscription_tier=tier,
        policy_overrides=policy_overrides,
    )
    enabled_features = sorted(name for name, enabled in features.items() if enabled)
    disabled_features = sorted(name for name, enabled in features.items() if not enabled)
    return {
        "profile_key": key,
        "platform_mode": platform_mode,
        "subscription_tier": tier,
        "is_admin": is_admin,
        "features": features,
        "enabled_features": enabled_features,
        "disabled_features": disabled_features,
        "enabled_count": len(enabled_features),
        "disabled_count": len(disabled_features),
    }


def route_feature_key(pathname: str) -> str | None:
    """Map a dashboard pathname to a feature key when known."""

    normalized = (pathname or "/").split("#")[0] or "/"
    if normalized in ROUTE_FEATURE_KEYS:
        return ROUTE_FEATURE_KEYS[normalized]
    for prefix, key in sorted(ROUTE_FEATURE_KEYS.items(), key=lambda item: len(item[0]), reverse=True):
        if prefix != "/" and (normalized == prefix or normalized.startswith(f"{prefix}/")):
            return key
    if normalized.startswith("/settings"):
        return "settings"
    return None


def is_route_allowed(
    pathname: str,
    *,
    features: dict[str, bool],
) -> bool:
    """Return True when pathname is not gated or its feature is enabled."""

    key = route_feature_key(pathname)
    if key is None:
        return True
    return bool(features.get(key, True))


__all__ = [
    "FEATURE_LABELS",
    "FEATURE_SECTIONS",
    "PlatformMode",
    "PROFILE_COLUMNS",
    "ROUTE_FEATURE_KEYS",
    "build_feature_matrix",
    "catalog_default_for_profile",
    "is_route_allowed",
    "normalize_platform_mode",
    "preview_features_for_profile",
    "profile_key_for",
    "resolve_platform_features",
    "resolve_platform_features_for_subscription",
    "route_feature_key",
]
