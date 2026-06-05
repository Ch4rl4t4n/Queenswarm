"""BA5 — Telegram delivery for proactive midday pulse."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.proactive_pulse import compose_proactive_pulse
from app.application.services.execution_studio_notifications import _resolve_telegram_credentials
from app.core.config import settings
from app.core.logging import get_logger
from app.core.notifications import notify_telegram
from app.infrastructure.persistence.models.tenant import Tenant

_logger = get_logger(__name__)


async def notify_proactive_pulse_midday_telegram(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    dashboard_user_id: uuid.UUID,
) -> dict[str, bool]:
    """Midday Telegram digest — what changed + autonomous runs."""

    if not settings.proactive_pulse_telegram_midday_enabled:
        return {"telegram": False}

    tenant = await db.get(Tenant, tenant_id)
    pulse = await compose_proactive_pulse(
        db,
        tenant_id=tenant_id,
        dashboard_user_id=dashboard_user_id,
        tenant=tenant,
        phase="midday",
    )

    token, chat_id = _resolve_telegram_credentials(tenant)
    if not token or not chat_id:
        return {"telegram": False}

    lines = [f"🕛 *Hive pulse — midday*", f"_{pulse.headline}_"]
    if pulse.changes:
        lines.append("")
        lines.append("*Changed:*")
        for change in pulse.changes[:5]:
            lines.append(f"• {change.label}")
    if pulse.autonomous_runs:
        lines.append("")
        lines.append("*Ran autonomously:*")
        for run in pulse.autonomous_runs[:5]:
            lines.append(f"• {run.label}")

    domain = str(settings.domain or "queenswarm.love").strip().rstrip("/")
    base = f"https://{domain}" if not domain.startswith("http") else domain.rstrip("/")
    lines.append(f"\n{base}/cockpit")

    ok = await notify_telegram("\n".join(lines), bot_token=token, chat_id=chat_id)
    _logger.info(
        "proactive_pulse.telegram_midday",
        agent_id="proactive_pulse",
        task_id=str(tenant_id),
        sent=ok,
    )
    return {"telegram": ok}


__all__ = ["notify_proactive_pulse_midday_telegram"]
