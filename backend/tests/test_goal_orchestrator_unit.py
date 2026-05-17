"""Unit tests for GoalOrchestrator and decomposition retry behavior."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
import uuid

import pytest

from app.application.services.decomposition_service import DecompositionService
from app.application.services.goal_orchestrator import GoalOrchestrator
from app.domain.goals.models import Goal, GoalAuditResult, GoalStatus
from app.infrastructure.persistence.models.goal import GoalORM, GoalStatusORM


class _FakeSession:
    def __init__(self, goal: GoalORM) -> None:
        self.goal = goal
        self.added: list[object] = []

    async def get(self, model, item_id):  # noqa: ANN001
        if model is GoalORM and item_id == self.goal.id:
            return self.goal
        return None

    async def commit(self) -> None:
        return None

    async def refresh(self, _row: object) -> None:
        return None

    def add(self, row: object) -> None:
        self.added.append(row)


class _FakeSessionFactory:
    def __init__(self, session: _FakeSession) -> None:
        self._session = session

    async def __aenter__(self) -> _FakeSession:
        return self._session

    async def __aexit__(self, exc_type, exc, tb) -> None:  # noqa: ANN001
        del exc_type, exc, tb
        return None

    def __call__(self) -> "_FakeSessionFactory":
        return self


class _FakeSupervisor:
    def __init__(self) -> None:
        self.dispatched = 0

    async def dispatch_sub_task(self, session, *, goal, sub_task, iteration):  # noqa: ANN001
        del session, goal, sub_task, iteration
        self.dispatched += 1
        return uuid.uuid4()

    async def wait_for_sub_task(self, session, *, supervisor_session_id, timeout_seconds):  # noqa: ANN001
        del session, supervisor_session_id, timeout_seconds
        return {"status": "completed", "output": "done"}


class _FakeGovernor:
    async def assert_can_spend(self, *_args, **_kwargs) -> None:  # noqa: ANN002, ANN003
        return None


class _FakeLogger:
    def info(self, *_args, **_kwargs) -> None:  # noqa: ANN002, ANN003
        return None

    def warning(self, *_args, **_kwargs) -> None:  # noqa: ANN002, ANN003
        return None


def _goal_row(*, status: GoalStatusORM = GoalStatusORM.PENDING) -> GoalORM:
    now = datetime.now(tz=UTC)
    row = GoalORM(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        title="Test Goal",
        description_md="desc",
        acceptance_criteria_md="criteria",
        max_iterations=3,
        budget_usd=50.0,
        status=status,
        current_iteration=0,
        root_task_id=None,
        created_at=now,
        updated_at=now,
        completed_at=None,
        spent_usd=0.0,
        halt_reason=None,
    )
    return row


@pytest.mark.asyncio
async def test_decompose_then_audit_done_completes_goal(monkeypatch) -> None:
    """Goal completes when auditor returns done with high confidence."""

    row = _goal_row()
    session = _FakeSession(row)
    async def _decompose(*_args, **_kwargs):  # noqa: ANN002, ANN003
        return [
            SimpleNamespace(title="t1", description="d1", agent_role_hint="researcher", estimated_minutes=10, depends_on=[])

        ]

    async def _audit(*_args, **_kwargs):  # noqa: ANN002, ANN003
        return GoalAuditResult(
            iteration=1,
            is_done=True,
            reasoning="all done",
            remaining_work_md="",
            confidence=0.9,
        )

    decomposer = SimpleNamespace(last_cost_usd=0.1, decompose=_decompose)
    auditor = SimpleNamespace(last_cost_usd=0.1, audit=_audit)
    orchestrator = GoalOrchestrator(
        db_session_factory=_FakeSessionFactory(session),  # type: ignore[arg-type]
        supervisor_service=_FakeSupervisor(),
        decomposer=decomposer,  # type: ignore[arg-type]
        auditor=auditor,  # type: ignore[arg-type]
        cost_governor=_FakeGovernor(),
        logger=_FakeLogger(),
    )
    async def _latest(*_args, **_kwargs):  # noqa: ANN002, ANN003
        return None

    monkeypatch.setattr(orchestrator, "_latest_audit", _latest)

    goal = await orchestrator.execute(row.id)
    assert goal.status == GoalStatus.COMPLETED
    assert goal.current_iteration == 1


@pytest.mark.asyncio
async def test_decompose_then_audit_not_done_iterates_again(monkeypatch) -> None:
    """Loop advances to next iteration when audit says not done."""

    row = _goal_row()
    session = _FakeSession(row)
    decomposer_calls = {"count": 0}

    async def _decompose(*_args, **_kwargs):  # noqa: ANN002, ANN003
        decomposer_calls["count"] += 1
        return [SimpleNamespace(title="t1", description="d1", agent_role_hint="researcher", estimated_minutes=10, depends_on=[])]

    audit_calls = {"count": 0}

    async def _audit(*_args, **_kwargs):  # noqa: ANN002, ANN003
        audit_calls["count"] += 1
        if audit_calls["count"] == 1:
            return GoalAuditResult(
                iteration=1,
                is_done=False,
                reasoning="not yet",
                remaining_work_md="more",
                confidence=0.6,
            )
        return GoalAuditResult(
            iteration=2,
            is_done=True,
            reasoning="done now",
            remaining_work_md="",
            confidence=0.8,
        )

    decomposer = SimpleNamespace(last_cost_usd=0.1, decompose=_decompose)
    auditor = SimpleNamespace(last_cost_usd=0.1, audit=_audit)
    orchestrator = GoalOrchestrator(
        db_session_factory=_FakeSessionFactory(session),  # type: ignore[arg-type]
        supervisor_service=_FakeSupervisor(),
        decomposer=decomposer,  # type: ignore[arg-type]
        auditor=auditor,  # type: ignore[arg-type]
        cost_governor=_FakeGovernor(),
        logger=_FakeLogger(),
    )
    async def _latest(*_args, **_kwargs):  # noqa: ANN002, ANN003
        return None

    monkeypatch.setattr(orchestrator, "_latest_audit", _latest)

    goal = await orchestrator.execute(row.id)
    assert goal.status == GoalStatus.COMPLETED
    assert goal.current_iteration == 2
    assert decomposer_calls["count"] == 2


@pytest.mark.asyncio
async def test_budget_exceeded_halts_with_budget_status(monkeypatch) -> None:
    """Existing spent budget halts goal before decomposition."""

    row = _goal_row()
    row.budget_usd = 1.0
    row.spent_usd = 1.1
    session = _FakeSession(row)
    orchestrator = GoalOrchestrator(
        db_session_factory=_FakeSessionFactory(session),  # type: ignore[arg-type]
        supervisor_service=_FakeSupervisor(),
        decomposer=SimpleNamespace(last_cost_usd=0.0, decompose=lambda *_a, **_k: []),  # type: ignore[arg-type]
        auditor=SimpleNamespace(last_cost_usd=0.0, audit=lambda *_a, **_k: None),  # type: ignore[arg-type]
        cost_governor=_FakeGovernor(),
        logger=_FakeLogger(),
    )
    async def _latest(*_args, **_kwargs):  # noqa: ANN002, ANN003
        return None

    monkeypatch.setattr(orchestrator, "_latest_audit", _latest)

    goal = await orchestrator.execute(row.id)
    assert goal.status == GoalStatus.HALTED_BY_BUDGET


@pytest.mark.asyncio
async def test_max_iterations_reached_fails(monkeypatch) -> None:
    """Goal fails once max iteration cap is reached."""

    row = _goal_row()
    row.max_iterations = 1
    row.current_iteration = 1
    session = _FakeSession(row)
    orchestrator = GoalOrchestrator(
        db_session_factory=_FakeSessionFactory(session),  # type: ignore[arg-type]
        supervisor_service=_FakeSupervisor(),
        decomposer=SimpleNamespace(last_cost_usd=0.0, decompose=lambda *_a, **_k: []),  # type: ignore[arg-type]
        auditor=SimpleNamespace(last_cost_usd=0.0, audit=lambda *_a, **_k: None),  # type: ignore[arg-type]
        cost_governor=_FakeGovernor(),
        logger=_FakeLogger(),
    )
    async def _latest(*_args, **_kwargs):  # noqa: ANN002, ANN003
        return None

    monkeypatch.setattr(orchestrator, "_latest_audit", _latest)

    goal = await orchestrator.execute(row.id)
    assert goal.status == GoalStatus.FAILED


@pytest.mark.asyncio
async def test_human_halt_marks_halted_by_human() -> None:
    """Human halt endpoint should apply terminal halted state."""

    row = _goal_row()
    session = _FakeSession(row)
    orchestrator = GoalOrchestrator(
        db_session_factory=_FakeSessionFactory(session),  # type: ignore[arg-type]
        supervisor_service=_FakeSupervisor(),
        decomposer=SimpleNamespace(last_cost_usd=0.0, decompose=lambda *_a, **_k: []),  # type: ignore[arg-type]
        auditor=SimpleNamespace(last_cost_usd=0.0, audit=lambda *_a, **_k: None),  # type: ignore[arg-type]
        cost_governor=_FakeGovernor(),
        logger=_FakeLogger(),
    )
    goal = await orchestrator.halt(row.id, reason="manual stop", user_id=row.user_id)
    assert goal.status == GoalStatus.HALTED_BY_HUMAN


@pytest.mark.asyncio
async def test_low_confidence_audit_does_not_complete(monkeypatch) -> None:
    """Low-confidence done verdict should not mark the goal complete."""

    row = _goal_row()
    row.max_iterations = 1
    session = _FakeSession(row)

    async def _decompose(*_args, **_kwargs):  # noqa: ANN002, ANN003
        return [SimpleNamespace(title="t1", description="d1", agent_role_hint="researcher", estimated_minutes=10, depends_on=[])]

    async def _audit(*_args, **_kwargs):  # noqa: ANN002, ANN003
        return GoalAuditResult(
            iteration=1,
            is_done=True,
            reasoning="might be done",
            remaining_work_md="",
            confidence=0.5,
        )

    orchestrator = GoalOrchestrator(
        db_session_factory=_FakeSessionFactory(session),  # type: ignore[arg-type]
        supervisor_service=_FakeSupervisor(),
        decomposer=SimpleNamespace(last_cost_usd=0.0, decompose=_decompose),  # type: ignore[arg-type]
        auditor=SimpleNamespace(last_cost_usd=0.0, audit=_audit),  # type: ignore[arg-type]
        cost_governor=_FakeGovernor(),
        logger=_FakeLogger(),
    )
    async def _latest(*_args, **_kwargs):  # noqa: ANN002, ANN003
        return None

    monkeypatch.setattr(orchestrator, "_latest_audit", _latest)

    goal = await orchestrator.execute(row.id)
    assert goal.status == GoalStatus.FAILED


@pytest.mark.asyncio
async def test_decomposer_schema_validation_retry() -> None:
    """Decomposition service retries malformed JSON once, then succeeds."""

    class _Router:
        def __init__(self) -> None:
            self.calls = 0

        async def decompose(self, *_args, **_kwargs):  # noqa: ANN002, ANN003
            self.calls += 1
            if self.calls == 1:
                return "{not json", 0.01
            return (
                '[{"title":"Task A","description":"Do task A thoroughly","agent_role_hint":"researcher","estimated_minutes":15,"depends_on":[]}]',
                0.01,
            )

    goal = Goal(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        title="Retry goal",
        description_md="desc",
        acceptance_criteria_md="criteria",
        max_iterations=2,
        budget_usd=5.0,
        status=GoalStatus.PENDING,
        current_iteration=1,
        root_task_id=None,
        created_at=datetime.now(tz=UTC),
        completed_at=None,
    )
    service = DecompositionService(llm_router=_Router())  # type: ignore[arg-type]
    fake_session = SimpleNamespace()
    out = await service.decompose(fake_session, goal=goal, previous_audit=None)  # type: ignore[arg-type]
    assert len(out) == 1
    assert out[0].title == "Task A"
