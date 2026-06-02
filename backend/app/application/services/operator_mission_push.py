"""Web Push fan-out for operator mission feed events."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.execution_studio_push import send_execution_studio_web_push
from app.core.logging import get_logger
from app.infrastructure.persistence.models.tenant import Tenant

_logger = get_logger(__name__)


async def maybe_send_mission_feed_web_push(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    title: str,
    body: str,
    href: str,
) -> None:
    """Best-effort browser push using Execution Studio subscription store."""

    tenant = await session.get(Tenant, tenant_id)
    if tenant is None:
        return
    try:
        stats = await send_execution_studio_web_push(
            tenant=tenant,
            title=title[:120],
            body=body[:240],
            url=href[:300],
            session=session,
        )
        if stats.get("sent"):
            _logger.info(
                "operator_mission_push.sent",
                agent_id="operator_hub",
                swarm_id=str(tenant_id),
                task_id="mission_feed",
                sent=stats.get("sent"),
            )
    except Exception as exc:
        _logger.warning(
            "operator_mission_push.failed",
            agent_id="operator_hub",
            swarm_id=str(tenant_id),
            error_type=type(exc).__name__,
            error=str(exc)[:200],
        )


__all__ = ["maybe_send_mission_feed_web_push"]
