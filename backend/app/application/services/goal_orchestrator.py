"""Queen `/goal` orchestrator that reuses the existing supervisor runtime."""

from __future__ import annotations

import asyncio
from dataclasses import asdict
from datetime import UTC, datetime
import uuid
from typing import Any, Protocol

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.application.services.auditor_service import AuditorService
from app.application.services.decomposition_service import DecompositionService, SubTaskSpec
from app.application.services.supervisor.session_service import create_supervisor_session, get_supervisor_session
from app.application.services.supervisor.shared_context import SharedContextService
from app.core.cost_governor import BudgetExceededError, CostGovernor
from app.core.database import async_session
from app.core.logging import get_logger
from app.domain.goals.models import Goal, GoalAuditResult, GoalStatus
from app.infrastructure.persistence.models.goal import GoalAuditResultORM, GoalORM, GoalStatusORM


class SupervisorServiceProtocol(Protocol):
    """Runtime contract for delegating sub-tasks to existing supervisor sessions."""

    async def dispatch_sub_task(
        self,
        session: AsyncSession,
        *,
        goal: GoalORM,
        sub_task: SubTaskSpec,
        iteration: int,
    ) -> uuid.UUID: ...

    async def wait_for_sub_task(
        self,
        session: AsyncSession,
        *,
        supervisor_session_id: uuid.UUID,
        timeout_seconds: float,
    ) -> dict[str, Any]: ...


class SupervisorGoalBridge:
    """Adapter that routes goal sub-tasks into `create_supervisor_session`."""

    def __init__(self, *, poll_interval_seconds: float = 2.0) -> None:
        """Initialize reusable bridge for supervisor integration."""

        self._poll_interval_seconds = max(0.2, float(poll_interval_seconds))

    async def dispatch_sub_task(
        self,
        session: AsyncSession,
        *,
        goal: GoalORM,
        sub_task: SubTaskSpec,
        iteration: int,
    ) -> uuid.UUID:
        """Create one durable supervisor session for a decomposed sub-task."""

        supervisor_goal = (
            f"[Goal:{goal.id}] Iteration {iteration} · {sub_task.title}\n\n"
            f"{sub_task.description}"
        )
        row = await create_supervisor_session(
            session,
            goal=supervisor_goal,
            created_by_subject=str(goal.user_id) if goal.user_id else None,
            runtime_mode="durable",
            roles=[sub_task.agent_role_hint],
            shared_context=SharedContextService(),
            tenant_id=goal.tenant_id,
        )
        await session.flush()
        return row.id

    async def wait_for_sub_task(
        self,
        session: AsyncSession,
        *,
        supervisor_session_id: uuid.UUID,
        timeout_seconds: float,
    ) -> dict[str, Any]:
        """Poll supervisor session until terminal status or timeout."""

        started = datetime.now(tz=UTC)
        while True:
            row = await get_supervisor_session(session, supervisor_session_id)
            if row is None:
                return {"session_id": str(supervisor_session_id), "status": "missing", "output": ""}
            if row.status in {"completed", "needs_input", "stopped"}:
                sub_outputs: list[str] = []
                for sub in row.sub_agents:
                    if isinstance(sub.last_output, str) and sub.last_output.strip():
                        sub_outputs.append(sub.last_output.strip())
                return {
                    "session_id": str(supervisor_session_id),
                    "status": row.status,
                    "output": "\n\n".join(sub_outputs)[:12000],
                    "context_summary": dict(row.context_summary or {}),
                }
            elapsed = (datetime.now(tz=UTC) - started).total_seconds()
            if elapsed >= timeout_seconds:
                return {"session_id": str(supervisor_session_id), "status": "timeout", "output": ""}
            await asyncio.sleep(self._poll_interval_seconds)


