"""Unit tests for agent initiative and self-proposed improvements."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any

import pytest

from app.application.services.supervisor.initiative import (
    list_agent_suggestions,
    propose_agent_improvements,
    review_agent_suggestion,
)
from app.infrastructure.persistence.models.agent_suggestion import AgentSuggestion
from app.infrastructure.persistence.models.supervisor_session import SubAgentSession, SupervisorSession


class _ScalarRows:
    def __init__(self, rows: list[Any]) -> None:
        self._rows = rows

    def all(self) -> list[Any]:
        return self._rows


class _FakeDb:
    def __init__(self) -> None:
        self.rows: list[Any] = []

    def add(self, row: Any) -> None:
        self.rows.append(row)

    async def flush(self) -> None:
        return None

    async def scalars(self, _stmt):  # noqa: ANN001
        filtered = [row for row in self.rows if isinstance(row, AgentSuggestion)]
        return _ScalarRows(filtered)

    async def get(self, _model, _key):  # noqa: ANN001
        return None


@pytest.mark.asyncio
async def test_propose_agent_improvements_when_low_risk_then_auto_approved(monkeypatch) -> None:
    """Low-risk proposal should be auto-approved and immediately implemented."""

    monkeypatch.setattr("app.application.services.supervisor.initiative.settings.agent_initiative_enabled", True)
    monkeypatch.setattr("app.application.services.supervisor.initiative.settings.agent_initiative_auto_approve_enabled", True)
    monkeypatch.setattr("app.application.services.supervisor.initiative.settings.agent_initiative_auto_approve_max_risk_score", 0.3)
    monkeypatch.setattr("app.application.services.supervisor.initiative.settings.agent_initiative_auto_approve_max_impact_score", 0.9)

    db = _FakeDb()
    sup = SupervisorSession(
        tenant_id=uuid.uuid4(),
        goal="Improve retrieval quality for routine analysis",
        status="running",
        runtime_mode="inprocess",
        context_summary={},
    )
    sub = SubAgentSession(
        tenant_id=sup.tenant_id,
        supervisor_session_id=sup.id,
        role="researcher",
        status="running",
        runtime_mode="inprocess",
        toolset=[],
        short_memory={},
        spawn_order=0,
    )
    out = await propose_agent_improvements(
        db,  # type: ignore[arg-type]
        supervisor_session=sup,
        sub_agent=sub,
        role="researcher",
        goal=sup.goal,
        selected_skills=["context"],
        retrieval_sections=["semantic_memory"],
        meta_reasoning={"strategy_score": 0.74, "recommended_shift": "maintain_strategy", "issues": [], "attempts": 1},
        reflections=[{"attempt": 1}],
    )
    assert out
    assert any(row.status == "approved" for row in out)
    assert "agent_initiative_hints" in dict(sup.context_summary or {})


@pytest.mark.asyncio
async def test_review_agent_suggestion_cycle_when_pending_then_approved(monkeypatch) -> None:
    """Pending suggestion can be approved and reflected into session context."""

    monkeypatch.setattr("app.application.services.supervisor.initiative.settings.agent_initiative_enabled", True)
    db = SimpleNamespace(flush=lambda: None)

    async def _flush() -> None:
        return None

    db.flush = _flush

    sup = SupervisorSession(
        tenant_id=uuid.uuid4(),
        goal="goal",
        status="running",
        runtime_mode="inprocess",
        context_summary={},
    )
    row = AgentSuggestion(
        tenant_id=sup.tenant_id,
        supervisor_session_id=sup.id,
        sub_agent_session_id=None,
        proposal_type="workflow_optimization",
        proposed_by_role="critic",
        title="Improve workflow ordering",
        description="Move validation before external call",
        proposal_payload={},
        risk_level="low",
        impact_score=0.35,
        status="pending",
        requires_manual_approval=False,
    )
    reviewed = await review_agent_suggestion(
        db,  # type: ignore[arg-type]
        suggestion=row,
        decision="approved",
        reviewer_subject="dashboard:owner",
        supervisor_session=sup,
    )
    assert reviewed.status == "approved"
    assert reviewed.implemented_at is not None
    assert reviewed.reviewed_by_subject == "dashboard:owner"
    hints = list(dict(sup.context_summary or {}).get("agent_initiative_hints") or [])
    assert hints


@pytest.mark.asyncio
async def test_list_agent_suggestions_when_rows_exist_then_returns_rows() -> None:
    """List helper returns persisted suggestions for tenant."""

    db = _FakeDb()
    tenant_id = uuid.uuid4()
    db.add(
        AgentSuggestion(
            tenant_id=tenant_id,
            supervisor_session_id=None,
            sub_agent_session_id=None,
            proposal_type="prompt_optimization",
            proposed_by_role="researcher",
            title="Prompt fix",
            description="Use acceptance criteria",
            proposal_payload={},
            risk_level="low",
            impact_score=0.2,
            status="pending",
            requires_manual_approval=False,
        ),
    )
    rows = await list_agent_suggestions(db, tenant_id=tenant_id)  # type: ignore[arg-type]
    assert len(rows) == 1
