"""Human-readable schedule parsing + due checks for Celery Beat ticks."""

from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta
from typing import Any

from croniter import croniter

from app.core.logging import get_logger
from app.models.agent_config import AgentConfig

logger = get_logger(__name__)


def parse_schedule_to_cron(schedule_value: str) -> str | None:
    """Map friendly operator text to a 5-field cron string (minute hour dom mon dow)."""

    if not schedule_value:
        return None
    s = schedule_value.lower().strip()

    m = re.match(r"every\s+(\d+)\s+hours?", s)
    if m:
        return f"0 */{m.group(1)} * * *"

    m = re.match(r"every\s+(\d+)\s+minutes?", s)
    if m:
        return f"*/{m.group(1)} * * * *"

    m = re.match(r"daily\s+(\d{1,2}):(\d{2})", s)
    if m:
        return f"{m.group(2)} {m.group(1)} * * *"

    m = re.match(r"every\s+day\s+at\s+(\d{1,2}):(\d{2})", s)
    if m:
        return f"{m.group(2)} {m.group(1)} * * *"

    days = {
        "monday": 1,
        "tuesday": 2,
        "wednesday": 3,
        "thursday": 4,
        "friday": 5,
        "saturday": 6,
        "sunday": 0,
    }
    for day, dow in days.items():
        pattern = rf"(?:every\s+)?{day}\s+(\d{{1,2}}):(\d{{2}})"
        m = re.match(pattern, s)
        if m:
            return f"{m.group(2)} {m.group(1)} * * {dow}"

    if re.match(r"^[\d\*/\-,\s]{8,}$", s) and croniter.is_valid(s):
        return schedule_value.strip()

    return None


def parse_human_interval(schedule_value: str) -> timedelta | None:
    """Return timedelta for explicit ``every N hours/minutes`` strings."""

    if not schedule_value:
        return None
    s = schedule_value.lower().strip()
    if m := re.match(r"every\s+(\d+)\s+hours?", s):
        return timedelta(hours=int(m.group(1)))
    if m := re.match(r"every\s+(\d+)\s+minutes?", s):
        return timedelta(minutes=int(m.group(1)))
    return None


def should_run_dynamic_agent(cfg: AgentConfig, *, now: datetime | None = None) -> bool:
    """Decide whether a scheduled universal agent should enqueue another run."""

    if not cfg.is_active:
        return False

    lowered = cfg.schedule_type.lower().strip()
    if lowered == "on_demand" or lowered == "trigger":
        return False

    if lowered not in {"interval", "cron"}:
        logger.warning("scheduler.unknown_schedule_type", schedule_type=cfg.schedule_type, agent_id=str(cfg.agent_id))
        return False

    moment = now or datetime.now(tz=UTC)
    raw = (cfg.schedule_value or "").strip()
    if not raw:
        return False

    if lowered == "cron":
        cron_expr = parse_schedule_to_cron(raw) or (raw if croniter.is_valid(raw) else None)
        if cron_expr is None:
            return False
        try:
            return bool(croniter.match(cron_expr, moment))
        except Exception as exc:  # noqa: BLE001 — croniter rejects odd exprs
            logger.warning(
                "scheduler.cron_match_failed",
                cron=cron_expr,
                agent_id=str(cfg.agent_id),
                error=str(exc),
            )
            return False

    delta = parse_human_interval(raw)
    if delta is None:
        cron_expr = parse_schedule_to_cron(raw)
        if cron_expr is None:
            return False
        try:
            return bool(croniter.match(cron_expr, moment))
        except Exception:
            return False

    if cfg.last_run_at is None:
        return True
    last = cfg.last_run_at
    if last.tzinfo is None:
        last = last.replace(tzinfo=UTC)
    else:
        last = last.astimezone(UTC)
    return moment - last >= delta


def describe_next_hint(cfg: AgentConfig) -> dict[str, Any]:
    """Lightweight operator hint for logs (not a full planner)."""

    return {
        "agent_id": str(cfg.agent_id),
        "schedule_type": cfg.schedule_type,
        "schedule_value": cfg.schedule_value,
        "parsed_cron": parse_schedule_to_cron(cfg.schedule_value or ""),
        "interval": str(parse_human_interval(cfg.schedule_value or "") or ""),
    }


__all__ = [
    "describe_next_hint",
    "parse_human_interval",
    "parse_schedule_to_cron",
    "should_run_dynamic_agent",
]
