"""Long-term memory evolution + swarm learning routines."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import asc, desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.chroma_client import HIVE_MIND_COLLECTION, embed_and_store
from app.core.neo4j_client import create_knowledge_node
from app.infrastructure.persistence.models.enums import TaskStatus
from app.infrastructure.persistence.models.knowledge import KnowledgeItem
from app.infrastructure.persistence.models.memory_evolution import MemoryEvolutionProposal
from app.infrastructure.persistence.models.supervisor_session import SupervisorSession
from app.infrastructure.persistence.models.task import Task


@dataclass(slots=True)
class MemoryEvolutionRunSummary:
    """Result payload for one evolution run."""

    tenant_id: uuid.UUID
    generated_lessons: int
    pending_approval: int
    auto_applied: int
    swarm_learning_entries: int
    history_consolidations: int


def _task_status_value(value: Any) -> str:
    if isinstance(value, TaskStatus):
        return value.value
    return str(value or "").strip().lower()


def _avg(values: list[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / float(len(values))


async def _persist_evolution_knowledge(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    source_type: str,
    title: str,
    summary: str,
    tags: list[str],
    confidence: float,
    payload: dict[str, Any],
) -> tuple[str | None, str | None]:
    """Persist one shared knowledge row and mirror into vector+graph stores."""

    content = f"{title}\n\n{summary}".strip()
    row = KnowledgeItem(
        tenant_id=tenant_id,
        source_type=source_type[:50],
        source_url=None,
        content_text=content[:12000],
        confidence_score=max(0.0, min(1.0, float(confidence))),
        topic_tags=tags[:32],
        decay_factor=1.0,
        scraped_at=datetime.now(tz=UTC),
        verified_at=datetime.now(tz=UTC),
    )
    db.add(row)
    await db.flush()

    vector_id: str | None = None
    graph_id: str | None = None
    try:
        vector_id = await embed_and_store(
            text=row.content_text,
            metadata={
                "kind": "memory_evolution",
                "tenant_id": str(tenant_id),
                "knowledge_item_id": str(row.id),
                "source_type": source_type,
                "tags": ",".join(tags[:24]),
                "payload": payload,
            },
            collection_name=HIVE_MIND_COLLECTION,
        )
    except Exception:
        vector_id = None
    try:
        graph_id = await create_knowledge_node(
            content=row.content_text[:4000],
            source=f"memory_evolution:{tenant_id}",
            confidence=row.confidence_score,
            topic_tags=tags[:24],
        )
    except Exception:
        graph_id = None
    row.embedding_id = vector_id
    row.neo4j_node_id = graph_id
    await db.flush()
    return vector_id, graph_id


async def _create_proposal(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    proposal_kind: str,
    title: str,
    summary: str,
    payload: dict[str, Any],
    importance_score: float,
    requires_manual_approval: bool,
    proposed_by_user_id: uuid.UUID | None,
) -> MemoryEvolutionProposal:
    row = MemoryEvolutionProposal(
        tenant_id=tenant_id,
        proposal_kind=proposal_kind[:48],
        title=title[:240],
        summary=summary[:2000],
        payload=dict(payload),
        status="pending" if requires_manual_approval else "approved",
        importance_score=max(0.0, min(1.0, float(importance_score))),
        requires_manual_approval=requires_manual_approval,
        proposed_by_user_id=proposed_by_user_id,
    )
    db.add(row)
    await db.flush()
    return row


async def _apply_proposal_content(db: AsyncSession, *, proposal: MemoryEvolutionProposal) -> None:
    if proposal.tenant_id is None:
        return
    payload = dict(proposal.payload or {})
    tags = [str(item) for item in list(payload.get("tags") or []) if str(item).strip()]
    await _persist_evolution_knowledge(
        db,
        tenant_id=proposal.tenant_id,
        source_type=str(payload.get("source_type") or "memory_evolution"),
        title=str(proposal.title),
        summary=str(proposal.summary),
        tags=tags or ["memory_evolution"],
        confidence=float(payload.get("confidence", 0.74)),
        payload=payload,
    )


async def approve_memory_evolution_proposal(
    db: AsyncSession,
    *,
    proposal: MemoryEvolutionProposal,
    approver_user_id: uuid.UUID,
) -> None:
    """Approve pending proposal and apply it to shared memory."""

    if proposal.status != "pending":
        return
    await _apply_proposal_content(db, proposal=proposal)
    proposal.status = "approved"
    proposal.approved_by_user_id = approver_user_id
    proposal.approved_at = datetime.now(tz=UTC)
    await db.flush()


async def reject_memory_evolution_proposal(
    db: AsyncSession,
    *,
    proposal: MemoryEvolutionProposal,
    approver_user_id: uuid.UUID,
) -> None:
    """Reject pending proposal without applying memory changes."""

    if proposal.status != "pending":
        return
    proposal.status = "rejected"
    proposal.approved_by_user_id = approver_user_id
    proposal.approved_at = datetime.now(tz=UTC)
    await db.flush()


async def list_memory_evolution_proposals(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    status_filter: str | None = None,
    limit: int = 60,
) -> list[MemoryEvolutionProposal]:
    stmt = select(MemoryEvolutionProposal).where(MemoryEvolutionProposal.tenant_id == tenant_id)
    if status_filter:
        stmt = stmt.where(MemoryEvolutionProposal.status == status_filter.strip().lower())
    stmt = stmt.order_by(desc(MemoryEvolutionProposal.created_at)).limit(max(1, min(limit, 200)))
    return list((await db.scalars(stmt)).all())


async def run_memory_evolution_for_tenant(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    proposed_by_user_id: uuid.UUID | None,
    approval_threshold: float = 0.82,
    lookback_days: int = 30,
) -> MemoryEvolutionRunSummary:
    """Build lessons learned and swarm-level evolution entries from long-term history."""

    since = datetime.now(tz=UTC) - timedelta(days=max(7, lookback_days))
    tasks = list(
        (
            await db.scalars(
                select(Task)
                .where(Task.tenant_id == tenant_id, Task.created_at >= since)
                .order_by(desc(Task.created_at))
                .limit(300),
            )
        ).all(),
    )
    sessions = list(
        (
            await db.scalars(
                select(SupervisorSession)
                .where(SupervisorSession.tenant_id == tenant_id, SupervisorSession.created_at >= since)
                .options(selectinload(SupervisorSession.sub_agents))
                .order_by(desc(SupervisorSession.created_at))
                .limit(260),
            )
        ).all(),
    )
    old_knowledge = list(
        (
            await db.scalars(
                select(KnowledgeItem)
                .where(
                    KnowledgeItem.tenant_id == tenant_id,
                    KnowledgeItem.scraped_at < datetime.now(tz=UTC) - timedelta(days=21),
                )
                .order_by(asc(KnowledgeItem.scraped_at))
                .limit(220),
            )
        ).all(),
    )

    auto_applied = 0
    pending = 0
    generated = 0
    swarm_entries = 0
    history_consolidations = 0

    completed = [row for row in tasks if _task_status_value(row.status) == "completed"]
    failed = [row for row in tasks if _task_status_value(row.status) == "failed"]
    if tasks:
        completion_rate = len(completed) / float(len(tasks))
        failure_rate = len(failed) / float(len(tasks))
        lesson_summary = (
            f"Task execution trend (last {lookback_days}d): completion={completion_rate:.2%}, "
            f"failure={failure_rate:.2%}, total={len(tasks)}."
        )
        lesson_payload = {
            "source_type": "swarm_lessons_learned",
            "tags": [
                "swarm_learning",
                "lessons_learned",
                "task_history",
                "meta_reasoning",
            ],
            "confidence": max(0.55, completion_rate),
            "completion_rate": completion_rate,
            "failure_rate": failure_rate,
            "sample_success_titles": [row.title[:120] for row in completed[:6]],
            "sample_failure_titles": [row.title[:120] for row in failed[:6]],
        }
        importance = max(0.45, failure_rate + 0.35)
        requires_approval = importance >= approval_threshold
        proposal = await _create_proposal(
            db,
            tenant_id=tenant_id,
            proposal_kind="lessons_learned",
            title="Long-term lessons learned from swarm task history",
            summary=lesson_summary,
            payload=lesson_payload,
            importance_score=importance,
            requires_manual_approval=requires_approval,
            proposed_by_user_id=proposed_by_user_id,
        )
        generated += 1
        if requires_approval:
            pending += 1
        else:
            await _apply_proposal_content(db, proposal=proposal)
            proposal.approved_at = datetime.now(tz=UTC)
            proposal.approved_by_user_id = proposed_by_user_id
            auto_applied += 1

    if sessions:
        strategy_scores: list[float] = []
        shifts: dict[str, int] = {}
        by_swarm: dict[str, dict[str, Any]] = {}
        for sess in sessions:
            swarm_key = str(sess.swarm_id) if sess.swarm_id else "global"
            bucket = by_swarm.setdefault(
                swarm_key,
                {"sessions": 0, "scores": [], "shifts": {}, "skill_manifest_hits": 0},
            )
            bucket["sessions"] = int(bucket["sessions"]) + 1
            for sub in list(sess.sub_agents or []):
                memory = dict(sub.short_memory or {})
                meta = memory.get("meta_reasoning") if isinstance(memory.get("meta_reasoning"), dict) else {}
                score = meta.get("strategy_score")
                if isinstance(score, (int, float)):
                    strategy_scores.append(float(score))
                    bucket["scores"].append(float(score))
                shift = str(meta.get("recommended_shift") or "").strip()
                if shift:
                    shifts[shift] = shifts.get(shift, 0) + 1
                    bucket_shifts = bucket["shifts"]
                    bucket_shifts[shift] = int(bucket_shifts.get(shift, 0)) + 1
                manifest = memory.get("skill_manifest")
                if isinstance(manifest, list) and manifest:
                    bucket["skill_manifest_hits"] = int(bucket["skill_manifest_hits"]) + 1
        global_summary = (
            f"Swarm learning snapshot: sessions={len(sessions)}, avg_strategy_score={_avg(strategy_scores):.3f}, "
            f"top_shift={max(shifts, key=shifts.get) if shifts else 'maintain_strategy'}."
        )
        global_payload = {
            "source_type": "swarm_learning_snapshot",
            "tags": ["swarm_learning", "meta_reasoning", "advanced_skills", "shared_knowledge_base"],
            "confidence": max(0.55, _avg(strategy_scores) if strategy_scores else 0.6),
            "shift_distribution": shifts,
            "swarm_buckets": by_swarm,
        }
        global_importance = min(0.98, 0.55 + (1.0 - _avg(strategy_scores)))
        global_requires = global_importance >= approval_threshold
        proposal = await _create_proposal(
            db,
            tenant_id=tenant_id,
            proposal_kind="swarm_learning",
            title="Swarm-level learning snapshot from supervisor session history",
            summary=global_summary,
            payload=global_payload,
            importance_score=global_importance,
            requires_manual_approval=global_requires,
            proposed_by_user_id=proposed_by_user_id,
        )
        generated += 1
        swarm_entries += 1
        if global_requires:
            pending += 1
        else:
            await _apply_proposal_content(db, proposal=proposal)
            proposal.approved_at = datetime.now(tz=UTC)
            proposal.approved_by_user_id = proposed_by_user_id
            auto_applied += 1

    if old_knowledge:
        tag_counter: dict[str, int] = {}
        for row in old_knowledge:
            for tag in list(row.topic_tags or []):
                key = str(tag).strip().lower()
                if not key:
                    continue
                tag_counter[key] = tag_counter.get(key, 0) + 1
        top_tags = sorted(tag_counter.items(), key=lambda item: (-item[1], item[0]))[:8]
        consolidation_summary = (
            f"Consolidated {len(old_knowledge)} older HiveMind entries into one compact memory checkpoint. "
            f"Top tags: {', '.join(tag for tag, _count in top_tags) or 'none'}."
        )
        consolidation_payload = {
            "source_type": "memory_consolidation",
            "tags": ["memory_evolution", "hivemind_consolidation", "long_term_memory"],
            "confidence": 0.72,
            "oldest_item_at": min(row.scraped_at for row in old_knowledge).isoformat(),
            "newest_item_at": max(row.scraped_at for row in old_knowledge).isoformat(),
            "top_tags": top_tags,
            "item_count": len(old_knowledge),
        }
        consolidation_importance = 0.58
        proposal = await _create_proposal(
            db,
            tenant_id=tenant_id,
            proposal_kind="history_consolidation",
            title="HiveMind long-term history consolidation checkpoint",
            summary=consolidation_summary,
            payload=consolidation_payload,
            importance_score=consolidation_importance,
            requires_manual_approval=False,
            proposed_by_user_id=proposed_by_user_id,
        )
        generated += 1
        history_consolidations += 1
        await _apply_proposal_content(db, proposal=proposal)
        proposal.approved_at = datetime.now(tz=UTC)
        proposal.approved_by_user_id = proposed_by_user_id
        auto_applied += 1

    await db.flush()
    return MemoryEvolutionRunSummary(
        tenant_id=tenant_id,
        generated_lessons=generated,
        pending_approval=pending,
        auto_applied=auto_applied,
        swarm_learning_entries=swarm_entries,
        history_consolidations=history_consolidations,
    )


__all__ = [
    "MemoryEvolutionRunSummary",
    "approve_memory_evolution_proposal",
    "list_memory_evolution_proposals",
    "reject_memory_evolution_proposal",
    "run_memory_evolution_for_tenant",
]
