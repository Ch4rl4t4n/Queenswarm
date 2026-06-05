"""Operator Loop — unified morning/evening snapshot (overnight + brief + publish + trading)."""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.morning_hive_brief import compose_morning_hive_brief
from app.application.services.morning_publish_pipeline import compose_morning_publish_pipeline_snapshot
from app.application.services.publish_operator_onboarding import compose_publish_onboarding_snapshot
from app.application.services.hive_oracle import (
    COCKPIT_OVERVIEW_HREF,
    HARNES_OPERATOR_HUB_HREF,
    STUDIO_PUBLISH_QUEUE_HREF,
    STUDIO_TRADING_COCKPIT_HREF,
)
from app.application.services.trading_cockpit import (
    compose_trading_cockpit_action_signals,
    compose_trading_cockpit_snapshot,
)
from app.core.config import settings
from app.infrastructure.persistence.models.tenant import Tenant

OperatorLoopPhase = Literal["morning", "evening", "anytime"]


class OperatorLoopActionOut(BaseModel):
    """One actionable next step for the operator."""

    model_config = ConfigDict(extra="ignore")

    id: str
    label: str
    detail: str
    priority: Literal["high", "medium", "low"]
    href: str | None = None


class OperatorLoopSnapshotOut(BaseModel):
    """Single snapshot for Operator Loop panel — daily command center."""

    model_config = ConfigDict(extra="ignore")

    enabled: bool
    generated_at: datetime
    phase: OperatorLoopPhase
    overnight: dict[str, Any]
    morning_brief: dict[str, Any]
    publish_pipeline: dict[str, Any]
    publish_onboarding: dict[str, Any]
    trading: dict[str, Any]
    actions: list[OperatorLoopActionOut] = Field(default_factory=list)
    links: dict[str, str] = Field(default_factory=dict)


async def _load_overnight_summary(db: AsyncSession, *, tenant_id: uuid.UUID) -> dict[str, Any]:
    from sqlalchemy import desc, select

    from app.infrastructure.persistence.models.dump_sleep_batch import DumpSleepBatchORM, DumpSleepStatusORM

    if not settings.dump_sleep_enabled:
        return {"available": False, "reason": "dump_sleep_disabled"}

    row = await db.scalar(
        select(DumpSleepBatchORM)
        .where(
            DumpSleepBatchORM.tenant_id == tenant_id,
            DumpSleepBatchORM.status == DumpSleepStatusORM.COMPLETED,
        )
        .order_by(desc(DumpSleepBatchORM.processed_at))
        .limit(1),
    )
    if row is None:
        return {"available": False, "reason": "no_completed_batch"}
    return {
        "available": True,
        "batch_id": str(row.id),
        "items_ingested": row.items_ingested,
        "stalled_signals": row.stalled_signals,
        "pollen_earned": float(row.pollen_earned or 0),
        "briefing_preview": (row.briefing_md or "")[:1200],
        "processed_at": row.processed_at.isoformat() if row.processed_at else None,
    }


def _derive_actions(
    *,
    overnight: dict[str, Any],
    publish_pipeline: dict[str, Any],
    publish_onboarding: dict[str, Any],
    trading: dict[str, Any],
) -> list[OperatorLoopActionOut]:
    """Build prioritized operator actions from subsystem snapshots."""

    actions: list[OperatorLoopActionOut] = []

    pending = int(publish_pipeline.get("pending_publish_count") or 0)
    if pending > 0:
        actions.append(
            OperatorLoopActionOut(
                id="approve_publish",
                label=f"Approve {pending} publish pack(s)",
                detail="Publish Queue — simulate-only approval before social live.",
                priority="high",
                href=STUDIO_PUBLISH_QUEUE_HREF,
            ),
        )

    onboard_raw = publish_onboarding
    if hasattr(publish_onboarding, "model_dump"):
        onboard_raw = publish_onboarding.model_dump()
    progress = int((onboard_raw or {}).get("progress_pct") or 0)
    if progress < 100:
        actions.append(
            OperatorLoopActionOut(
                id="publish_onboarding",
                label=f"Publish onboarding {progress}%",
                detail="Complete OAuth + simulate steps before first live post.",
                priority="high" if progress < 60 else "medium",
                href=HARNES_OPERATOR_HUB_HREF,
            ),
        )

    perf = trading.get("performance") if isinstance(trading.get("performance"), dict) else {}
    if perf.get("is_halted"):
        actions.append(
            OperatorLoopActionOut(
                id="trading_halted",
                label="Trading agent halted",
                detail=str(perf.get("halt_reason") or "Daily stop-loss — review Trading Cockpit."),
                priority="high",
                href=STUDIO_TRADING_COCKPIT_HREF,
            ),
        )
    elif not perf.get("live_ready") and settings.prediction_markets_enabled:
        actions.append(
            OperatorLoopActionOut(
                id="polymarket_prep",
                label="Complete Polymarket live setup",
                detail="Vault CLOB credentials and enable live trading flag after risk review.",
                priority="high",
                href=STUDIO_TRADING_COCKPIT_HREF,
            ),
        )

    if overnight.get("available") and int(overnight.get("stalled_signals") or 0) > 0:
        actions.append(
            OperatorLoopActionOut(
                id="stalled_triage",
                label="Triage stalled projects",
                detail=f"{overnight.get('stalled_signals')} signals from overnight dump.",
                priority="medium",
                href=COCKPIT_OVERVIEW_HREF,
            ),
        )

    if not overnight.get("available"):
        actions.append(
            OperatorLoopActionOut(
                id="dump_sleep",
                label="Evening Dump & Sleep",
                detail="Upload notes/files in Ballroom before sleep — morning brief tomorrow.",
                priority="low",
                href="/ballroom",
            ),
        )

    return actions[:8]


