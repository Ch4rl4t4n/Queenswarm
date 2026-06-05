"""Skill Factory queue drain — auto-approve, auto-rebuild, and prioritized build slots."""

from __future__ import annotations

import uuid
from typing import Any

import structlog
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.skill_factory_service import (
    SkillFactoryPolicyOut,
    _forge_payload_fields,
    _forge_suggestions_by_session,
    list_skill_opportunities,
    rebuild_factory_opportunity,
)
from app.infrastructure.persistence.models.agent_suggestion import AgentSuggestion
from app.infrastructure.persistence.models.skill_opportunity import SkillOpportunityORM

logger = structlog.get_logger(__name__)


class SkillFactoryQueueDrainOut(BaseModel):
    """Outcome counters for one drain pass."""

    model_config = ConfigDict(extra="ignore")

    approved: int = 0
    rebuilt: int = 0
    started: int = 0
    skipped_cap: int = 0
    building_slots_used: int = 0
    errors: list[str] = Field(default_factory=list)


def _forge_needs_rebuild(*, quality_passed: bool | None, critic_approved: bool | None) -> bool:
    return quality_passed is False or critic_approved is False


def _forge_ready_to_approve(*, quality_passed: bool | None, critic_approved: bool | None) -> bool:
    return quality_passed is not False and critic_approved is not False


async def _count_building(session: AsyncSession, *, tenant_id: uuid.UUID) -> int:
    return int(
        await session.scalar(
            select(func.count())
            .select_from(SkillOpportunityORM)
            .where(
                SkillOpportunityORM.tenant_id == tenant_id,
                SkillOpportunityORM.status == "building",
            ),
        )
        or 0,
    )


async def _approve_passing_forge(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    forge: AgentSuggestion,
    reviewer_subject: str,
) -> bool:
    """Approve one quality-passed forge and publish to Library."""

    from app.application.services.skill_factory_publish import publish_verified_skill_forge
    from app.application.services.supervisor.initiative import review_agent_suggestion_with_handoff
    from app.infrastructure.persistence.models.supervisor_session import SupervisorSession
    from app.infrastructure.persistence.models.tenant import Tenant

    if str(forge.status or "").strip().lower() != "pending":
        return False
    quality_passed, critic_approved, _ = _forge_payload_fields(forge)
    if not _forge_ready_to_approve(quality_passed=quality_passed, critic_approved=critic_approved):
        return False

    supervisor = None
    if forge.supervisor_session_id is not None:
        supervisor = await session.get(SupervisorSession, forge.supervisor_session_id)
    tenant = await session.get(Tenant, tenant_id)
    reviewed, _handoff = await review_agent_suggestion_with_handoff(
        session,
        suggestion=forge,
        decision="approved",
        reviewer_subject=reviewer_subject,
        supervisor_session=supervisor,
        tenant=tenant,
    )
    if str(reviewed.status or "").strip().lower() != "approved":
        return False
    result = await publish_verified_skill_forge(
        session,
        suggestion=reviewed,
        tenant_id=tenant_id,
        tenant=tenant,
        reviewer_subject=reviewer_subject,
    )
    return bool(result and result.get("ok"))

