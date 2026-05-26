"""Context Teleport — verified cross-swarm context transfer (compose-only)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.cross_swarm_knowledge import compose_cross_swarm_knowledge_snapshot
from app.core.config import settings
from app.infrastructure.persistence.models.tenant import Tenant


class ContextTeleportPackOut(BaseModel):
    """One teleportable context pack between swarms."""

    model_config = ConfigDict(extra="ignore")

    pack_id: str
    source_domain: str
    target_domain: str
    recipe_name: str
    similarity: float
    excerpt: str
    hook_hint: str | None = None


class ContextTeleportSnapshotOut(BaseModel):
    """Snapshot for cockpit Context Teleport widget."""

    model_config = ConfigDict(extra="ignore")

    enabled: bool
    generated_at: datetime
    source_domain: str = "trading"
    target_domain: str = "marketing"
    packs: list[ContextTeleportPackOut] = Field(default_factory=list)
    recent_sessions: list[dict[str, str]] = Field(default_factory=list)


async def compose_context_teleport_snapshot(
    session: AsyncSession,
    *,
    tenant: Tenant | None,
    source_domain: str = "trading",
    target_domain: str = "marketing",
    limit: int = 5,
) -> ContextTeleportSnapshotOut:
    """Build teleport packs from cross-swarm recipe matches + recent verified sessions."""

    if not settings.cross_swarm_knowledge_enabled or not settings.operator_control_plane_enabled:
        return ContextTeleportSnapshotOut(
            enabled=False,
            generated_at=datetime.now(tz=UTC),
            source_domain=source_domain,
            target_domain=target_domain,
        )

    cross = await compose_cross_swarm_knowledge_snapshot(
        session,
        source_domain=source_domain,
        target_domain=target_domain,
        limit=limit,
    )

    packs: list[ContextTeleportPackOut] = []
    for idx, row in enumerate(cross.suggestions):
        packs.append(
            ContextTeleportPackOut(
                pack_id=f"tp-{source_domain}-{target_domain}-{idx}",
                source_domain=row.source_domain,
                target_domain=row.target_domain,
                recipe_name=row.name,
                similarity=row.similarity,
                excerpt=row.rationale[:400],
                hook_hint=f"Apply {row.name} learnings to {target_domain} lane.",
            ),
        )

    recent_sessions: list[dict[str, str]] = []
    if tenant is not None:
        from app.application.services.execution_studio_activity import list_execution_activity

        for event in list_execution_activity(tenant, limit=12):
            event_type = str(event.get("event_type") or "")
            if not event_type.startswith("publish_"):
                continue
            payload = dict(event.get("payload") or {})
            recent_sessions.append(
                {
                    "at": str(event.get("at") or ""),
                    "kind": event_type.removeprefix("publish_"),
                    "title": str(payload.get("title") or event.get("message") or "")[:120],
                    "channel": str(payload.get("channel") or ""),
                },
            )
            if len(recent_sessions) >= 4:
                break

    return ContextTeleportSnapshotOut(
        enabled=True,
        generated_at=datetime.now(tz=UTC),
        source_domain=source_domain,
        target_domain=target_domain,
        packs=packs,
        recent_sessions=recent_sessions,
    )


async def execute_context_teleport(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    tenant: Tenant | None,
    source_domain: str,
    target_domain: str,
    pack_id: str | None = None,
) -> dict[str, Any]:
    """Simulate-first teleport — returns injectable brief for target swarm (no live side effects)."""

    snap = await compose_context_teleport_snapshot(
        session,
        tenant=tenant,
        source_domain=source_domain,
        target_domain=target_domain,
    )
    if not snap.enabled or not snap.packs:
        return {"ok": False, "message": "No teleport packs available — add verified recipes first."}

    chosen = snap.packs[0]
    if pack_id:
        for pack in snap.packs:
            if pack.pack_id == pack_id:
                chosen = pack
                break

    brief_md = (
        f"# Context Teleport · {source_domain} → {target_domain}\n\n"
        f"**Recipe:** {chosen.recipe_name} (cosine {chosen.similarity:.0%})\n\n"
        f"{chosen.excerpt}\n\n"
        f"**Hook hint:** {chosen.hook_hint or 'n/a'}\n"
    )
    return {
        "ok": True,
        "pack_id": chosen.pack_id,
        "brief_md": brief_md,
        "trust_lane": "simulate",
        "href": f"/agents?teleport={chosen.pack_id}",
    }


__all__ = [
    "ContextTeleportPackOut",
    "ContextTeleportSnapshotOut",
    "compose_context_teleport_snapshot",
    "execute_context_teleport",
]
