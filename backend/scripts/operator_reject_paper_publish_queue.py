#!/usr/bin/env python3
"""Reject pending publish packs generated from paper trading (one-shot cleanup)."""

from __future__ import annotations

import asyncio
import re
import uuid

from app.application.services.publish_queue import (
    bulk_review_publish_queue,
    classify_publish_queue_status,
    _structured_body,
)
from app.domain.outputs.service import list_owned_deliverables
from app.core.database import async_session
from app.infrastructure.persistence.models.tenant import DashboardUserTenantMembership
from sqlalchemy import select

PAPER_PATTERN = re.compile(
    r"paper\s*(trade|mode)|btc|eth|sol|momentum|notional|educational content only",
    re.IGNORECASE,
)


async def main() -> int:
    rejected = 0
    async with async_session() as session:
        membership = (
            await session.scalars(
                select(DashboardUserTenantMembership)
                .where(DashboardUserTenantMembership.role.in_(("owner", "admin")))
                .order_by(DashboardUserTenantMembership.created_at.asc())
                .limit(1),
            )
        ).first()
        if membership is None:
            print("rejected_paper_publish_packs=0 (no owner membership)")
            return 0

        rows = await list_owned_deliverables(
            session,
            dashboard_user_id=membership.dashboard_user_id,
            limit=200,
            ready_to_publish=True,
        )
        ids: list[uuid.UUID] = []
        for row in rows:
            if classify_publish_queue_status(row) != "pending":
                continue
            blob = f"{row.title or ''} {_structured_body(row)}"
            if PAPER_PATTERN.search(blob):
                ids.append(row.id)
        if ids:
            result = await bulk_review_publish_queue(
                session,
                deliverable_ids=ids,
                dashboard_user_id=membership.dashboard_user_id,
                decision="reject",
                note="Paper trading removed — auto-rejected legacy pack.",
                reviewed_by="operator:reject-paper-cleanup",
            )
            rejected = result.updated
        await session.commit()
    print(f"rejected_paper_publish_packs={rejected}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
