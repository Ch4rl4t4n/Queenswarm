"""Subscription tiers, usage aggregation, and plan limit enforcement."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.persistence.models.cost import CostRecord
from app.infrastructure.persistence.models.external_output import ExternalOutput
from app.infrastructure.persistence.models.external_project import ExternalProjectRunAudit
from app.infrastructure.persistence.models.knowledge import KnowledgeItem
from app.infrastructure.persistence.models.billing import TenantSubscription
from app.infrastructure.persistence.models.supervisor_session import SupervisorSession
from app.infrastructure.persistence.models.agent import Agent
from app.infrastructure.persistence.models.swarm import SubSwarm
from app.infrastructure.persistence.models.tenant import Tenant


def _normalize_platform_mode(raw: str | None) -> str:
    """Coerce tenant mode without importing platform_features (avoids circular import)."""

    key = str(raw or "internal").strip().lower()
    return "commercial" if key == "commercial" else "internal"

TIER_FREE = "free"
TIER_PRO = "pro"
TIER_ENTERPRISE = "enterprise"


@dataclass(frozen=True, slots=True)
class PlanDefinition:
    """Static plan definition for usage and feature gating."""

    tier: str
    label: str
    monthly_token_soft: int
    monthly_token_hard: int
    monthly_supervisor_sessions_soft: int
    monthly_supervisor_sessions_hard: int
    monthly_external_calls_soft: int
    monthly_external_calls_hard: int
    storage_mb_soft: int
    storage_mb_hard: int
    max_agents_soft: int
    max_agents_hard: int
    max_swarms_soft: int
    max_swarms_hard: int
    features: dict[str, bool]


_PLANS: dict[str, PlanDefinition] = {
    TIER_FREE: PlanDefinition(
        tier=TIER_FREE,
        label="Free",
        monthly_token_soft=150_000,
        monthly_token_hard=250_000,
        monthly_supervisor_sessions_soft=50,
        monthly_supervisor_sessions_hard=80,
        monthly_external_calls_soft=1_000,
        monthly_external_calls_hard=1_500,
        storage_mb_soft=200,
        storage_mb_hard=300,
        max_agents_soft=2,
        max_agents_hard=2,
        max_swarms_soft=1,
        max_swarms_hard=1,
        features={
            "advanced_routines": False,
            "priority_support": False,
            "custom_branding": False,
            "team_rbac": True,
            "api_access": True,
        },
    ),
    TIER_PRO: PlanDefinition(
        tier=TIER_PRO,
        label="Pro",
        monthly_token_soft=2_000_000,
        monthly_token_hard=2_500_000,
        monthly_supervisor_sessions_soft=500,
        monthly_supervisor_sessions_hard=650,
        monthly_external_calls_soft=30_000,
        monthly_external_calls_hard=40_000,
        storage_mb_soft=3_000,
        storage_mb_hard=4_000,
        max_agents_soft=50,
        max_agents_hard=100,
        max_swarms_soft=20,
        max_swarms_hard=50,
        features={
            "advanced_routines": True,
            "priority_support": False,
            "custom_branding": True,
            "team_rbac": True,
            "api_access": True,
        },
    ),
    TIER_ENTERPRISE: PlanDefinition(
        tier=TIER_ENTERPRISE,
        label="Enterprise",
        monthly_token_soft=10_000_000,
        monthly_token_hard=15_000_000,
        monthly_supervisor_sessions_soft=3_000,
        monthly_supervisor_sessions_hard=4_000,
        monthly_external_calls_soft=200_000,
        monthly_external_calls_hard=250_000,
        storage_mb_soft=50_000,
        storage_mb_hard=80_000,
        max_agents_soft=500,
        max_agents_hard=1_000,
        max_swarms_soft=200,
        max_swarms_hard=500,
        features={
            "advanced_routines": True,
            "priority_support": True,
            "custom_branding": True,
            "team_rbac": True,
            "api_access": True,
            "dedicated_support_channel": True,
        },
    ),
}


def _month_window(now: datetime | None = None) -> tuple[datetime, datetime]:
    """Return UTC start/end timestamps for current month window."""

    anchor = now or datetime.now(tz=UTC)
    start = anchor.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if start.month == 12:
        end = start.replace(year=start.year + 1, month=1)
    else:
        end = start.replace(month=start.month + 1)
    return start, end


def _plan_for_tier(tier: str | None) -> PlanDefinition:
    """Resolve tier to known plan with safe free fallback."""

    key = str(tier or TIER_FREE).strip().lower()
    return _PLANS.get(key, _PLANS[TIER_FREE])


async def ensure_tenant_subscription(db: AsyncSession, *, tenant_id: uuid.UUID) -> TenantSubscription:
    """Guarantee each tenant has one active subscription row."""

    row = await db.scalar(
        select(TenantSubscription).where(TenantSubscription.tenant_id == tenant_id),
    )
    if row is not None:
        return row
    row = TenantSubscription(
        tenant_id=tenant_id,
        tier=TIER_FREE,
        status="active",
    )
    db.add(row)
    await db.flush()
    return row


def resolve_plan_features(subscription: TenantSubscription) -> dict[str, bool]:
    """Merge base tier features with explicit tenant overrides."""

    base = dict(_plan_for_tier(subscription.tier).features)
    overrides = dict(subscription.feature_overrides or {})
    for key, value in overrides.items():
        base[str(key)] = bool(value)
    return base


def resolve_plan_limits(subscription: TenantSubscription) -> dict[str, int]:
    """Merge base tier limits with tenant overrides."""

    plan = _plan_for_tier(subscription.tier)
    limits = {
        "monthly_token_soft": plan.monthly_token_soft,
        "monthly_token_hard": plan.monthly_token_hard,
        "monthly_supervisor_sessions_soft": plan.monthly_supervisor_sessions_soft,
        "monthly_supervisor_sessions_hard": plan.monthly_supervisor_sessions_hard,
        "monthly_external_calls_soft": plan.monthly_external_calls_soft,
        "monthly_external_calls_hard": plan.monthly_external_calls_hard,
        "storage_mb_soft": plan.storage_mb_soft,
        "storage_mb_hard": plan.storage_mb_hard,
        "max_agents_soft": plan.max_agents_soft,
        "max_agents_hard": plan.max_agents_hard,
        "max_swarms_soft": plan.max_swarms_soft,
        "max_swarms_hard": plan.max_swarms_hard,
    }
    for key, value in dict(subscription.limits_override or {}).items():
        if key in limits:
            try:
                limits[key] = max(0, int(value))
            except (TypeError, ValueError):
                continue
    return limits


async def compute_tenant_usage(db: AsyncSession, *, tenant_id: uuid.UUID) -> dict[str, float]:
    """Aggregate usage signals for current month and tenant footprint."""

    month_start, month_end = _month_window()
    token_total = await db.scalar(
        select(
            func.coalesce(func.sum(CostRecord.tokens_in + CostRecord.tokens_out), 0),
        ).where(
            CostRecord.tenant_id == tenant_id,
            CostRecord.created_at >= month_start,
            CostRecord.created_at < month_end,
        ),
    )
    total_spend = await db.scalar(
        select(func.coalesce(func.sum(CostRecord.cost_usd), 0.0)).where(
            CostRecord.tenant_id == tenant_id,
            CostRecord.created_at >= month_start,
            CostRecord.created_at < month_end,
        ),
    )
    supervisor_sessions = await db.scalar(
        select(func.count()).select_from(SupervisorSession).where(
            SupervisorSession.tenant_id == tenant_id,
            SupervisorSession.created_at >= month_start,
            SupervisorSession.created_at < month_end,
        ),
    )
    supervisor_runtime_seconds = await db.scalar(
        select(
            func.coalesce(
                func.sum(
                    func.extract(
                        "epoch",
                        func.coalesce(SupervisorSession.completed_at, func.now()) - SupervisorSession.started_at,
                    ),
                ),
                0.0,
            ),
        ).where(
            SupervisorSession.tenant_id == tenant_id,
            SupervisorSession.started_at.is_not(None),
            SupervisorSession.created_at >= month_start,
            SupervisorSession.created_at < month_end,
        ),
    )
    external_calls = await db.scalar(
        select(func.count()).select_from(ExternalProjectRunAudit).where(
            ExternalProjectRunAudit.tenant_id == tenant_id,
            ExternalProjectRunAudit.created_at >= month_start,
            ExternalProjectRunAudit.created_at < month_end,
        ),
    )
    knowledge_chars = await db.scalar(
        select(func.coalesce(func.sum(func.length(KnowledgeItem.content_text)), 0)).where(
            KnowledgeItem.tenant_id == tenant_id,
        ),
    )
    output_chars = await db.scalar(
        select(
            func.coalesce(
                func.sum(
                    func.length(
                        func.coalesce(ExternalOutput.text_report, ""),
                    ),
                ),
                0,
            ),
        ).where(
            ExternalOutput.tenant_id == tenant_id,
        ),
    )
    storage_bytes = float((int(knowledge_chars or 0) + int(output_chars or 0)))
    return {
        "monthly_tokens": float(int(token_total or 0)),
        "monthly_spend_usd": float(total_spend or 0.0),
        "monthly_supervisor_sessions": float(int(supervisor_sessions or 0)),
        "monthly_supervisor_runtime_sec": float(supervisor_runtime_seconds or 0.0),
        "monthly_external_calls": float(int(external_calls or 0)),
        "storage_bytes_estimate": storage_bytes,
        "storage_mb_estimate": round(storage_bytes / (1024.0 * 1024.0), 2),
    }


def feature_enabled_for_subscription(*, subscription: TenantSubscription, feature_key: str) -> bool:
    """Resolve effective feature availability for subscription tier."""

    features = resolve_plan_features(subscription)
    return bool(features.get(feature_key, False))


def evaluate_usage_health(*, limits: dict[str, int], usage: dict[str, float]) -> dict[str, dict[str, Any]]:
    """Return soft/hard saturation details for usage dashboard."""

    checks: dict[str, tuple[float, int, int]] = {
        "monthly_tokens": (
            float(usage.get("monthly_tokens", 0.0)),
            int(limits["monthly_token_soft"]),
            int(limits["monthly_token_hard"]),
        ),
        "monthly_supervisor_sessions": (
            float(usage.get("monthly_supervisor_sessions", 0.0)),
            int(limits["monthly_supervisor_sessions_soft"]),
            int(limits["monthly_supervisor_sessions_hard"]),
        ),
        "monthly_external_calls": (
            float(usage.get("monthly_external_calls", 0.0)),
            int(limits["monthly_external_calls_soft"]),
            int(limits["monthly_external_calls_hard"]),
        ),
        "storage_mb_estimate": (
            float(usage.get("storage_mb_estimate", 0.0)),
            int(limits["storage_mb_soft"]),
            int(limits["storage_mb_hard"]),
        ),
    }
    out: dict[str, dict[str, Any]] = {}
    for metric, (value, soft, hard) in checks.items():
        soft_pct = (value / soft * 100.0) if soft > 0 else 0.0
        hard_pct = (value / hard * 100.0) if hard > 0 else 0.0
        out[metric] = {
            "value": value,
            "soft_limit": soft,
            "hard_limit": hard,
            "soft_exceeded": value >= soft if soft > 0 else False,
            "hard_exceeded": value >= hard if hard > 0 else False,
            "soft_pct": round(soft_pct, 2),
            "hard_pct": round(hard_pct, 2),
        }
    return out


async def assert_supervisor_session_hard_limit(db: AsyncSession, *, tenant_id: uuid.UUID) -> None:
    """Block new supervisor sessions when hard monthly quota is exceeded."""

    subscription = await ensure_tenant_subscription(db, tenant_id=tenant_id)
    limits = resolve_plan_limits(subscription)
    usage = await compute_tenant_usage(db, tenant_id=tenant_id)
    sessions = float(usage.get("monthly_supervisor_sessions", 0.0))
    hard = float(limits["monthly_supervisor_sessions_hard"])
    if hard > 0 and sessions >= hard:
        raise ValueError("billing_limit_exceeded:monthly_supervisor_sessions")


async def _commercial_subscription_for_tenant(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID | None,
) -> TenantSubscription | None:
    """Return subscription when tenant is commercial; skip gating for internal hives."""

    if tenant_id is None:
        return None
    tenant = await db.get(Tenant, tenant_id)
    if tenant is None:
        return None
    if _normalize_platform_mode(getattr(tenant, "platform_mode", "internal")) != "commercial":
        return None
    return await ensure_tenant_subscription(db, tenant_id=tenant_id)


async def assert_agent_hard_limit(db: AsyncSession, *, tenant_id: uuid.UUID | None) -> None:
    """Block new dynamic agents when commercial tier agent cap is reached."""

    subscription = await _commercial_subscription_for_tenant(db, tenant_id=tenant_id)
    if subscription is None:
        return
    limits = resolve_plan_limits(subscription)
    hard = int(limits.get("max_agents_hard", 0))
    if hard <= 0:
        return
    count = int(await db.scalar(select(func.count()).select_from(Agent)) or 0)
    if count >= hard:
        raise ValueError("billing_limit_exceeded:max_agents")


async def assert_swarm_hard_limit(db: AsyncSession, *, tenant_id: uuid.UUID | None) -> None:
    """Block new sub-swarms when commercial tier swarm cap is reached."""

    subscription = await _commercial_subscription_for_tenant(db, tenant_id=tenant_id)
    if subscription is None:
        return
    limits = resolve_plan_limits(subscription)
    hard = int(limits.get("max_swarms_hard", 0))
    if hard <= 0:
        return
    count = int(await db.scalar(select(func.count()).select_from(SubSwarm)) or 0)
    if count >= hard:
        raise ValueError("billing_limit_exceeded:max_swarms")


def plan_catalog() -> list[dict[str, Any]]:
    """Return static plan comparison payload for dashboard UI."""

    plans: list[dict[str, Any]] = []
    for plan in (_PLANS[TIER_FREE], _PLANS[TIER_PRO], _PLANS[TIER_ENTERPRISE]):
        plans.append(
            {
                "tier": plan.tier,
                "label": plan.label,
                "limits": {
                    "monthly_tokens_soft": plan.monthly_token_soft,
                    "monthly_tokens_hard": plan.monthly_token_hard,
                    "monthly_supervisor_sessions_soft": plan.monthly_supervisor_sessions_soft,
                    "monthly_supervisor_sessions_hard": plan.monthly_supervisor_sessions_hard,
                    "monthly_external_calls_soft": plan.monthly_external_calls_soft,
                    "monthly_external_calls_hard": plan.monthly_external_calls_hard,
                    "storage_mb_soft": plan.storage_mb_soft,
                    "storage_mb_hard": plan.storage_mb_hard,
                    "max_agents_soft": plan.max_agents_soft,
                    "max_agents_hard": plan.max_agents_hard,
                    "max_swarms_soft": plan.max_swarms_soft,
                    "max_swarms_hard": plan.max_swarms_hard,
                },
                "features": dict(plan.features),
            },
        )
    return plans


__all__ = [
    "TIER_ENTERPRISE",
    "TIER_FREE",
    "TIER_PRO",
    "assert_agent_hard_limit",
    "assert_supervisor_session_hard_limit",
    "assert_swarm_hard_limit",
    "compute_tenant_usage",
    "ensure_tenant_subscription",
    "evaluate_usage_health",
    "feature_enabled_for_subscription",
    "plan_catalog",
    "resolve_plan_features",
    "resolve_plan_limits",
]
