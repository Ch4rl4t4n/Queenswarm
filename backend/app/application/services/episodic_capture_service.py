"""MEM1 — Auto episodic capture: completed session → daily summarized log."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, timedelta
from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.loop_guardrails_service import last_rubric_score_from_summary
from app.core.config import settings
from app.core.logging import get_logger
from app.infrastructure.persistence.models.supervisor_session import SubAgentSession, SupervisorSession
from app.infrastructure.persistence.models.tenant import Tenant

_logger = get_logger(__name__)

EPISODIC_CAPTURES_BUCKET = "episodic_captures"
_MAX_CAPTURES = 400
_MIN_SUMMARY_CHARS = 48


class EpisodicCaptureOut(BaseModel):
    """One auto-captured completed session row."""

    model_config = ConfigDict(extra="ignore")

    capture_id: str
    session_id: str
    captured_at: str
    day: str
    goal: str
    summary: str
    status: str = "completed"
    rubric_score: float | None = None
    href: str | None = None


class EpisodicDailyLogDayOut(BaseModel):
    """One UTC day in the MemSearch-style daily episodic log."""

    model_config = ConfigDict(extra="ignore")

    date: str
    session_count: int = 0
    headline: str = ""
    summary_md: str = ""
    captures: list[EpisodicCaptureOut] = Field(default_factory=list)


class EpisodicDailyLogOut(BaseModel):
    """Operator-facing daily episodic log (MEM1)."""

    model_config = ConfigDict(extra="ignore")

    enabled: bool = True
    retention_days: int = 90
    days: list[EpisodicDailyLogDayOut] = Field(default_factory=list)
    total_captures: int = 0
    operator_hint: str = "Completed supervisor sessions auto-capture into the daily episodic log."


def _clip(text: str, limit: int = 320) -> str:
    cleaned = " ".join((text or "").strip().split())
    if len(cleaned) <= limit:
        return cleaned
    return f"{cleaned[: limit - 1]}…"


def _captures_bucket(operator_settings: dict[str, Any] | None) -> dict[str, Any]:
    root = dict(operator_settings or {})
    bucket = root.get(EPISODIC_CAPTURES_BUCKET)
    if not isinstance(bucket, dict):
        return {"captures": [], "updated_at": None}
    captures = bucket.get("captures")
    if not isinstance(captures, list):
        captures = []
    return {
        "captures": [row for row in captures if isinstance(row, dict)],
        "updated_at": bucket.get("updated_at"),
    }


def _merge_capture_bucket(operator_settings: dict[str, Any] | None, capture: dict[str, Any]) -> dict[str, Any]:
    root = dict(operator_settings or {})
    bucket = _captures_bucket(root)
    captures = list(bucket.get("captures") or [])
    session_id = str(capture.get("session_id") or "")
    if session_id and any(str(row.get("session_id")) == session_id for row in captures):
        return root
    captures.insert(0, capture)
    bucket["captures"] = captures[:_MAX_CAPTURES]
    bucket["updated_at"] = datetime.now(tz=UTC).isoformat()
    root[EPISODIC_CAPTURES_BUCKET] = bucket
    return root


async def _best_session_excerpt(db: AsyncSession, *, supervisor_session_id: uuid.UUID) -> str:
    rows = list(
        (
            await db.scalars(
                select(SubAgentSession)
                .where(SubAgentSession.supervisor_session_id == supervisor_session_id)
                .order_by(SubAgentSession.spawn_order.asc()),
            )
        ).all(),
    )
    priority = ("critic", "reporter", "coder", "publisher", "researcher")
    by_role = {str(row.role or "").lower(): row for row in rows if str(row.status or "").lower() == "completed"}
    for role in priority:
        row = by_role.get(role)
        if row is None:
            continue
        memory = dict(row.short_memory or {})
        text = str(memory.get("last_summary") or row.last_output or "").strip()
        if len(text) >= _MIN_SUMMARY_CHARS:
            return text
    for row in reversed(rows):
        if str(row.status or "").lower() != "completed":
            continue
        memory = dict(row.short_memory or {})
        text = str(memory.get("last_summary") or row.last_output or "").strip()
        if len(text) >= _MIN_SUMMARY_CHARS:
            return text
    return ""


def _should_skip_capture(session: SupervisorSession) -> bool:
    ctx = dict(session.context_summary or {})
    if ctx.get("episodic_captured") is True:
        return True
    if ctx.get("skip_episodic_capture") is True:
        return True
    if ctx.get("skill_factory") is True:
        return True
    return False


def build_capture_record(
    session: SupervisorSession,
    *,
    summary: str,
    captured_at: datetime | None = None,
) -> dict[str, Any]:
    """Build one MEM1 capture dict from a completed supervisor session."""

    moment = captured_at or session.completed_at or datetime.now(tz=UTC)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=UTC)
    ctx = dict(session.context_summary or {})
    goal = str(ctx.get("raw_goal") or session.goal or "Supervisor session").strip()
    rubric = last_rubric_score_from_summary(ctx)
    patterns = ctx.get("agentic_patterns")
    pattern_list: list[str] = []
    if isinstance(patterns, dict):
        pattern_list = [str(item) for item in (patterns.get("primary") or [])[:4]]
    return {
        "capture_id": f"capture:{session.id}",
        "session_id": str(session.id),
        "captured_at": moment.isoformat(),
        "day": moment.date().isoformat(),
        "goal": _clip(goal, 240),
        "summary": _clip(summary, 900),
        "status": str(session.status or "completed"),
        "rubric_score": rubric,
        "patterns": pattern_list,
        "href": f"/agents?session={session.id}",
    }


def derive_episodic_daily_log(
    captures: list[dict[str, Any]],
    *,
    days: int = 14,
    retention_days: int | None = None,
) -> EpisodicDailyLogOut:
    """Group persisted captures into daily summarized log rows."""

    window = max(1, min(days, 90))
    retention = retention_days or settings.episodic_memory_retention_days
    cutoff = datetime.now(tz=UTC).date() - timedelta(days=max(1, retention))
    day_keys = [(datetime.now(tz=UTC).date() - timedelta(days=offset)).isoformat() for offset in range(window)]
    by_day: dict[str, list[dict[str, Any]]] = {key: [] for key in day_keys}

    for row in captures:
        day = str(row.get("day") or "")
        if day < cutoff.isoformat():
            continue
        if day not in by_day:
            by_day[day] = []
        by_day[day].append(row)

    days_out: list[EpisodicDailyLogDayOut] = []
    for day_key in day_keys:
        day_rows = sorted(
            by_day.get(day_key) or [],
            key=lambda item: str(item.get("captured_at") or ""),
            reverse=True,
        )
        capture_models = [
            EpisodicCaptureOut(
                capture_id=str(row.get("capture_id") or row.get("session_id") or ""),
                session_id=str(row.get("session_id") or ""),
                captured_at=str(row.get("captured_at") or ""),
                day=day_key,
                goal=str(row.get("goal") or ""),
                summary=str(row.get("summary") or ""),
                status=str(row.get("status") or "completed"),
                rubric_score=row.get("rubric_score") if isinstance(row.get("rubric_score"), (int, float)) else None,
                href=str(row.get("href") or "") or None,
            )
            for row in day_rows
        ]
        headlines = [_clip(str(row.goal or ""), 48) for row in capture_models[:3]]
        headline = "; ".join(headlines) if headlines else "No completed sessions"
        summary_lines = [
            f"- **{row.goal}** — {row.summary}"
            for row in capture_models
        ]
        summary_md = "\n".join(summary_lines) if summary_lines else "_No auto-captured sessions this day._"
        days_out.append(
            EpisodicDailyLogDayOut(
                date=day_key,
                session_count=len(capture_models),
                headline=headline,
                summary_md=summary_md,
                captures=capture_models,
            ),
        )

    total = sum(day.session_count for day in days_out)
    hint = (
        "Daily log auto-updates when supervisor sessions complete — MemSearch-style recall without leaky dumps."
        if total > 0
        else "Complete a supervisor session to seed the first daily episodic capture."
    )
    return EpisodicDailyLogOut(
        enabled=True,
        retention_days=retention,
        days=days_out,
        total_captures=total,
        operator_hint=hint,
    )


async def capture_episodic_session(
    db: AsyncSession,
    *,
    session: SupervisorSession,
) -> bool:
    """Persist one MEM1 episodic capture for a completed session."""

    if not settings.auto_episodic_capture_enabled or not settings.episodic_memory_enabled:
        return False
    if session.tenant_id is None:
        return False
    if str(session.status or "").lower() != "completed":
        return False
    if _should_skip_capture(session):
        return False

    excerpt = await _best_session_excerpt(db, supervisor_session_id=session.id)
    if len(excerpt) < _MIN_SUMMARY_CHARS:
        goal_only = str(session.goal or "").strip()
        if len(goal_only) < _MIN_SUMMARY_CHARS:
            return False
        excerpt = goal_only

    tenant = await db.get(Tenant, session.tenant_id)
    if tenant is None:
        return False

    capture = build_capture_record(session, summary=excerpt)
    tenant.operator_settings = _merge_capture_bucket(tenant.operator_settings, capture)
    ctx = dict(session.context_summary or {})
    ctx["episodic_captured"] = True
    session.context_summary = ctx
    await db.flush()

    _logger.info(
        "episodic_capture.persisted",
        agent_id="episodic_capture",
        swarm_id=str(session.tenant_id),
        task_id=str(session.id),
        day=capture.get("day"),
    )
    return True


async def compose_episodic_daily_log(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    days: int = 14,
) -> EpisodicDailyLogOut:
    """Return MEM1 daily summarized log for operator UI."""

    if not settings.auto_episodic_capture_enabled or not settings.episodic_memory_enabled:
        return EpisodicDailyLogOut(enabled=False)

    tenant = await db.get(Tenant, tenant_id)
    bucket = _captures_bucket(tenant.operator_settings if tenant else None)
    return derive_episodic_daily_log(
        list(bucket.get("captures") or []),
        days=days,
        retention_days=settings.episodic_memory_retention_days,
    )


def list_episodic_capture_timeline_items(
    captures: list[dict[str, Any]],
    *,
    cutoff: datetime,
    limit: int,
) -> list[dict[str, Any]]:
    """Map persisted captures into episodic timeline rows."""

    items: list[dict[str, Any]] = []
    for row in captures:
        captured_at = str(row.get("captured_at") or "")
        if not captured_at:
            continue
        try:
            moment = datetime.fromisoformat(captured_at.replace("Z", "+00:00"))
        except ValueError:
            continue
        if moment < cutoff:
            continue
        session_id = str(row.get("session_id") or "")
        goal = str(row.get("goal") or "Session capture")
        summary = str(row.get("summary") or "")
        rubric = row.get("rubric_score")
        rubric_note = f" Rubric {float(rubric):.0%}." if isinstance(rubric, (int, float)) else ""
        items.append(
            {
                "id": str(row.get("capture_id") or f"capture:{session_id}"),
                "kind": "episodic_capture",
                "occurred_at": captured_at,
                "title": _clip(goal, 96),
                "summary": _clip(f"{summary}{rubric_note}", 280),
                "session_id": session_id or None,
                "metadata": {
                    "day": row.get("day"),
                    "patterns": row.get("patterns") or [],
                    "auto_capture": True,
                },
            },
        )
    items.sort(key=lambda item: str(item.get("occurred_at") or ""), reverse=True)
    return items[:limit]


__all__ = [
    "EPISODIC_CAPTURES_BUCKET",
    "EpisodicCaptureOut",
    "EpisodicDailyLogDayOut",
    "EpisodicDailyLogOut",
    "build_capture_record",
    "capture_episodic_session",
    "compose_episodic_daily_log",
    "derive_episodic_daily_log",
    "list_episodic_capture_timeline_items",
]
