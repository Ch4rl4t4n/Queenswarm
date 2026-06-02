"""Run social intel scrape cycles for YouTube/X foragers."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.forager_service import ForagerService
from app.application.services.social_intel_scraper import (
    ScrapedIntelItem,
    fetch_x_user_items,
    fetch_youtube_channel_items,
    normalize_x_source_key,
    normalize_youtube_source_key,
    scraped_item_to_ingest_record,
)
from app.application.services.supervisor.routine_service import trigger_supervisor_routine_now
from app.application.services.x_social_context import _read_x_access_token
from app.core.config import settings
from app.core.logging import get_logger
from app.infrastructure.persistence.models.forager import ForagerORM
from app.infrastructure.persistence.models.intel_source_cursor import IntelSourceCursorORM
from app.infrastructure.persistence.models.supervisor_routine import SupervisorRoutine
from app.infrastructure.persistence.models.tenant import DashboardUserTenantMembership

logger = get_logger(__name__)

_SUPPORTED_SOURCE_TYPES = frozenset({"youtube", "twitter", "x"})


async def resolve_tenant_operator_user_id(session: AsyncSession, *, tenant_id: uuid.UUID) -> uuid.UUID | None:
    """Return first owner/admin dashboard user for OAuth token lookup."""

    return await session.scalar(
        select(DashboardUserTenantMembership.dashboard_user_id)
        .where(
            DashboardUserTenantMembership.tenant_id == tenant_id,
            DashboardUserTenantMembership.role.in_(("owner", "admin")),
        )
        .order_by(DashboardUserTenantMembership.created_at.asc())
        .limit(1),
    )


async def _load_cursor(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    forager_id: uuid.UUID,
    platform: str,
    source_key: str,
) -> IntelSourceCursorORM:
    """Load or create watermark row for one monitored source."""

    row = await session.scalar(
        select(IntelSourceCursorORM).where(
            IntelSourceCursorORM.tenant_id == tenant_id,
            IntelSourceCursorORM.forager_id == forager_id,
            IntelSourceCursorORM.platform == platform,
            IntelSourceCursorORM.source_key == source_key,
        ),
    )
    if row is not None:
        return row
    row = IntelSourceCursorORM(
        tenant_id=tenant_id,
        forager_id=forager_id,
        platform=platform,
        source_key=source_key,
        last_external_id=None,
        last_checked_at=None,
        backfill_complete=False,
    )
    session.add(row)
    await session.flush()
    return row


def _source_keys_for_forager(forager: ForagerORM) -> list[str]:
    """Extract channel/account list from forager source_config."""

    cfg = dict(forager.source_config or {})
    if forager.source_type == "youtube":
        raw = cfg.get("channels") or cfg.get("channel_ids") or []
    else:
        raw = cfg.get("accounts") or cfg.get("handles") or cfg.get("channels") or []
    if isinstance(raw, str):
        raw = [line.strip() for line in raw.splitlines() if line.strip()]
    if not isinstance(raw, list):
        return []
    return [str(item).strip() for item in raw if str(item).strip()]


async def scrape_forager_sources(
    session: AsyncSession,
    *,
    forager: ForagerORM,
    operator_user_id: uuid.UUID | None = None,
) -> list[ScrapedIntelItem]:
    """Scrape all configured sources for one forager."""

    cfg = dict(forager.source_config or {})
    backfill_limit = int(cfg.get("backfill_limit") or 50)
    delta_limit = int(cfg.get("delta_limit") or 20)
    backfill_limit = max(1, min(backfill_limit, 200))
    delta_limit = max(1, min(delta_limit, 100))

    source_keys = _source_keys_for_forager(forager)
    if not source_keys:
        return []

    collected: list[ScrapedIntelItem] = []
    async with httpx.AsyncClient() as client:
        if forager.source_type == "youtube":
            api_key = (settings.youtube_api_key or "").strip()
            if not api_key:
                logger.warning(
                    "social_intel.youtube.missing_api_key",
                    agent_id="youtube_scraper",
                    swarm_id=str(forager.id),
                )
                return []
            for raw_key in source_keys:
                norm = normalize_youtube_source_key(raw_key)
                cursor = await _load_cursor(
                    session,
                    tenant_id=forager.tenant_id,
                    forager_id=forager.id,
                    platform="youtube",
                    source_key=norm,
                )
                items = await fetch_youtube_channel_items(
                    client,
                    api_key=api_key,
                    source_key=raw_key,
                    last_external_id=cursor.last_external_id,
                    backfill_limit=backfill_limit,
                    delta_limit=delta_limit,
                )
                if items:
                    cursor.last_external_id = items[0].external_id
                    cursor.backfill_complete = len(items) < backfill_limit or cursor.backfill_complete
                cursor.last_checked_at = datetime.now(tz=UTC)
                collected.extend(items)

        elif forager.source_type in {"twitter", "x"}:
            op_id = operator_user_id or await resolve_tenant_operator_user_id(
                session,
                tenant_id=forager.tenant_id,
            )
            if op_id is None:
                logger.warning(
                    "social_intel.x.missing_operator",
                    agent_id="x_scraper",
                    swarm_id=str(forager.tenant_id),
                )
                return []
            token = await _read_x_access_token(session, dashboard_user_id=op_id)
            if not token:
                logger.warning(
                    "social_intel.x.missing_token",
                    agent_id="x_scraper",
                    swarm_id=str(forager.tenant_id),
                )
                return []
            for raw_key in source_keys:
                norm = normalize_x_source_key(raw_key)
                cursor = await _load_cursor(
                    session,
                    tenant_id=forager.tenant_id,
                    forager_id=forager.id,
                    platform="x",
                    source_key=norm,
                )
                items = await fetch_x_user_items(
                    client,
                    access_token=token,
                    source_key=raw_key,
                    last_external_id=cursor.last_external_id,
                    backfill_limit=backfill_limit,
                    delta_limit=delta_limit,
                )
                if items:
                    cursor.last_external_id = items[0].external_id
                    cursor.backfill_complete = len(items) < backfill_limit or cursor.backfill_complete
                cursor.last_checked_at = datetime.now(tz=UTC)
                collected.extend(items)

    return collected


async def run_social_intel_forager(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    forager_id: uuid.UUID,
    trigger_evaluator: bool = True,
    operator_user_id: uuid.UUID | None = None,
) -> dict[str, Any]:
    """Scrape, ingest to Knowledge, optionally trigger evaluator routine."""

    service = ForagerService(db=session)
    forager = await service.get_by_id(tenant_id, forager_id)
    if forager is None:
        return {"status": "not_found", "scraped": 0, "ingested": 0}
    if not forager.is_active:
        return {"status": "inactive", "scraped": 0, "ingested": 0}
    if forager.source_type not in _SUPPORTED_SOURCE_TYPES:
        return {"status": "unsupported_source", "scraped": 0, "ingested": 0}

    items = await scrape_forager_sources(
        session,
        forager=forager,
        operator_user_id=operator_user_id,
    )
    default_tags = [str(tag).strip() for tag in list((forager.filter_config or {}).get("default_tags") or []) if str(tag).strip()]
    records = [scraped_item_to_ingest_record(item, default_tags=default_tags) for item in items]
    ingested = 0
    if records:
        ingested = await service.ingest_records(tenant_id=tenant_id, forager_id=forager.id, records=records)

    routine_triggered = False
    routine_session_id: str | None = None
    if trigger_evaluator and ingested > 0 and forager.supervisor_routine_id is not None:
        routine = await session.get(SupervisorRoutine, forager.supervisor_routine_id)
        if routine is not None and bool(routine.is_active):
            session_id = await trigger_supervisor_routine_now(session, routine=routine)
            routine_triggered = True
            routine_session_id = str(session_id)

    logger.info(
        "social_intel.forager_run_complete",
        agent_id="social_intel_runner",
        swarm_id=str(forager.id),
        task_id=str(tenant_id),
        scraped=len(items),
        ingested=ingested,
    )
    return {
        "status": "ok",
        "forager_id": str(forager.id),
        "source_type": forager.source_type,
        "scraped": len(items),
        "ingested": ingested,
        "routine_triggered": routine_triggered,
        "routine_session_id": routine_session_id,
    }


async def append_forager_sources(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    forager_id: uuid.UUID,
    platform: str,
    sources: list[str],
) -> ForagerORM | None:
    """Append unique channel/account handles to forager source_config."""

    service = ForagerService(db=session)
    row = await service.get_by_id(tenant_id, forager_id)
    if row is None:
        return None
    cfg = dict(row.source_config or {})
    field = "channels" if platform == "youtube" else "accounts"
    existing_raw = cfg.get(field) or []
    if isinstance(existing_raw, str):
        existing = [line.strip() for line in existing_raw.splitlines() if line.strip()]
    else:
        existing = [str(item).strip() for item in list(existing_raw) if str(item).strip()]

    normalize = normalize_youtube_source_key if platform == "youtube" else normalize_x_source_key
    seen = {normalize(item) for item in existing}
    for src in sources:
        cleaned = src.strip()
        if not cleaned:
            continue
        norm = normalize(cleaned)
        if norm in seen:
            continue
        seen.add(norm)
        existing.append(cleaned)

    cfg[field] = existing
    row.source_config = cfg
    await session.flush()
    return row


async def run_all_active_social_intel_foragers(session: AsyncSession) -> dict[str, Any]:
    """Daily tick — scrape all active youtube/x foragers across tenants."""

    rows = list(
        (
            await session.scalars(
                select(ForagerORM)
                .where(
                    ForagerORM.is_active.is_(True),
                    ForagerORM.source_type.in_(tuple(_SUPPORTED_SOURCE_TYPES)),
                )
                .order_by(ForagerORM.updated_at.desc())
                .limit(64),
            )
        ).all(),
    )
    results: list[dict[str, Any]] = []
    total_ingested = 0
    for row in rows:
        try:
            out = await run_social_intel_forager(
                session,
                tenant_id=row.tenant_id,
                forager_id=row.id,
                trigger_evaluator=True,
            )
            results.append(out)
            total_ingested += int(out.get("ingested") or 0)
        except Exception as exc:
            logger.warning(
                "social_intel.forager_tick_failed",
                agent_id="social_intel_runner",
                swarm_id=str(row.id),
                error=str(exc)[:200],
            )
            results.append({"forager_id": str(row.id), "status": "error", "error": str(exc)[:200]})
    return {"foragers": len(rows), "total_ingested": total_ingested, "results": results}


__all__ = [
    "append_forager_sources",
    "run_all_active_social_intel_foragers",
    "run_social_intel_forager",
    "scrape_forager_sources",
]