class GoalOrchestrator:
    """Drive decompose → delegate → audit loop until goal completion or halt condition."""

    def __init__(
        self,
        *,
        db_session_factory: async_sessionmaker[AsyncSession] = async_session,
        supervisor_service: SupervisorServiceProtocol | None = None,
        decomposer: DecompositionService | None = None,
        auditor: AuditorService | None = None,
        cost_governor: CostGovernor | None = None,
        logger: Any = None,
    ) -> None:
        """Construct orchestrator dependencies."""

        self._db_session_factory = db_session_factory
        self._supervisor_service = supervisor_service or SupervisorGoalBridge()
        self._decomposer = decomposer or DecompositionService()
        self._auditor = auditor or AuditorService()
        self._cost_governor = cost_governor or CostGovernor()
        self._logger = logger or get_logger(__name__)

    async def submit(
        self,
        *,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID | None,
        title: str,
        description_md: str,
        acceptance_criteria_md: str,
        max_iterations: int,
        budget_usd: float,
        root_task_id: uuid.UUID | None = None,
    ) -> Goal:
        """Persist a new pending goal."""

        async with self._db_session_factory() as session:
            row = GoalORM(
                tenant_id=tenant_id,
                user_id=user_id,
                title=title.strip(),
                description_md=description_md.strip(),
                acceptance_criteria_md=acceptance_criteria_md.strip(),
                max_iterations=max(1, int(max_iterations)),
                budget_usd=max(0.0, float(budget_usd)),
                status=GoalStatusORM.PENDING,
                current_iteration=0,
                root_task_id=root_task_id,
            )
            session.add(row)
            await session.commit()
            await session.refresh(row)
            self._logger.info(
                "goal.submit.ok",
                agent_id="goal_orchestrator",
                swarm_id=str(tenant_id),
                task_id=str(row.id),
            )
            return self._to_domain(row)

    async def execute(self, goal_id: uuid.UUID) -> Goal:
        """Execute goal loop until completed, failed, or halted."""

        async with self._db_session_factory() as session:
            row = await session.get(GoalORM, goal_id)
            if row is None:
                raise ValueError(f"Goal not found: {goal_id}")
            if row.status in {GoalStatusORM.COMPLETED, GoalStatusORM.HALTED_BY_HUMAN, GoalStatusORM.HALTED_BY_BUDGET}:
                return self._to_domain(row)

            while True:
                try:
                    await self._cost_governor.assert_can_spend(session, delta_usd=0.0)
                except BudgetExceededError:
                    row.status = GoalStatusORM.HALTED_BY_BUDGET
                    row.completed_at = datetime.now(tz=UTC)
                    row.halt_reason = "cost_governor_budget_block"
                    await session.commit()
                    break
                if row.budget_usd > 0 and float(row.spent_usd) >= float(row.budget_usd):
                    row.status = GoalStatusORM.HALTED_BY_BUDGET
                    row.completed_at = datetime.now(tz=UTC)
                    row.halt_reason = "budget_exceeded"
                    await session.commit()
                    break

                next_iteration = int(row.current_iteration) + 1
                if next_iteration > int(row.max_iterations):
                    row.status = GoalStatusORM.FAILED
                    row.completed_at = datetime.now(tz=UTC)
                    row.halt_reason = "max_iterations_reached"
                    await session.commit()
                    break

                row.current_iteration = next_iteration
                row.status = GoalStatusORM.DECOMPOSING
                await session.commit()

                prior_audit = await self._latest_audit(session, goal_id=row.id)
                goal_domain = self._to_domain(row)
                sub_tasks = await self._decomposer.decompose(
                    session,
                    goal=goal_domain,
                    previous_audit=prior_audit,
                )
                row.spent_usd = float(row.spent_usd) + float(self._decomposer.last_cost_usd)
                if row.budget_usd > 0 and float(row.spent_usd) >= float(row.budget_usd):
                    row.status = GoalStatusORM.HALTED_BY_BUDGET
                    row.completed_at = datetime.now(tz=UTC)
                    row.halt_reason = "budget_exceeded_during_decomposition"
                    await session.commit()
                    break

                row.status = GoalStatusORM.EXECUTING
                await session.commit()

                completed_sub_tasks: list[dict[str, Any]] = []
                for sub in sub_tasks:
                    sup_session_id = await self._supervisor_service.dispatch_sub_task(
                        session,
                        goal=row,
                        sub_task=sub,
                        iteration=next_iteration,
                    )
                    result = await self._supervisor_service.wait_for_sub_task(
                        session,
                        supervisor_session_id=sup_session_id,
                        timeout_seconds=480.0,
                    )
                    completed_sub_tasks.append(
                        {
                            "title": sub.title,
                            "description": sub.description,
                            "agent_role_hint": sub.agent_role_hint,
                            "estimated_minutes": sub.estimated_minutes,
                            "depends_on": list(sub.depends_on),
                            "supervisor_result": result,
                        }
                    )

                row.status = GoalStatusORM.AUDITING
                await session.commit()
                audit = await self._auditor.audit(
                    session,
                    goal=self._to_domain(row),
                    iteration=next_iteration,
                    completed_sub_tasks=completed_sub_tasks,
                )
                row.spent_usd = float(row.spent_usd) + float(self._auditor.last_cost_usd)
                audit_row = GoalAuditResultORM(
                    goal_id=row.id,
                    tenant_id=row.tenant_id,
                    iteration=audit.iteration,
                    is_done=bool(audit.is_done),
                    reasoning=audit.reasoning,
                    remaining_work_md=audit.remaining_work_md,
                    confidence=float(audit.confidence),
                    raw_payload=asdict(audit),
                )
                session.add(audit_row)

                if audit.is_done and float(audit.confidence) >= 0.75:
                    row.status = GoalStatusORM.COMPLETED
                    row.completed_at = datetime.now(tz=UTC)
                    row.halt_reason = None
                    await session.commit()
                    break

                if row.budget_usd > 0 and float(row.spent_usd) >= float(row.budget_usd):
                    row.status = GoalStatusORM.HALTED_BY_BUDGET
                    row.completed_at = datetime.now(tz=UTC)
                    row.halt_reason = "budget_exceeded_after_audit"
                    await session.commit()
                    break

                row.status = GoalStatusORM.PENDING
                await session.commit()

            await session.refresh(row)
            return self._to_domain(row)

    async def halt(self, goal_id: uuid.UUID, *, reason: str, user_id: uuid.UUID | None) -> Goal:
        """Apply explicit human override and stop further loop execution."""

        async with self._db_session_factory() as session:
            row = await session.get(GoalORM, goal_id)
            if row is None:
                raise ValueError(f"Goal not found: {goal_id}")
            row.status = GoalStatusORM.HALTED_BY_HUMAN
            row.completed_at = datetime.now(tz=UTC)
            row.halt_reason = reason.strip()[:2000]
            if user_id is not None:
                row.user_id = user_id
            await session.commit()
            await session.refresh(row)
            self._logger.info(
                "goal.halt.human",
                agent_id="goal_orchestrator",
                swarm_id=str(row.tenant_id),
                task_id=str(goal_id),
            )
            return self._to_domain(row)

    @staticmethod
    async def _latest_audit(session: AsyncSession, *, goal_id: uuid.UUID) -> GoalAuditResult | None:
        stmt = (
            select(GoalAuditResultORM)
            .where(GoalAuditResultORM.goal_id == goal_id)
            .order_by(GoalAuditResultORM.created_at.desc())
            .limit(1)
        )
        row = await session.scalar(stmt)
        if row is None:
            return None
        return GoalAuditResult(
            iteration=int(row.iteration),
            is_done=bool(row.is_done),
            reasoning=str(row.reasoning or ""),
            remaining_work_md=str(row.remaining_work_md or ""),
            confidence=float(row.confidence),
        )

    @staticmethod
    def _to_domain(row: GoalORM) -> Goal:
        return Goal(
            id=row.id,
            tenant_id=row.tenant_id,
            user_id=row.user_id,
            title=row.title,
            description_md=row.description_md,
            acceptance_criteria_md=row.acceptance_criteria_md,
            max_iterations=int(row.max_iterations),
            budget_usd=float(row.budget_usd),
            status=GoalStatus(row.status.value),
            current_iteration=int(row.current_iteration),
            root_task_id=row.root_task_id,
            created_at=row.created_at,
            completed_at=row.completed_at,
        )


def build_default_goal_orchestrator() -> GoalOrchestrator:
    """Factory for API and Celery entry points."""

    return GoalOrchestrator(
        db_session_factory=async_session,
        supervisor_service=SupervisorGoalBridge(),
        decomposer=DecompositionService(),
        auditor=AuditorService(),
        cost_governor=CostGovernor(),
        logger=get_logger(__name__),
    )


__all__ = ["GoalOrchestrator", "SupervisorGoalBridge", "build_default_goal_orchestrator"]
