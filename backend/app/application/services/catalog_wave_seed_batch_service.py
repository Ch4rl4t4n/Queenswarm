"""MK11 — One-click Skill Factory seed batch from pending MK6 vertical seeds."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.factory_catalog_wave import pending_vertical_seeds
from app.application.services.skill_factory_research import auto_queue_factory_builds, run_skill_market_research
from app.application.services.skill_factory_service import get_skill_factory_policy
from app.core.config import settings
from app.core.logging import get_logger

_logger = get_logger(__name__)


class CatalogWaveSeedBatchRowOut(BaseModel):
    """One pending seed processed in a batch."""

    model_config = ConfigDict(extra="ignore")

    niche: str
    opportunity_id: str | None = None
    status: str = "skipped"


class CatalogWaveSeedBatchOut(BaseModel):
    """Result of MK11 seed-batch from catalog wave pending seeds."""

    model_config = ConfigDict(extra="ignore")

    ok: bool = False
    message: str = ""
    pending_before: int = 0
    researched_count: int = 0
    builds_started: int = 0
    seeds: list[str] = Field(default_factory=list)
    rows: list[CatalogWaveSeedBatchRowOut] = Field(default_factory=list)
    factory_href: str = "/apps-tools/skill-factory"


async def run_catalog_wave_seed_batch(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    created_by_subject: str,
    limit: int = 3,
) -> CatalogWaveSeedBatchOut:
    """Research + optional auto-build for pending MK6 vertical seeds not yet in catalog."""

    if not settings.catalog_wave_seed_batch_enabled:
        return CatalogWaveSeedBatchOut(
            ok=False,
            message="Catalog wave seed batch disabled.",
        )
    if not settings.skill_factory_enabled:
        return CatalogWaveSeedBatchOut(
            ok=False,
            message="Skill Factory is disabled.",
        )

    cap = max(1, min(limit, 6))
    pending = pending_vertical_seeds()
    if not pending:
        return CatalogWaveSeedBatchOut(
            ok=False,
            pending_before=0,
            message="No pending vertical seeds — catalog families already cover SSOT seeds.",
            factory_href="/apps-tools/skill-factory",
        )

    batch = pending[:cap]
    policy = await get_skill_factory_policy(session, tenant_id=tenant_id)
    if not policy.enabled:
        return CatalogWaveSeedBatchOut(
            ok=False,
            pending_before=len(pending),
            seeds=batch,
            message="Enable Skill Factory in tenant settings before seeding.",
        )

    batch_policy = policy.model_copy(update={"niche_seeds": batch})
    created = await run_skill_market_research(
        session,
        tenant_id=tenant_id,
        policy=batch_policy,
        max_new=cap,
    )
    builds_started = 0
    if policy.auto_build_enabled and created:
        builds_started = await auto_queue_factory_builds(
            session,
            tenant_id=tenant_id,
            policy=policy,
            created_by_subject=created_by_subject,
        )

    rows: list[CatalogWaveSeedBatchRowOut] = []
    created_by_niche = {row.niche: row for row in created}
    for seed in batch:
        opp = created_by_niche.get(seed)
        if opp is not None:
            rows.append(
                CatalogWaveSeedBatchRowOut(
                    niche=seed,
                    opportunity_id=str(opp.id),
                    status=str(opp.status),
                ),
            )
        else:
            rows.append(CatalogWaveSeedBatchRowOut(niche=seed, status="skipped"))

    ok = len(created) > 0
    if ok and builds_started > 0:
        message = f"Researched {len(created)} pending seed(s) and started {builds_started} build(s)."
    elif ok:
        message = f"Researched {len(created)} pending seed(s) — review queue in Skill Factory."
    else:
        message = (
            f"No new opportunities from {len(batch)} pending seed(s) — niches may be retired, "
            "duplicate, or already in queue."
        )

    _logger.info(
        "catalog_wave_seed_batch.complete",
        agent_id="catalog_wave_seed_batch",
        swarm_id=str(tenant_id),
        pending_before=len(pending),
        researched=len(created),
        builds_started=builds_started,
    )

    return CatalogWaveSeedBatchOut(
        ok=ok,
        message=message,
        pending_before=len(pending),
        researched_count=len(created),
        builds_started=builds_started,
        seeds=batch,
        rows=rows,
        factory_href="/apps-tools/skill-factory?section=queue#queue",
    )


__all__ = [
    "CatalogWaveSeedBatchOut",
    "CatalogWaveSeedBatchRowOut",
    "run_catalog_wave_seed_batch",
]