async def compose_operator_loop_lite(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    dashboard_user_id: uuid.UUID,
    tenant: Tenant | None,
    phase: OperatorLoopPhase = "morning",
) -> OperatorLoopSnapshotOut:
    """Fast operator loop for Cockpit core — parallel I/O, skips morning brief."""

    overnight, publish_pipeline_snap, publish_onboarding, trading = await asyncio.gather(
        _load_overnight_summary(db, tenant_id=tenant_id),
        compose_morning_publish_pipeline_snapshot(
            db,
            tenant_id=tenant_id,
            dashboard_user_id=dashboard_user_id,
            include_brief=False,
        ),
        compose_publish_onboarding_snapshot(
            db,
            tenant_id=tenant_id,
            dashboard_user_id=dashboard_user_id,
            tenant=tenant,
        ),
        compose_trading_cockpit_action_signals(
            db,
            dashboard_user_id=dashboard_user_id,
            tenant=tenant,
        ),
    )
    publish_pipeline = publish_pipeline_snap.model_dump()
    onboard_dump = publish_onboarding.model_dump()

    actions = _derive_actions(
        overnight=overnight,
        publish_pipeline=publish_pipeline,
        publish_onboarding=onboard_dump,
        trading=trading,
    )

    return OperatorLoopSnapshotOut(
        enabled=bool(settings.operator_loop_enabled),
        generated_at=datetime.now(tz=UTC),
        phase=phase,
        overnight=overnight,
        morning_brief={},
        publish_pipeline=publish_pipeline,
        publish_onboarding=onboard_dump,
        trading=trading,
        actions=actions,
        links={
            "ballroom": "/ballroom",
            "execution_studio": "/integrations?tab=studio",
            "publish_queue": STUDIO_PUBLISH_QUEUE_HREF,
            "trading_cockpit": STUDIO_TRADING_COCKPIT_HREF,
            "knowledge": "/knowledge",
            "settings_harness": "/settings/harness",
        },
    )


async def compose_operator_loop_snapshot(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    dashboard_user_id: uuid.UUID,
    tenant: Tenant | None,
    phase: OperatorLoopPhase = "morning",
) -> OperatorLoopSnapshotOut:
    """Assemble unified operator loop from existing verified subsystems."""

    overnight = await _load_overnight_summary(db, tenant_id=tenant_id)
    morning_brief = await compose_morning_hive_brief(db, tenant_id=tenant_id)
    publish_pipeline_snap = await compose_morning_publish_pipeline_snapshot(
        db,
        tenant_id=tenant_id,
        dashboard_user_id=dashboard_user_id,
    )
    publish_pipeline = publish_pipeline_snap.model_dump()
    publish_onboarding = await compose_publish_onboarding_snapshot(
        db,
        tenant_id=tenant_id,
        dashboard_user_id=dashboard_user_id,
        tenant=tenant,
    )
    trading_snap = await compose_trading_cockpit_snapshot(
        db,
        dashboard_user_id=dashboard_user_id,
        tenant=tenant,
    )
    trading = trading_snap.model_dump()

    actions = _derive_actions(
        overnight=overnight,
        publish_pipeline=publish_pipeline,
        publish_onboarding=publish_onboarding,
        trading=trading,
    )

    return OperatorLoopSnapshotOut(
        enabled=bool(settings.operator_loop_enabled),
        generated_at=datetime.now(tz=UTC),
        phase=phase,
        overnight=overnight,
        morning_brief=morning_brief,
        publish_pipeline=publish_pipeline,
        publish_onboarding=publish_onboarding.model_dump(),
        trading={
            "performance": trading.get("performance"),
            "funding": trading.get("funding"),
            "config": trading.get("config"),
        },
        actions=actions,
        links={
            "ballroom": "/ballroom",
            "execution_studio": "/integrations?tab=studio",
            "publish_queue": STUDIO_PUBLISH_QUEUE_HREF,
            "trading_cockpit": STUDIO_TRADING_COCKPIT_HREF,
            "knowledge": "/knowledge",
            "settings_harness": "/settings/harness",
        },
    )


__all__ = ["OperatorLoopSnapshotOut", "compose_operator_loop_lite", "compose_operator_loop_snapshot"]
