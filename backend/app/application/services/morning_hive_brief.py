"""Morning Hive Brief — composite digest from solo trio lane outputs."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.queen_maintainer.tech_health import build_tech_health_report
from app.application.services.solo_operator_trio import get_solo_trio_status
from app.core.logging import get_logger
from app.infrastructure.persistence.models.supervisor_session import SubAgentSession, SupervisorSession

logger = get_logger(__name__)


async def _session_excerpt(
    db: AsyncSession,
    *,
    session_id: uuid.UUID,
    max_chars: int = 1200,
) -> str:
    """Load a short excerpt from the latest sub-agent summary."""

    row = await db.scalar(
        select(SubAgentSession)
        .where(SubAgentSession.supervisor_session_id == session_id)
        .order_by(desc(SubAgentSession.spawn_order))
        .limit(1),
    )
    if row is None:
        return ""
    memory = dict(row.short_memory or {})
    text = str(memory.get("last_summary") or row.last_output or "").strip()
    return text[:max_chars]


async def _latest_completed_session(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    routine_id: uuid.UUID,
) -> SupervisorSession | None:
    stmt = (
        select(SupervisorSession)
        .where(
            SupervisorSession.tenant_id == tenant_id,
            SupervisorSession.context_summary["routine_id"].astext == str(routine_id),
            SupervisorSession.status == "completed",
        )
        .order_by(desc(SupervisorSession.completed_at))
        .limit(1)
    )
    return await db.scalar(stmt)


async def compose_forager_brief_section(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
) -> list[dict[str, Any]]:
    """Compact forager KPI rows for morning brief."""

    from app.application.services.dashboard_foragers_overview import build_foragers_overview_payload

    payload = await build_foragers_overview_payload(db)
    rows: list[dict[str, Any]] = []
    for row in payload.get("configurations") or []:
        if not isinstance(row, dict):
            continue
        rows.append(
            {
                "id": row.get("id"),
                "name": row.get("source_name"),
                "status": row.get("status"),
                "items_count": row.get("items_count", 0),
                "progress_pct": row.get("run_progress_pct", 0),
                "progress_kind": row.get("progress_kind"),
            },
        )
    _ = tenant_id
    return rows[:12]


async def compose_morning_hive_brief(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    """Assemble a verified morning digest from trio lanes + tech health."""

    trio = await get_solo_trio_status(db, tenant_id=tenant_id)
    tech = build_tech_health_report()
    sections: list[dict[str, Any]] = []
    markdown_parts: list[str] = [
        f"# Morning Hive Brief",
        f"_Generated {datetime.now(tz=UTC).strftime('%Y-%m-%d %H:%M UTC')}_",
        "",
        f"**Tech health:** {float(tech.get('health_score', 0.0)):.0%}",
        "",
    ]

    for lane in trio.get("lanes") or []:
        lane_id = str(lane.get("lane_id") or "")
        label = str(lane.get("label") or lane_id)
        routine_id_raw = lane.get("routine_id")
        excerpt = ""
        session_status = lane.get("last_session_status")
        verify_status = None

        if routine_id_raw:
            routine_uuid = uuid.UUID(str(routine_id_raw))
            session = await _latest_completed_session(
                db,
                tenant_id=tenant_id,
                routine_id=routine_uuid,
            )
            if session is not None:
                excerpt = await _session_excerpt(db, session_id=session.id)
                session_status = session.status
                ctx = dict(session.context_summary or {})
                verify_status = ctx.get("hivemind_verify_status")

        sections.append(
            {
                "lane_id": lane_id,
                "label": label,
                "routine_name": lane.get("routine_name"),
                "binding": lane.get("binding"),
                "last_session_status": session_status,
                "hivemind_verify_status": verify_status,
                "excerpt": excerpt,
            },
        )

        markdown_parts.append(f"## {label}")
        if lane.get("binding") == "missing":
            markdown_parts.append(f"_No routine bound — build `{lane.get('swarm_hint')}` swarm._")
        elif not excerpt:
            markdown_parts.append("_No completed session yet — run today's trio cycle._")
        else:
            if verify_status:
                markdown_parts.append(f"_Verify: {verify_status}_")
            markdown_parts.append(excerpt)
        markdown_parts.append("")

    signals = tech.get("signals") or []
    if signals:
        markdown_parts.append("## SCV signals")
        markdown_parts.extend(f"- {sig}" for sig in signals[:6])
        markdown_parts.append("")

    foragers = await compose_forager_brief_section(db, tenant_id=tenant_id)
    if foragers:
        markdown_parts.append("## Foragers")
        for row in foragers:
            markdown_parts.append(
                f"- **{row.get('name')}** · {row.get('status')} · "
                f"{row.get('items_count', 0)} items · {row.get('progress_pct', 0)}% "
                f"({row.get('progress_kind')})",
            )
        markdown_parts.append("")

    markdown = "\n".join(markdown_parts).strip()
    logger.info(
        "morning_brief.composed",
        agent_id="morning_hive_brief",
        swarm_id=str(tenant_id),
        task_id="compose",
        sections=len(sections),
    )
    return {
        "generated_at": datetime.now(tz=UTC).isoformat(),
        "tech_health_score": float(tech.get("health_score", 0.0)),
        "lanes_bound": trio.get("lanes_bound", 0),
        "sections": sections,
        "foragers": foragers,
        "markdown": markdown,
    }


__all__ = ["compose_forager_brief_section", "compose_morning_hive_brief"]
