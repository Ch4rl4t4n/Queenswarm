#!/usr/bin/env python3
"""Unblock factory builds — enable auto-approve, approve sessions, approve forge proposals."""

from __future__ import annotations

import asyncio
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import select

from app.application.services.content_pack_factory_forge import is_content_pack_factory_session
from app.application.services.content_pack_factory_service import compose_content_pack_factory_snapshot
from app.application.services.skill_factory_forge import is_skill_factory_session
from app.application.services.supervisor.initiative import bulk_review_agent_suggestions
from app.application.services.supervisor.session_service import apply_session_review, get_supervisor_session
from app.application.services.supervisor_session_control import (
    merge_supervisor_sessions_patch,
)
from app.core.database import async_session
from app.infrastructure.persistence.models.agent_suggestion import AgentSuggestion
from app.infrastructure.persistence.models.supervisor_session import SupervisorSession
from app.infrastructure.persistence.models.tenant import Tenant

_OPERATOR = "operator:factory-unblock-builds"
_FACTORY_FORGE_TYPES = ("verified_content_pack_forge", "verified_skill_forge")


async def _enable_tenant_auto_approve(session, tenant: Tenant) -> bool:
    bucket = dict(tenant.operator_settings or {})
    sessions = dict(bucket.get("supervisor_sessions") or {})
    if sessions.get("auto_approve_enabled"):
        return False
    tenant.operator_settings = merge_supervisor_sessions_patch(bucket, {"auto_approve_enabled": True})
    await session.flush()
    return True


async def _approve_factory_sessions(session, *, tenant_id: uuid.UUID) -> list[str]:
    rows = list(
        (
            await session.scalars(
                select(SupervisorSession).where(
                    SupervisorSession.tenant_id == tenant_id,
                    SupervisorSession.status == "needs_input",
                ),
            )
        ).all(),
    )
    approved: list[str] = []
    for row in rows:
        if not is_content_pack_factory_session(row) and not is_skill_factory_session(row):
            continue
        hydrated = await get_supervisor_session(session, row.id)
        if hydrated is None:
            continue
        await apply_session_review(
            session,
            session_row=hydrated,
            decision="approve",
            note="factory_unblock_builds",
        )
        approved.append(str(row.id))
    return approved


async def _approve_factory_forges(session, *, tenant_id: uuid.UUID) -> dict[str, int]:
    total = 0
    errors: list[str] = []
    for proposal_type in _FACTORY_FORGE_TYPES:
        pending = list(
            (
                await session.scalars(
                    select(AgentSuggestion).where(
                        AgentSuggestion.tenant_id == tenant_id,
                        AgentSuggestion.status == "pending",
                        AgentSuggestion.proposal_type == proposal_type,
                    ),
                )
            ).all(),
        )
        if not pending:
            continue
        result = await bulk_review_agent_suggestions(
            session,
            tenant_id=tenant_id,
            decision="approved",
            reviewer_subject=_OPERATOR,
            suggestion_ids=[row.id for row in pending],
            include_high_risk=False,
            limit=20,
        )
        total += int(result.get("processed", 0))
        errors.extend(str(e) for e in list(result.get("errors") or [])[:5])
    return {"processed": total, "errors": errors}


async def _reject_spurious_skill_forges(session, *, tenant_id: uuid.UUID) -> int:
    """Reject skill forges accidentally created on content-pack factory sessions."""

    from app.application.services.content_pack_factory_forge import is_content_pack_factory_session

    rows = list(
        (
            await session.scalars(
                select(AgentSuggestion).where(
                    AgentSuggestion.tenant_id == tenant_id,
                    AgentSuggestion.proposal_type == "verified_skill_forge",
                    AgentSuggestion.status == "pending",
                ),
            )
        ).all(),
    )
    rejected = 0
    for row in rows:
        if row.supervisor_session_id is None:
            continue
        sup = await session.get(SupervisorSession, row.supervisor_session_id)
        if sup is None or not is_content_pack_factory_session(sup):
            continue
        from app.application.services.supervisor.initiative import review_agent_suggestion_with_handoff

        await review_agent_suggestion_with_handoff(
            session,
            suggestion=row,
            decision="rejected",
            reviewer_subject=_OPERATOR,
            supervisor_session=sup,
            tenant=await session.get(Tenant, tenant_id),
        )
        rejected += 1
    return rejected


async def _run(*, tenant_id: uuid.UUID | None) -> int:
    async with async_session() as session:
        if tenant_id is None:
            tenant = await session.scalar(select(Tenant).order_by(Tenant.created_at.asc()).limit(1))
        else:
            tenant = await session.get(Tenant, tenant_id)
        if tenant is None:
            print("No tenant.")
            return 1

        enabled = await _enable_tenant_auto_approve(session, tenant)
        rejected = await _reject_spurious_skill_forges(session, tenant_id=tenant.id)
        approved_sessions = await _approve_factory_sessions(session, tenant_id=tenant.id)
        forge_result = await _approve_factory_forges(session, tenant_id=tenant.id)
        await session.commit()

        snapshot = await compose_content_pack_factory_snapshot(session, tenant_id=tenant.id)

        print("== Factory unblock builds ==")
        print(f"tenant_id={tenant.id}")
        print(f"auto_approve_enabled_now={enabled or resolve_auto(tenant)}")
        print(f"spurious_skill_forges_rejected={rejected}")
        print(f"sessions_approved={len(approved_sessions)} ids={approved_sessions}")
        print(f"forge_approved={forge_result['processed']} errors={forge_result['errors']}")
        print(
            f"content_pack_queue={snapshot.queue_count} building={snapshot.building_count} "
            f"library={len(snapshot.library)}",
        )
        print("\nNote: durable sessions continue via Celery worker after approve.")
        return 0


def resolve_auto(tenant: Tenant) -> bool:
    from app.application.services.supervisor_session_control import resolve_supervisor_sessions_auto_approve

    return resolve_supervisor_sessions_auto_approve(tenant)


def main() -> None:
    raw = sys.argv[1] if len(sys.argv) > 1 else ""
    tid = uuid.UUID(raw) if raw else None
    raise SystemExit(asyncio.run(_run(tenant_id=tid)))


if __name__ == "__main__":
    main()
