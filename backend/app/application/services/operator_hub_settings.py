"""Operator hub settings — unified autonomy + live lane snapshot for Settings UI."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.live_lane import LiveLaneSnapshotOut, compose_live_lane_snapshot
from app.application.services.operator_next_action import OperatorNextActionOut, resolve_operator_next_action
from app.application.services.operator_social_oauth_status import (
    OperatorSocialOAuthStatusOut,
    compose_operator_social_oauth_status,
)
from app.application.services.publish_operator_onboarding import (
    PublishOnboardingSnapshotOut,
    compose_publish_onboarding_snapshot,
)
from app.application.services.solo_daily_plan import SoloDailyPlanOut, compose_solo_daily_plan
from app.core.config import settings
from app.infrastructure.persistence.models.tenant import Tenant


class OperatorModuleOut(BaseModel):
    """One shipped autonomy module row."""

    model_config = ConfigDict(extra="ignore")

    id: str
    label: str
    enabled: bool
    env_hint: str | None = None


class OperatorEnvFlagOut(BaseModel):
    """Read-only env flag status (never exposes secrets)."""

    model_config = ConfigDict(extra="ignore")

    key: str
    active: bool
    description: str


class OperatorHubSnapshotOut(BaseModel):
    """Settings → AI harness operator hub snapshot."""

    model_config = ConfigDict(extra="ignore")

    enabled: bool
    generated_at: datetime
    modules: list[OperatorModuleOut] = Field(default_factory=list)
    env_flags: list[OperatorEnvFlagOut] = Field(default_factory=list)
    live_lane: LiveLaneSnapshotOut | None = None
    publish_onboarding: PublishOnboardingSnapshotOut | None = None
    social_oauth: OperatorSocialOAuthStatusOut | None = None
    next_action: OperatorNextActionOut | None = None
    daily_plan: SoloDailyPlanOut | None = None
    docs: dict[str, str] = Field(default_factory=dict)


def _build_modules() -> list[OperatorModuleOut]:
    """Return autonomy module toggles from platform settings."""

    rows: list[tuple[str, str, bool, str | None]] = [
        ("agent_os", "Agent OS P8", settings.agent_os_enabled, None),
        ("operator_loop", "Operator Loop", settings.operator_loop_enabled, None),
        ("publish_performance", "Publish Performance", settings.publish_performance_enabled, None),
        ("research_bee", "Research Bee", settings.research_bee_enabled, None),
        ("live_lane", "Live Lane Prep", settings.live_lane_snapshot_enabled, None),
        ("trading_cockpit", "Trading Cockpit", settings.trading_cockpit_enabled, None),
        ("pattern_router_llm", "Pattern Router LLM", settings.supervisor_pattern_router_llm_enabled, "SUPERVISOR_PATTERN_ROUTER_LLM_ENABLED"),
    ]
    if not settings.solo_mode_enabled:
        rows.extend(
            [
                ("media_agency", "Media Agency in a Box", settings.media_agency_in_a_box_enabled, None),
                ("micro_saas_factory", "Micro-SaaS Factory", settings.micro_saas_factory_enabled, None),
            ],
        )
    elif settings.media_agency_in_a_box_enabled or settings.micro_saas_factory_enabled:
        if settings.media_agency_in_a_box_enabled:
            rows.append(("media_agency", "Media Agency in a Box", True, None))
        if settings.micro_saas_factory_enabled:
            rows.append(("micro_saas_factory", "Micro-SaaS Factory", True, None))
    return [
        OperatorModuleOut(id=mid, label=label, enabled=enabled, env_hint=hint)
        for mid, label, enabled, hint in rows
    ]


def _build_env_flags() -> list[OperatorEnvFlagOut]:
    """Live-money and publish env kill switches — read-only."""

    return [
        OperatorEnvFlagOut(
            key="PREDICTION_MARKETS_LIVE_TRADING_ENABLED",
            active=bool(settings.prediction_markets_live_trading_enabled),
            description="Polymarket real-money orders (default off).",
        ),
        OperatorEnvFlagOut(
            key="SOCIAL_PUBLISH_LIVE_ENABLED",
            active=bool(settings.social_publish_live_enabled),
            description="Social API live posts (default off).",
        ),
        OperatorEnvFlagOut(
            key="SUPERVISOR_PATTERN_ROUTER_LLM_ENABLED",
            active=bool(settings.supervisor_pattern_router_llm_enabled),
            description="Optional LLM pattern refine hop (default off).",
        ),
    ]


async def compose_operator_hub_snapshot(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    dashboard_user_id: uuid.UUID,
    tenant: Tenant | None,
) -> OperatorHubSnapshotOut:
    """Build operator settings hub — modules, env flags, live lane."""

    if not settings.operator_hub_settings_enabled:
        return OperatorHubSnapshotOut(
            enabled=False,
            generated_at=datetime.now(tz=UTC),
        )

    live_lane: LiveLaneSnapshotOut | None = None
    if settings.live_lane_snapshot_enabled:
        live_lane = await compose_live_lane_snapshot(
            session,
            tenant_id=tenant_id,
            dashboard_user_id=dashboard_user_id,
            tenant=tenant,
        )

    publish_onboarding: PublishOnboardingSnapshotOut | None = None
    if settings.social_publish_enabled:
        publish_onboarding = await compose_publish_onboarding_snapshot(
            session,
            tenant_id=tenant_id,
            dashboard_user_id=dashboard_user_id,
            tenant=tenant,
        )

    social_oauth: OperatorSocialOAuthStatusOut | None = None
    if settings.social_publish_enabled:
        social_oauth = await compose_operator_social_oauth_status(
            session,
            dashboard_user_id=dashboard_user_id,
            tenant=tenant,
        )

    next_action: OperatorNextActionOut | None = None
    if publish_onboarding is not None:
        next_action = resolve_operator_next_action(
            publish_onboarding=publish_onboarding,
            social_oauth=social_oauth,
        )

    daily_plan: SoloDailyPlanOut | None = None
    if settings.solo_mode_enabled:
        daily_plan = await compose_solo_daily_plan(
            session,
            tenant_id=tenant_id,
            dashboard_user_id=dashboard_user_id,
            tenant=tenant,
            max_items=5,
        )

    return OperatorHubSnapshotOut(
        enabled=True,
        generated_at=datetime.now(tz=UTC),
        modules=_build_modules(),
        env_flags=_build_env_flags(),
        live_lane=live_lane,
        publish_onboarding=publish_onboarding,
        social_oauth=social_oauth,
        next_action=next_action,
        daily_plan=daily_plan,
        docs={
            "live_lane": "docs/OPERATOR_PREDICTION_MARKETS_SETUP.md",
            "publish": "docs/OPERATOR_FIRST_LIVE_POST.md",
            "publish_lane_prep": "scripts/operator-publish-lane-prep.sh",
            "live_prep_script": "scripts/operator-live-trading-prep.sh",
        },
    )


__all__ = ["OperatorHubSnapshotOut", "compose_operator_hub_snapshot"]
