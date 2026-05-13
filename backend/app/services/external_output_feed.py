"""Persist and list generic orchestrator results for external pull clients."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.external_output import ExternalOutput

logger = get_logger(__name__)

_DEFAULT_TAGS: tuple[str, ...] = ("hive.mission", "orchestrator.delivery")


def normalize_tag_filter(raw: str | None) -> list[str]:
    """Split a comma-separated tag filter into non-empty tokens."""

    if raw is None or not raw.strip():
        return []
    return [p.strip() for p in raw.split(",") if p.strip()]


def parse_since_iso(raw: str | None) -> datetime | None:
    """Parse optional ISO-8601 ``since`` (accepts trailing ``Z``)."""

    if raw is None or not raw.strip():
        return None
    candidate = raw.strip().replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(candidate)
    except ValueError as exc:
        msg = "Invalid since timestamp (use ISO-8601)."
        raise ValueError(msg) from exc
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


async def record_orchestrator_delivery(
    session: AsyncSession,
    *,
    dashboard_user_id: uuid.UUID,
    mission_id: uuid.UUID,
    session_id: uuid.UUID | None,
    text_report: str,
    voice_script: str | None,
    output_metadata: dict[str, Any],
    simulation_outcome: dict[str, Any] | None,
    tags: Sequence[str] | None = None,
    orchestrator_agent_id: uuid.UUID | None = None,
) -> ExternalOutput:
    """Insert one feed row (caller commits)."""

    merged_tags = list(dict.fromkeys([*_DEFAULT_TAGS, *(tags or [])]))
    row = ExternalOutput(
        id=uuid.uuid4(),
        dashboard_user_id=dashboard_user_id,
        mission_id=mission_id,
        session_id=session_id,
        text_report=text_report.strip(),
        voice_script=voice_script.strip() if voice_script else None,
        output_metadata=dict(output_metadata),
        simulation_outcome=dict(simulation_outcome) if simulation_outcome is not None else None,
        tags=merged_tags,
    )
    session.add(row)
    await session.flush()
    logger.info(
        "external_output.recorded",
        agent_id=str(orchestrator_agent_id) if orchestrator_agent_id is not None else "",
        swarm_id=str(dashboard_user_id),
        task_id=str(mission_id),
    )
    return row


async def list_external_results(
    session: AsyncSession,
    *,
    dashboard_user_id: uuid.UUID,
    since: datetime | None,
    limit: int,
    tag_filter: Sequence[str],
) -> list[ExternalOutput]:
    """Return newest rows for the API key owner, optionally filtered."""

    cap = max(1, min(limit, 200))
    stmt = (
        select(ExternalOutput)
        .where(ExternalOutput.dashboard_user_id == dashboard_user_id)
        .order_by(ExternalOutput.created_at.desc())
        .limit(cap)
    )
    if since is not None:
        stmt = stmt.where(ExternalOutput.created_at > since)
    if tag_filter:
        stmt = stmt.where(ExternalOutput.tags.overlap(list(tag_filter)))

    scal = await session.scalars(stmt)
    return list(scal.all())


__all__ = [
    "normalize_tag_filter",
    "parse_since_iso",
    "record_orchestrator_delivery",
    "list_external_results",
]
