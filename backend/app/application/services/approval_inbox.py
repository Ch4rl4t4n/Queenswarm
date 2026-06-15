"""Unified Approval Inbox (BA4) — compose pending items from verified subsystems."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.business_operator import compose_revenue_summary
from app.application.services.marketing_product_catalog import build_catalog
from app.application.services.publish_queue import build_publish_queue_snapshot
from app.application.services.solo_operator_digest_inbox import compose_four_lane_digest_inbox
from app.application.services.supervisor.initiative import list_agent_suggestions
from app.core.config import settings
from app.infrastructure.persistence.models.tenant import Tenant

ApprovalInboxKind = Literal[
    "publish_queue",
    "agent_suggestion",
    "lane_digest",
    "innovation",
    "gumroad_manual",
    "goldmine_alert",
]


class ApprovalInboxItemOut(BaseModel):
    """One row in the unified operator approval inbox."""

    model_config = ConfigDict(extra="ignore")

    id: str
    kind: ApprovalInboxKind
    lane: str
    title: str
    detail: str
    created_at: datetime | None = None
    href: str
    source_id: str
    reject_supported: bool = True


class ApprovalInboxCountsOut(BaseModel):
    """Per-source pending counts."""

    model_config = ConfigDict(extra="ignore")

    publish_queue: int = 0
    agent_suggestions: int = 0
    lane_digests: int = 0
    innovation: int = 0
    gumroad_manual: int = 0
    goldmine_alerts: int = 0
    total: int = 0


class ApprovalInboxSnapshotOut(BaseModel):
    """Unified approval inbox for CBO panel."""

    model_config = ConfigDict(extra="ignore")

    enabled: bool = True
    generated_at: datetime
    counts: ApprovalInboxCountsOut = Field(default_factory=ApprovalInboxCountsOut)
    items: list[ApprovalInboxItemOut] = Field(default_factory=list)


def _proposal_label(proposal_type: str) -> str:
    mapping = {
        "verified_skill_forge": "Skill forge",
        "verified_content_pack_forge": "Content pack forge",
        "execution_studio_external": "External handoff",
        "codebase_proposal": "Codebase proposal",
    }
    return mapping.get(proposal_type, proposal_type.replace("_", " "))


async def compose_approval_inbox_snapshot(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    dashboard_user_id: uuid.UUID,
    tenant: Tenant | None,
    limit: int = 30,
) -> ApprovalInboxSnapshotOut:
    """Merge publish queue, suggestions, lane digests, and revenue manual steps."""

    if not settings.operator_control_plane_enabled:
        return ApprovalInboxSnapshotOut(
            enabled=False,
            generated_at=datetime.now(tz=UTC),
        )

    cap = max(1, min(limit, 50))
    items: list[ApprovalInboxItemOut] = []
    counts = ApprovalInboxCountsOut()

    if settings.publish_queue_enabled:
        queue = await build_publish_queue_snapshot(session, dashboard_user_id=dashboard_user_id)
        for row in queue.items:
            if row.status != "pending":
                continue
            counts.publish_queue += 1
            items.append(
                ApprovalInboxItemOut(
                    id=f"publish:{row.id}",
                    kind="publish_queue",
                    lane="marketing",
                    title=row.title,
                    detail=row.body_preview or f"{row.channel} publish pack — simulate-first.",
                    created_at=row.created_at,
                    href="/integrations?tab=studio&section=publish#publish-queue",
                    source_id=str(row.id),
                    reject_supported=True,
                ),
            )

    suggestion_rows = await list_agent_suggestions(
        session,
        tenant_id=tenant_id,
        status_filter="pending",
        limit=cap,
    )
    for row in suggestion_rows:
        counts.agent_suggestions += 1
        detail = str(row.description or row.title or row.proposal_type or "Agent suggestion").strip()
        items.append(
            ApprovalInboxItemOut(
                id=f"suggestion:{row.id}",
                kind="agent_suggestion",
                lane="ops",
                title=str(row.title or _proposal_label(str(row.proposal_type or "suggestion"))).strip(),
                detail=detail[:320],
                created_at=row.created_at,
                href="/agents#learning-loop",
                source_id=str(row.id),
                reject_supported=True,
            ),
        )

    digest = await compose_four_lane_digest_inbox(session, tenant_id=tenant_id, limit=cap)
    for row in digest.items:
        if row.task_id is not None:
            continue
        if not row.promote_ready:
            continue
        counts.lane_digests += 1
        items.append(
            ApprovalInboxItemOut(
                id=f"digest:{row.session_id}",
                kind="lane_digest",
                lane=row.lane_id,
                title=row.title,
                detail=row.excerpt[:320],
                created_at=row.created_at,
                href=row.session_href,
                source_id=row.session_id,
                reject_supported=False,
            ),
        )

    if settings.hive_innovation_lab_enabled:
        from app.application.services.hive_innovation_lab import count_pending_innovation_proposals

        innovation_pending = await count_pending_innovation_proposals(session, tenant_id=tenant_id)
        if innovation_pending > 0:
            counts.innovation = innovation_pending
            items.append(
                ApprovalInboxItemOut(
                    id="innovation:pending",
                    kind="innovation",
                    lane="ops",
                    title=f"{innovation_pending} innovation proposal(s)",
                    detail="Review in Innovation Lab — Queen Maintainer implements approved items via PR.",
                    created_at=None,
                    href="/agentic-os#innovation",
                    source_id="innovation",
                    reject_supported=False,
                ),
            )

    from app.application.services.forager_goldmine_dispatch_service import compose_goldmine_alert_inbox_items

    goldmine_rows = await compose_goldmine_alert_inbox_items(session, tenant_id=tenant_id, limit=cap)
    for row in goldmine_rows:
        counts.goldmine_alerts += 1
        new_count = int(row.get("new_item_count") or 0)
        forager_name = str(row.get("forager_name") or "Forager")
        source_type = str(row.get("source_type") or "")
        items.append(
            ApprovalInboxItemOut(
                id=f"goldmine:{row.get('forager_id')}",
                kind="goldmine_alert",
                lane="intel",
                title=f"Goldmine · {forager_name} · {new_count} new",
                detail=str(row.get("detail") or "New signals since last scheduled run."),
                created_at=None,
                href="/foragers",
                source_id=str(row.get("forager_id") or ""),
                reject_supported=False,
            ),
        )

    catalog = build_catalog()
    revenue = compose_revenue_summary()
    gumroad_linked = sum(1 for product in catalog.products if product.gumroad_url)
    if catalog.product_count > 0 and gumroad_linked == 0 and not revenue.missing_reports:
        counts.gumroad_manual = 1
        items.append(
            ApprovalInboxItemOut(
                id="gumroad:manual_upload",
                kind="gumroad_manual",
                lane="revenue",
                title="First Gumroad upload pending",
                detail=revenue.next_operator_action or "Upload from exports/gumroad-ready/UPLOAD_QUEUE.md",
                created_at=None,
                href="/factory",
                source_id="gumroad_manual",
                reject_supported=False,
            ),
        )

    items.sort(
        key=lambda row: (
            0 if row.kind in {"publish_queue", "gumroad_manual"} else 1,
            0 if row.kind == "goldmine_alert" else 1,
            -(row.created_at.timestamp() if row.created_at else 0),
        ),
    )
    counts.total = (
        counts.publish_queue
        + counts.agent_suggestions
        + counts.lane_digests
        + counts.innovation
        + counts.gumroad_manual
        + counts.goldmine_alerts
    )

    return ApprovalInboxSnapshotOut(
        enabled=True,
        generated_at=datetime.now(tz=UTC),
        counts=counts,
        items=items[:cap],
    )


__all__ = [
    "ApprovalInboxItemOut",
    "ApprovalInboxSnapshotOut",
    "compose_approval_inbox_snapshot",
]
