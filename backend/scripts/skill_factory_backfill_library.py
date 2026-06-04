#!/usr/bin/env python3
"""Backfill tenant library — one skill row per completed factory opportunity."""

from __future__ import annotations

import asyncio
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import select

from app.application.services.skill_factory_publish import publish_verified_skill_forge
from app.core.database import async_session
from app.infrastructure.persistence.models.agent_suggestion import AgentSuggestion
from app.infrastructure.persistence.models.skill_opportunity import SkillOpportunityORM
from app.infrastructure.persistence.models.tenant import Tenant
from app.infrastructure.persistence.models.tenant_skill import TenantSkillORM


async def backfill_factory_library(*, tenant_id: uuid.UUID) -> dict[str, int]:
    """Re-publish approved forges so each completed opportunity gets its own skill row."""

    created = 0
    linked = 0
    skipped = 0
    errors = 0

    async with async_session() as session:
        tenant = await session.get(Tenant, tenant_id)
        if tenant is None:
            return {"created": 0, "linked": 0, "skipped": 0, "errors": 1}

        opportunities = list(
            (
                await session.scalars(
                    select(SkillOpportunityORM)
                    .where(
                        SkillOpportunityORM.tenant_id == tenant_id,
                        SkillOpportunityORM.status == "completed",
                        SkillOpportunityORM.supervisor_session_id.is_not(None),
                    )
                    .order_by(SkillOpportunityORM.created_at.asc()),
                )
            ).all(),
        )

        skill_ids_before = {
            row.id
            for row in (
                await session.scalars(
                    select(TenantSkillORM).where(TenantSkillORM.tenant_id == tenant_id),
                )
            ).all()
        }

        for opp in opportunities:
            if opp.supervisor_session_id is None:
                skipped += 1
                continue
            forge = await session.scalar(
                select(AgentSuggestion).where(
                    AgentSuggestion.tenant_id == tenant_id,
                    AgentSuggestion.supervisor_session_id == opp.supervisor_session_id,
                    AgentSuggestion.proposal_type == "verified_skill_forge",
                    AgentSuggestion.status == "approved",
                ),
            )
            if forge is None:
                skipped += 1
                continue

            prior_skill_id = opp.tenant_skill_id
            try:
                result = await publish_verified_skill_forge(
                    session,
                    suggestion=forge,
                    tenant_id=tenant_id,
                    tenant=tenant,
                    reviewer_subject="operator:skill_factory_backfill",
                )
            except Exception as exc:  # noqa: BLE001
                print(f"error opp={opp.id} {exc}")
                errors += 1
                continue

            if not result or not result.get("ok"):
                skipped += 1
                continue

            new_skill_id = uuid.UUID(str(result["tenant_skill_id"]))
            if new_skill_id not in skill_ids_before:
                created += 1
                skill_ids_before.add(new_skill_id)
            if opp.tenant_skill_id != prior_skill_id:
                linked += 1

        await session.commit()

    return {"created": created, "linked": linked, "skipped": skipped, "errors": errors}


async def _run() -> int:
    raw = sys.argv[1] if len(sys.argv) > 1 else "e098b808-8974-4bae-a6e1-de10bf6a2880"
    tenant_id = uuid.UUID(raw)
    stats = await backfill_factory_library(tenant_id=tenant_id)
    print(f"skill_factory_backfill_library {stats!s}")
    return 0 if stats["errors"] == 0 else 1


def main() -> None:
    raise SystemExit(asyncio.run(_run()))


if __name__ == "__main__":
    main()
