"""Enterprise alert dispatch with cooldown and external channel fan-out."""

from __future__ import annotations

import time
from typing import Any

from app.core.config import settings
from app.core.logging import get_logger
from app.core.notifications import notify_enterprise_alert
from app.core.redis_client import get_json, set_json

logger = get_logger(__name__)


def _cooldown_key(code: str) -> str:
    safe = (code or "unknown").strip().lower().replace(" ", "_")
    return f"queenswarm:alerts:cooldown:{safe[:64]}"


async def dispatch_alert_if_due(*, code: str, severity: str, title: str, message: str) -> bool:
    """Send alert only when per-code cooldown elapsed."""

    if not settings.alerting_enabled:
        return False
    now = time.time()
    key = _cooldown_key(code)
    last = await get_json(key)
    if isinstance(last, dict):
        previous = float(last.get("ts") or 0.0)
        if previous > 0 and (now - previous) < float(settings.alert_dispatch_cooldown_sec):
            return False

    channels = await notify_enterprise_alert(title=title, message=message, severity=severity)
    delivered = any(channels.values())
    if delivered:
        await set_json(
            key,
            {"ts": now, "channels": channels},
            ttl=max(int(settings.alert_dispatch_cooldown_sec) * 3, 120),
        )
        logger.info(
            "enterprise_alert.sent",
            agent_id="enterprise_alerting",
            swarm_id="global",
            task_id=code,
            channels=channels,
            severity=severity,
        )
    else:
        logger.warning(
            "enterprise_alert.not_delivered",
            agent_id="enterprise_alerting",
            swarm_id="global",
            task_id=code,
            severity=severity,
        )
    return delivered


async def dispatch_alert_batch(alerts: list[dict[str, Any]]) -> int:
    """Dispatch eligible alert list, returning count of delivered alerts."""

    sent = 0
    for alert in alerts:
        code = str(alert.get("code") or "unknown")
        severity = str(alert.get("severity") or "warning")
        title = str(alert.get("title") or code.replace("_", " ").title())
        message = str(alert.get("message") or "")
        if not message:
            continue
        delivered = await dispatch_alert_if_due(
            code=code,
            severity=severity,
            title=title,
            message=message,
        )
        if delivered:
            sent += 1
    return sent


__all__ = ["dispatch_alert_batch", "dispatch_alert_if_due"]
