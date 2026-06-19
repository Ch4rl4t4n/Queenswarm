"""ST7 — Personal OS eval metrics (HN5) for operator cockpit."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.persistence.models.supervisor_session import SupervisorSession


class PersonalOsEvalMetricsOut(BaseModel):
    """Lightweight AFK quality metrics — no new dashboard engine."""

    model_config = ConfigDict(extra="ignore")

    window_days: int = 7
    sessions_completed: int = 0
    sessions_stopped_discipline: int = 0
    digest_promoted: int = 0
    approve_rate_pct: float | None = None
    message: str = ""


async def compose_personal_os_eval_metrics(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    window_days: int = 7,
) -> PersonalOsEvalMetricsOut:
    """Aggregate session outcomes for coach ritual / HN5 strip."""

    since = datetime.now(tz=UTC) - timedelta(days=max(1, window_days))
    rows = list(
        (
            await session.scalars(
                select(SupervisorSession).where(
                    SupervisorSession.tenant_id == tenant_id,
                    SupervisorSession.created_at >= since,
                ),
            )
        ).all(),
    )

    completed = sum(1 for r in rows if str(r.status or "").lower() == "completed")
    discipline_stopped = sum(
        1
        for r in rows
        if str(r.status or "").lower() == "stopped"
        and bool((r.context_summary or {}).get("discipline_halt_at"))
    )
    promoted = sum(1 for r in rows if (r.context_summary or {}).get("digest_promoted"))
    approved = sum(
        1
        for r in rows
        if str((r.context_summary or {}).get("approval_state") or "").lower() in {"approve", "approved"}
    )
    rate = round(approved / completed * 100.0, 1) if completed else None

    return PersonalOsEvalMetricsOut(
        window_days=window_days,
        sessions_completed=completed,
        sessions_stopped_discipline=discipline_stopped,
        digest_promoted=promoted,
        approve_rate_pct=rate,
        message=(
            f"{completed} completed · {promoted} promoted · {discipline_stopped} discipline stops (7d)."
            if rows
            else "No supervisor sessions in window — run a four-lane digest."
        ),
    )


__all__ = ["PersonalOsEvalMetricsOut", "compose_personal_os_eval_metrics"]
