"""AOS1 — Project harness profiles (marketing / factory / trading) for CBO + dispatch."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.infrastructure.persistence.models.tenant import Tenant

HarnessProfileId = Literal["marketing", "factory", "trading", "general"]

PROFILES_KEY = "harness_profiles"


class HarnessProjectProfileOut(BaseModel):
    """One reusable harness profile."""

    model_config = ConfigDict(extra="ignore")

    profile_id: HarnessProfileId
    label: str
    description: str
    skill_slugs: list[str] = Field(default_factory=list)
    cbo_lane: str = "ops"
    module_key: str = ""
    default_goal_hint: str = ""


class HarnessProfilesStateOut(BaseModel):
    """Tenant harness profile selection."""

    model_config = ConfigDict(extra="ignore")

    active_profile_id: HarnessProfileId = "general"
    profiles: list[HarnessProjectProfileOut] = Field(default_factory=list)
    updated_at: datetime | None = None


class HarnessProfilesPatchIn(BaseModel):
    """Patch active harness profile."""

    model_config = ConfigDict(extra="forbid")

    active_profile_id: HarnessProfileId


DEFAULT_PROFILES: tuple[HarnessProjectProfileOut, ...] = (
    HarnessProjectProfileOut(
        profile_id="marketing",
        label="Marketing harness",
        description="Content, publish queue, campaign simulate-first.",
        skill_slugs=["marketing-campaign-playbook", "multi-tenant-content-calendar", "execution-studio"],
        cbo_lane="marketing",
        module_key="marketing_automation",
        default_goal_hint="Draft and simulate marketing deliverables — no live publish without approval.",
    ),
    HarnessProjectProfileOut(
        profile_id="factory",
        label="Factory harness",
        description="Skill authoring, forge loop, export readiness.",
        skill_slugs=["skill-authoring-template", "self-review-loop", "product-mission"],
        cbo_lane="factory",
        module_key="content_factory",
        default_goal_hint="Build or refine one sellable skill — simulate-first, operator approves export.",
    ),
    HarnessProjectProfileOut(
        profile_id="trading",
        label="Trading harness",
        description="Paper discipline, risk gates, cockpit signals.",
        skill_slugs=["trading-paper-discipline", "decision-frameworks", "real-money-risk-gate"],
        cbo_lane="trading",
        module_key="trading_automation",
        default_goal_hint="Paper-mode analysis only — no live orders without explicit approval.",
    ),
    HarnessProjectProfileOut(
        profile_id="general",
        label="General operator",
        description="Balanced context + decision frameworks.",
        skill_slugs=["context", "decision-frameworks", "execution-studio"],
        cbo_lane="ops",
        module_key="research_workspace",
        default_goal_hint="Structured plan + simulate-first deliverable for operator review.",
    ),
)


def _profiles_root(tenant: Tenant | None) -> dict[str, Any]:
    if tenant is None:
        return {}
    root = dict(tenant.operator_settings or {})
    block = root.get(PROFILES_KEY)
    return dict(block) if isinstance(block, dict) else {}


def get_active_harness_profile(tenant: Tenant | None) -> HarnessProjectProfileOut:
    """Resolve active profile for CBO dispatch defaults."""

    block = _profiles_root(tenant)
    active = str(block.get("active_profile_id") or "general")
    for profile in DEFAULT_PROFILES:
        if profile.profile_id == active:
            return profile
    return DEFAULT_PROFILES[-1]


def compose_harness_profiles_state(tenant: Tenant | None) -> HarnessProfilesStateOut:
    """Read harness profiles for UI."""

    block = _profiles_root(tenant)
    active = str(block.get("active_profile_id") or "general")
    if active not in {"marketing", "factory", "trading", "general"}:
        active = "general"
    updated_raw = block.get("updated_at")
    updated: datetime | None = None
    if isinstance(updated_raw, str):
        try:
            updated = datetime.fromisoformat(updated_raw.replace("Z", "+00:00"))
        except ValueError:
            updated = None
    return HarnessProfilesStateOut(
        active_profile_id=active,  # type: ignore[arg-type]
        profiles=list(DEFAULT_PROFILES),
        updated_at=updated,
    )


def persist_active_harness_profile(tenant: Tenant, profile_id: HarnessProfileId) -> HarnessProfilesStateOut:
    """Set active profile (caller commits)."""

    root = dict(tenant.operator_settings or {})
    root[PROFILES_KEY] = {
        "active_profile_id": profile_id,
        "updated_at": datetime.now(tz=UTC).isoformat(),
    }
    tenant.operator_settings = root
    return compose_harness_profiles_state(tenant)


__all__ = [
    "HarnessProfilesPatchIn",
    "HarnessProfilesStateOut",
    "HarnessProjectProfileOut",
    "compose_harness_profiles_state",
    "get_active_harness_profile",
    "persist_active_harness_profile",
]
