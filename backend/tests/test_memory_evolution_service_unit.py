"""Unit tests for long-term memory evolution service."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any

import pytest

from app.application.services.supervisor.memory_evolution import (
    approve_memory_evolution_proposal,
    reject_memory_evolution_proposal,
    run_memory_evolution_for_tenant,
)
from app.infrastructure.persistence.models.enums import TaskStatus
from app.infrastructure.persistence.models.memory_evolution import MemoryEvolutionProposal


class _ScalarResult:
    def __init__(self, rows: list[Any]) -> None:
        self._rows = rows

    def all(self) -> list[Any]:
        return self._rows


class _FakeDb:
    def __init__(
        self,
        *,
        tasks: list[Any],
        sessions: list[Any],
        knowledge_rows: list[Any],
    ) -> None:
        self._tasks = tasks
        self._sessions = sessions
        self._knowledge_rows = knowledge_rows
        self.added: list[Any] = []

    def add(self, row: Any) -> None:
        self.added.append(row)

    async def flush(self) -> None:
        return None

    async def scalars(self, stmt):  # noqa: ANN001
        rendered = str(stmt)
        if "FROM tasks" in rendered:
            return _ScalarResult(self._tasks)
        if "FROM supervisor_sessions" in rendered:
            return _ScalarResult(self._sessions)
        if "FROM knowledge_items" in rendered:
            return _ScalarResult(self._knowledge_rows)
        if "FROM memory_evolution_proposals" in rendered:
            proposals = [
                row for row in self.added if isinstance(row, MemoryEvolutionProposal)
            ]
            return _ScalarResult(proposals)
        return _ScalarResult([])


@pytest.mark.asyncio
async def test_run_memory_evolution_for_tenant_when_high_importance_then_creates_pending(monkeypatch) -> None:
    """High-risk learning updates remain pending for manual approval."""

    tenant_id = uuid.uuid4()
    tasks = [
        SimpleNamespace(title="task-good", status=TaskStatus.COMPLETED, created_at=datetime.now(tz=UTC)),
        SimpleNamespace(title="task-bad", status=TaskStatus.FAILED, created_at=datetime.now(tz=UTC)),
    ]
    session = SimpleNamespace(
        swarm_id=None,
        created_at=datetime.now(tz=UTC),
        sub_agents=[
            SimpleNamespace(short_memory={"meta_reasoning": {"strategy_score": 0.12, "recommended_shift": "fallback"}}),
        ],
    )
    old_knowledge = [
        SimpleNamespace(topic_tags=["alpha", "beta"], scraped_at=datetime.now(tz=UTC)),
    ]
    db = _FakeDb(tasks=tasks, sessions=[session], knowledge_rows=old_knowledge)

    async def _noop_apply(*args, **kwargs):  # noqa: ANN002, ANN003
        return None

    monkeypatch.setattr(
        "app.application.services.supervisor.memory_evolution._apply_proposal_content",
        _noop_apply,
    )

    out = await run_memory_evolution_for_tenant(
        db,  # type: ignore[arg-type]
        tenant_id=tenant_id,
        proposed_by_user_id=None,
        approval_threshold=0.7,
    )
    assert out.generated_lessons >= 3
    assert out.pending_approval >= 1


@pytest.mark.asyncio
async def test_approve_and_reject_memory_proposals_update_status(monkeypatch) -> None:
    """Approval applies memory changes; rejection stores governance decision only."""

    db = SimpleNamespace(flush=lambda: None)

    async def _flush() -> None:
        return None

    db.flush = _flush

    applied: list[str] = []

    async def _record_apply(_db, *, proposal, **_kwargs):  # noqa: ANN001
        applied.append(str(proposal.id))

    monkeypatch.setattr(
        "app.application.services.supervisor.memory_evolution._apply_proposal_content",
        _record_apply,
    )

    pending = MemoryEvolutionProposal(
        tenant_id=uuid.uuid4(),
        proposal_kind="swarm_learning",
        title="Need review",
        summary="pending",
        payload={"source_type": "swarm_learning_snapshot", "tags": ["swarm_learning"]},
        status="pending",
        importance_score=0.9,
        requires_manual_approval=True,
    )
    approver_id = uuid.uuid4()
    await approve_memory_evolution_proposal(db, proposal=pending, approver_user_id=approver_id)
    assert pending.status == "approved"
    assert pending.approved_by_user_id == approver_id
    assert pending.approved_at is not None
    assert applied == [str(pending.id)]

    pending2 = MemoryEvolutionProposal(
        tenant_id=uuid.uuid4(),
        proposal_kind="lessons_learned",
        title="Reject me",
        summary="pending",
        payload={"source_type": "swarm_lessons_learned", "tags": ["lessons_learned"]},
        status="pending",
        importance_score=0.92,
        requires_manual_approval=True,
    )
    await reject_memory_evolution_proposal(db, proposal=pending2, approver_user_id=approver_id)
    assert pending2.status == "rejected"
    assert pending2.approved_by_user_id == approver_id
    assert pending2.approved_at is not None