async def drain_skill_factory_queue(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    policy: SkillFactoryPolicyOut,
    reviewer_subject: str = "celery:skill_factory_drain",
    created_by_subject: str = "celery:skill_factory_drain",
) -> SkillFactoryQueueDrainOut:
    """Move the factory queue forward with score-based prioritization.

    Order per tick (highest ``composite_score`` first):
    1. Auto-approve passing forges → Library
    2. Auto-rebuild failed quality/critic forges
    3. Auto-rebuild ``failed`` opportunities
    4. Start ``queued`` builds while under ``max_concurrent_builds``
    """

    out = SkillFactoryQueueDrainOut()
    if not policy.enabled or not policy.auto_queue_drain_enabled:
        return out

    building = await _count_building(session, tenant_id=tenant_id)
    slots = max(0, policy.max_concurrent_builds - building)
    out.building_slots_used = building
    batch = max(1, min(policy.drain_batch_per_tick, 10))
    budget = batch

    opportunities = await list_skill_opportunities(session, tenant_id=tenant_id, limit=120)
    actionable = [
        row
        for row in opportunities
        if row.status in {"awaiting_forge", "failed", "queued"}
    ]
    actionable.sort(key=lambda row: float(row.composite_score or 0.0), reverse=True)

    session_ids = [row.supervisor_session_id for row in actionable if row.supervisor_session_id]
    forge_by_session = await _forge_suggestions_by_session(
        session,
        tenant_id=tenant_id,
        session_ids=[sid for sid in session_ids if sid is not None],
    )

    if policy.auto_approve_passing_forges and budget > 0:
        for row in actionable:
            if budget <= 0:
                break
            if row.status != "awaiting_forge" or row.supervisor_session_id is None:
                continue
            forge = forge_by_session.get(row.supervisor_session_id)
            if forge is None:
                continue
            try:
                if await _approve_passing_forge(
                    session,
                    tenant_id=tenant_id,
                    forge=forge,
                    reviewer_subject=reviewer_subject,
                ):
                    out.approved += 1
                    budget -= 1
            except Exception as exc:
                out.errors.append(f"approve:{row.id}:{str(exc)[:80]}")
                logger.warning(
                    "skill_factory.drain_approve_failed",
                    agent_id="skill_factory",
                    swarm_id=str(tenant_id),
                    task_id=str(row.id),
                    error=str(exc)[:200],
                )

    if policy.auto_rebuild_failed_forges and budget > 0:
        for row in actionable:
            if budget <= 0:
                break
            if row.status == "awaiting_forge" and row.supervisor_session_id is not None:
                forge = forge_by_session.get(row.supervisor_session_id)
                if forge is None or str(forge.status or "").strip().lower() != "pending":
                    continue
                quality_passed, critic_approved, _ = _forge_payload_fields(forge)
                if not _forge_needs_rebuild(quality_passed=quality_passed, critic_approved=critic_approved):
                    continue
            elif row.status != "failed":
                continue
            try:
                rebuilt = await rebuild_factory_opportunity(
                    session,
                    tenant_id=tenant_id,
                    opportunity_id=row.id,
                    created_by_subject=created_by_subject,
                    reviewer_subject=reviewer_subject,
                )
                if rebuilt.status == "building":
                    out.rebuilt += 1
                    budget -= 1
                    building += 1
                    slots = max(0, policy.max_concurrent_builds - building)
            except ValueError as exc:
                code = str(exc)
                if code == "weekly_build_cap_reached":
                    out.skipped_cap += 1
                    break
                out.errors.append(f"rebuild:{row.id}:{code[:80]}")
            except Exception as exc:
                out.errors.append(f"rebuild:{row.id}:{str(exc)[:80]}")

    if policy.auto_build_enabled and slots > 0 and budget > 0:
        from app.application.services.skill_factory_research import _weekly_build_count
        from app.application.services.skill_factory_service import start_factory_build

        recent = await _weekly_build_count(session, tenant_id=tenant_id)
        if recent >= policy.max_builds_per_week:
            out.skipped_cap += 1
        else:
            for row in actionable:
                if slots <= 0 or budget <= 0:
                    break
                if row.status != "queued":
                    continue
                if float(row.composite_score or 0.0) < policy.auto_build_min_score:
                    continue
                try:
                    built = await start_factory_build(
                        session,
                        tenant_id=tenant_id,
                        opportunity_id=row.id,
                        created_by_subject=created_by_subject,
                    )
                    if built.status == "building":
                        out.started += 1
                        slots -= 1
                        budget -= 1
                except ValueError as exc:
                    code = str(exc)
                    if code == "weekly_build_cap_reached":
                        out.skipped_cap += 1
                        break
                    out.errors.append(f"start:{row.id}:{code[:80]}")

    if out.approved or out.rebuilt or out.started:
        logger.info(
            "skill_factory.queue_drained",
            agent_id="skill_factory",
            swarm_id=str(tenant_id),
            task_id="drain",
            approved=out.approved,
            rebuilt=out.rebuilt,
            started=out.started,
            building=building,
        )
    return out


__all__ = ["SkillFactoryQueueDrainOut", "drain_skill_factory_queue"]
