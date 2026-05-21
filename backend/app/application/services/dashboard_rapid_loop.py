"""Rapid learning loop telemetry for the operator dashboard widget."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any, Literal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.infrastructure.persistence.models.enums import TaskStatus
from app.infrastructure.persistence.models.knowledge import KnowledgeItem, LearningLog
from app.infrastructure.persistence.models.task import Task

StageId = Literal["scrape", "reflect", "simulate", "reward"]
StageStatus = Literal["idle", "active", "ok", "warn"]


def _iso(dt: datetime | None) -> str | None:
    """Serialize a timezone-aware datetime for JSON payloads."""

    if dt is None:
        return None
    stamp = dt if dt.tzinfo is not None else dt.replace(tzinfo=UTC)
    return stamp.isoformat()


def compute_sla_metrics(
    *,
    durations_sec: list[float],
    sla_target_sec: float,
) -> dict[str, float | None]:
    """Derive SLA compliance from completed cycle durations."""

    if not durations_sec:
        return {
            "avg_cycle_sec": None,
            "last_cycle_sec": None,
            "sla_met_pct": None,
        }
    met = sum(1 for value in durations_sec if value <= sla_target_sec)
    return {
        "avg_cycle_sec": round(sum(durations_sec) / len(durations_sec), 2),
        "last_cycle_sec": round(durations_sec[0], 2),
        "sla_met_pct": round((met / len(durations_sec)) * 100.0, 1),
    }


def stage_status(*, count: int, last_at: datetime | None, now: datetime) -> StageStatus:
    """Map stage activity to a UI-friendly status tone."""

    if last_at is None:
        return "idle"
    stamp = last_at if last_at.tzinfo is not None else last_at.replace(tzinfo=UTC)
    age_sec = (now - stamp).total_seconds()
    if age_sec <= float(settings.rapid_loop_timeout_sec):
        return "active"
    if count > 0 and age_sec <= 86_400:
        return "ok"
    return "warn"


def build_stage_row(
    *,
    stage_id: StageId,
    label: str,
    count: int,
    last_at: datetime | None,
    now: datetime,
) -> dict[str, Any]:
    """Compose one rapid-loop pipeline stage for the dashboard widget."""

    return {
        "id": stage_id,
        "label": label,
        "count_24h": int(count),
        "last_at": _iso(last_at),
        "status": stage_status(count=count, last_at=last_at, now=now),
    }


async def build_rapid_loop_payload(
    db: AsyncSession,
    *,
    window_hours: int = 24,
) -> dict[str, Any]:
    """Aggregate scrape → reflect → simulate → reward counts and SLA for the tenant."""

    now = datetime.now(tz=UTC)
    window_start = now - timedelta(hours=max(1, min(window_hours, 168)))
    sla_target_sec = float(settings.rapid_loop_timeout_sec)

    scrape_count = int(
        await db.scalar(
            select(func.count())
            .select_from(KnowledgeItem)
            .where(KnowledgeItem.scraped_at >= window_start),
        )
        or 0,
    )
    scrape_last = await db.scalar(
        select(func.max(KnowledgeItem.scraped_at)).where(KnowledgeItem.scraped_at >= window_start),
    )

    reflect_count = int(
        await db.scalar(
            select(func.count())
            .select_from(LearningLog)
            .where(LearningLog.created_at >= window_start),
        )
        or 0,
    )
    reflect_last = await db.scalar(
        select(func.max(LearningLog.created_at)).where(LearningLog.created_at >= window_start),
    )

    simulate_count = int(
        await db.scalar(
            select(func.count())
            .select_from(Task)
            .where(
                Task.status == TaskStatus.COMPLETED,
                Task.completed_at.is_not(None),
                Task.completed_at >= window_start,
            ),
        )
        or 0,
    )
    simulate_last = await db.scalar(
        select(func.max(Task.completed_at)).where(
            Task.status == TaskStatus.COMPLETED,
            Task.completed_at.is_not(None),
            Task.completed_at >= window_start,
        ),
    )

    reward_count = int(
        await db.scalar(
            select(func.count())
            .select_from(LearningLog)
            .where(
                LearningLog.created_at >= window_start,
                LearningLog.pollen_earned > 0.0,
            ),
        )
        or 0,
    )
    reward_last = await db.scalar(
        select(func.max(LearningLog.created_at)).where(
            LearningLog.created_at >= window_start,
            LearningLog.pollen_earned > 0.0,
        ),
    )

    duration_rows = (
        await db.execute(
            select(Task.started_at, Task.completed_at)
            .where(
                Task.status == TaskStatus.COMPLETED,
                Task.started_at.is_not(None),
                Task.completed_at.is_not(None),
                Task.completed_at >= window_start,
            )
            .order_by(Task.completed_at.desc())
            .limit(40),
        )
    ).all()

    durations_sec: list[float] = []
    last_cycle_at: datetime | None = None
    for started_at, completed_at in duration_rows:
        if started_at is None or completed_at is None:
            continue
        start = started_at if started_at.tzinfo is not None else started_at.replace(tzinfo=UTC)
        end = completed_at if completed_at.tzinfo is not None else completed_at.replace(tzinfo=UTC)
        durations_sec.append(max(0.0, (end - start).total_seconds()))
        if last_cycle_at is None:
            last_cycle_at = end

    sla = compute_sla_metrics(durations_sec=durations_sec, sla_target_sec=sla_target_sec)

    stages = [
        build_stage_row(stage_id="scrape", label="Scrape", count=scrape_count, last_at=scrape_last, now=now),
        build_stage_row(stage_id="reflect", label="Reflect", count=reflect_count, last_at=reflect_last, now=now),
        build_stage_row(stage_id="simulate", label="Simulate", count=simulate_count, last_at=simulate_last, now=now),
        build_stage_row(stage_id="reward", label="Reward", count=reward_count, last_at=reward_last, now=now),
    ]

    loop_healthy = (
        simulate_count > 0
        and (sla["sla_met_pct"] is None or float(sla["sla_met_pct"]) >= 50.0)
        and any(stage["status"] in {"active", "ok"} for stage in stages)
    )

    return {
        "generated_at": now.isoformat(),
        "window_hours": window_hours,
        "sla_target_sec": int(sla_target_sec),
        "sla_met_pct": sla["sla_met_pct"],
        "avg_cycle_sec": sla["avg_cycle_sec"],
        "last_cycle_sec": sla["last_cycle_sec"],
        "last_cycle_at": _iso(last_cycle_at),
        "stages": stages,
        "loop_healthy": loop_healthy,
    }


__all__ = [
    "build_rapid_loop_payload",
    "build_stage_row",
    "compute_sla_metrics",
    "stage_status",
]
