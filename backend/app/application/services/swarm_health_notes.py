"""Per-swarm health-note service — operator visibility for under-performance signals.

Health notes are stored in ``SubSwarm.local_memory['health_notes']`` (capped at
the most recent ``NOTES_KEEP`` entries). The top-of-stack timestamp is exposed
as ``last_complaint_at`` in dashboard payloads so operators see a red dot on
swarms with recent issues.

This is a *signal* surface, not a control surface — Queen and managers can
emit advisory notes; operators decide whether to act.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any, Literal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.infrastructure.persistence.models.swarm import SubSwarm

NOTES_KEEP = 10

Severity = Literal["info", "warn", "error"]


async def add_health_note(
    session: AsyncSession,
    *,
    swarm_id: uuid.UUID,
    message: str,
    severity: Severity = "warn",
    source: str = "operator",
    manager_agent_id: uuid.UUID | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Append a health note to a sub-swarm's local memory; return the stored note."""

    swarm = await session.get(SubSwarm, swarm_id)
    if swarm is None:
        msg = f"SubSwarm {swarm_id} not found"
        raise ValueError(msg)

    cleaned = (message or "").strip()
    if not cleaned:
        msg = "Health note message must be non-empty"
        raise ValueError(msg)
    if severity not in ("info", "warn", "error"):
        msg = f"Invalid severity {severity!r}"
        raise ValueError(msg)

    memory = dict(swarm.local_memory or {})
    notes_block = dict(memory.get("health_notes") or {})
    items = list(notes_block.get("items") or [])

    entry = {
        "id": str(uuid.uuid4()),
        "at": datetime.now(tz=UTC).isoformat(),
        "severity": severity,
        "source": source,
        "message": cleaned[:500],
        "manager_agent_id": str(manager_agent_id) if manager_agent_id else None,
        "metadata": dict(metadata) if metadata else {},
    }
    items.insert(0, entry)
    items = items[:NOTES_KEEP]

    notes_block["items"] = items
    notes_block["last_at"] = entry["at"]
    notes_block["last_severity"] = severity
    notes_block["last_message"] = entry["message"]
    memory["health_notes"] = notes_block
    swarm.local_memory = memory
    flag_modified(swarm, "local_memory")
    await session.flush()
    return entry


async def list_health_notes(
    session: AsyncSession,
    *,
    swarm_id: uuid.UUID,
    limit: int = NOTES_KEEP,
) -> list[dict[str, Any]]:
    """Return the most recent health notes for one swarm (newest first)."""

    swarm = await session.get(SubSwarm, swarm_id)
    if swarm is None:
        return []
    memory = dict(swarm.local_memory or {})
    items = list((memory.get("health_notes") or {}).get("items") or [])
    return items[: max(1, min(limit, NOTES_KEEP))]


async def acknowledge_health_notes(
    session: AsyncSession,
    *,
    swarm_id: uuid.UUID,
    note_id: str | None = None,
) -> int:
    """Remove one note (by id) or clear all; return remaining count."""

    swarm = await session.get(SubSwarm, swarm_id)
    if swarm is None:
        return 0
    memory = dict(swarm.local_memory or {})
    notes_block = dict(memory.get("health_notes") or {})
    items = list(notes_block.get("items") or [])
    if note_id is None:
        items = []
    else:
        items = [n for n in items if n.get("id") != note_id]
    notes_block["items"] = items
    if items:
        head = items[0]
        notes_block["last_at"] = head.get("at")
        notes_block["last_severity"] = head.get("severity")
        notes_block["last_message"] = head.get("message")
    else:
        notes_block.pop("last_at", None)
        notes_block.pop("last_severity", None)
        notes_block.pop("last_message", None)
    memory["health_notes"] = notes_block
    swarm.local_memory = memory
    flag_modified(swarm, "local_memory")
    await session.flush()
    return len(items)


def summarize_health_notes(swarm: SubSwarm) -> dict[str, Any] | None:
    """Return ``{last_at, last_severity, last_message, open_count}`` or ``None``."""

    memory = swarm.local_memory or {}
    block = memory.get("health_notes") if isinstance(memory, dict) else None
    if not block:
        return None
    items = block.get("items") or []
    if not items:
        return None
    head = items[0]
    return {
        "last_at": head.get("at"),
        "last_severity": head.get("severity") or "warn",
        "last_message": head.get("message") or "",
        "open_count": len(items),
    }


async def bulk_summary(session: AsyncSession) -> dict[uuid.UUID, dict[str, Any]]:
    """Return ``{swarm_id: summary}`` for every swarm with notes (single query)."""

    rows = (await session.execute(select(SubSwarm))).scalars().all()
    out: dict[uuid.UUID, dict[str, Any]] = {}
    for row in rows:
        summary = summarize_health_notes(row)
        if summary is not None:
            out[row.id] = summary
    return out


__all__ = [
    "NOTES_KEEP",
    "Severity",
    "acknowledge_health_notes",
    "add_health_note",
    "bulk_summary",
    "list_health_notes",
    "summarize_health_notes",
]
