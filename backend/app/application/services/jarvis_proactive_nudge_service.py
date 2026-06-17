"""POS-I2 — Jarvis proactive nudge via mission feed (deduped, simulate-first hints)."""

from __future__ import annotations

import uuid

import structlog
from redis.exceptions import RedisError
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.jarvis_advisor_service import MissionJarvisStepOut
from app.application.services.operator_mission_feed import push_mission_feed_event
from app.application.services.operator_mission_push import maybe_send_mission_feed_web_push
from app.core.config import settings
from app.core.redis_client import get_redis

logger = structlog.get_logger(__name__)

_DEDUP_PREFIX = "jarvis_nudge_dedup:v1:"
_DEDUP_TTL_SEC = 6 * 3600


def _dedup_key(*, tenant_id: uuid.UUID, step: MissionJarvisStepOut) -> str:
    slug = step.kind
    return f"{_DEDUP_PREFIX}{tenant_id}:{slug}"


async def _dedup_claim(*, tenant_id: uuid.UUID, step: MissionJarvisStepOut) -> bool:
    """Return True when this nudge kind may be pushed (first time in dedup window)."""

    key = _dedup_key(tenant_id=tenant_id, step=step)
    try:
        async for redis in get_redis():
            claimed = await redis.set(key, "1", nx=True, ex=_DEDUP_TTL_SEC)
            return bool(claimed)
    except RedisError as exc:
        logger.warning(
            "jarvis_nudge.dedup_failed",
            agent_id="jarvis_advisor",
            swarm_id=str(tenant_id),
            error=str(exc)[:200],
        )
        return True
    return False


async def push_jarvis_proactive_nudge(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    step: MissionJarvisStepOut | None,
) -> bool:
    """Push top Jarvis step to mission feed when dedup window allows."""

    if not settings.jarvis_proactive_nudge_enabled or step is None:
        return False

    if not await _dedup_claim(tenant_id=tenant_id, step=step):
        return False

    await push_mission_feed_event(
        tenant_id=tenant_id,
        kind="jarvis_nudge",
        title=step.title[:200],
        body=step.detail[:500],
        href=step.href[:300],
        entity_id=f"jarvis_{step.kind}",
    )

    if settings.jarvis_proactive_nudge_web_push_enabled:
        await maybe_send_mission_feed_web_push(
            session,
            tenant_id=tenant_id,
            title=f"Jarvis · {step.title[:100]}",
            body=step.detail[:240],
            href=step.href[:300],
        )

    logger.info(
        "jarvis_nudge.pushed",
        agent_id="jarvis_advisor",
        swarm_id=str(tenant_id),
        task_id=f"jarvis_{step.kind}",
        kind=step.kind,
    )
    return True


async def run_jarvis_proactive_nudge_for_tenant(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    dashboard_user_id: uuid.UUID,
) -> bool:
    """Celery-safe: compose advisor top step and push nudge if due."""

    from app.application.services.mission_home_service import compose_mission_home_snapshot
    from app.infrastructure.persistence.models.tenant import Tenant

    tenant = await session.get(Tenant, tenant_id)
    snapshot = await compose_mission_home_snapshot(
        session,
        tenant_id=tenant_id,
        dashboard_user_id=dashboard_user_id,
        tenant=tenant,
    )
    if not snapshot.jarvis_advisor_strip.enabled or not snapshot.jarvis_advisor_strip.steps:
        return False
    return await push_jarvis_proactive_nudge(
        session,
        tenant_id=tenant_id,
        step=snapshot.jarvis_advisor_strip.steps[0],
    )


__all__ = [
    "push_jarvis_proactive_nudge",
    "run_jarvis_proactive_nudge_for_tenant",
]
