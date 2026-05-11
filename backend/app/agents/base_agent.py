"""Abstract bee contract shared by scout / eval / sim / action colonies."""

from __future__ import annotations

import asyncio
import hashlib
import json
import uuid
from abc import ABC, abstractmethod
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from structlog.contextvars import bind_contextvars, clear_contextvars

from app.agents.cost_governor import CostGovernor
from app.core.config import settings
from app.core.logging import get_logger
from app.models.agent import Agent
from app.models.enums import AgentStatus
from app.models.knowledge import LearningLog
from app.models.reward import PollenReward

logger = get_logger(__name__)


class BaseAgent(ABC):
    """Runtime bee façade bound to persisted :class:`~app.models.agent.Agent` rows.

    Lifecycle hooks weave together CostGovernor enforcement, pollen accounting,
    :class:`~app.models.knowledge.LearningLog` reflections, and rapid-loop SLA timing
    mandated by queenswarm hive doctrine.
    """

    def __init__(
        self,
        *,
        db: AsyncSession,
        agent_record: Agent,
        cost_governor: CostGovernor | None = None,
    ) -> None:
        """Attach the swarm session plus ORM backbone for pollen + status updates."""

        self._db = db
        self._agent = agent_record
        self.cost_governor = cost_governor or CostGovernor()

    def __repr__(self) -> str:
        """Return a developer-friendly surrogate for swarm telemetry."""

        return f"{self.__class__.__name__}(agent_id={self.agent_id!s}, role={self._agent.role.value!r})"

    def waggle_cue(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Construct a compact waggle-dance cue for hive coordination (Redis / dance feed).

        Subclasses may extend with role-specific fingerprints; keep payloads small.
        """

        canonical = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
        digest = hashlib.sha256(canonical).hexdigest()[:16]
        return {
            "bee_class": self.__class__.__name__,
            "role": self._agent.role.value,
            "payload_digest": digest,
            "swarm_id": str(self.swarm_id) if self.swarm_id else None,
        }

    @property
    def agent_id(self) -> uuid.UUID:
        """Stable UUID aligned with Postgres ``agents.id``."""

        return self._agent.id

    @property
    def swarm_id(self) -> uuid.UUID | None:
        """Optional sub-swarm placement for decentralized hive minds."""

        return self._agent.swarm_id

    @property
    def pollen_points(self) -> float:
        """Rolling Maynard-Cross pollen associated with verified outcomes."""

        return float(self._agent.pollen_points)

    @abstractmethod
    async def execute(
        self,
        *,
        payload: dict[str, Any],
        task_id: uuid.UUID | None = None,
    ) -> dict[str, Any]:
        """Perform the narrowly scoped bee specialization.

        Args:
            payload: Task JSON blob issued by supervisors.
            task_id: Optional hive task lineage for pollen + reflection joins.

        Returns:
            Verified intermediate payload merged into swarm graph state transitions.
        """

    async def execute_task_cycle(
        self,
        *,
        payload: dict[str, Any],
        task_id: uuid.UUID | None = None,
        workflow_id: uuid.UUID | None = None,
        reflection: str | None = None,
        verified_outcome: bool = False,
        pollen_award_if_verified: float = 0.0,
        pollen_reason: str = "Verified swarm outcome credit",
    ) -> dict[str, Any]:
        """Run ``execute`` under CostGovernor + rapid SLA, then reconcile rewards/logs.

        Args:
            payload: Forwarded verbatim to :meth:`execute`.
            task_id: Optional foreign key bridging ``tasks``.
            workflow_id: Optional breaker graph identifier for telemetry context.
            reflection: Narrative persisted to ``learning_logs``.
            verified_outcome: Whether simulation gates approved the pollen transfer.
            pollen_award_if_verified: Quantity of pollen staged when proofs exist.
            pollen_reason: Explanation stored on ``pollen_rewards``.

        Returns:
            Result dictionary emitted by ``execute``.

        Raises:
            asyncio.TimeoutError: If ``execute`` exceeds ``rapid_loop_timeout_sec``.
            BudgetExceededError: When daily spend envelopes block new LLM bursts.
        """

        bind_contextvars(
            agent_id=str(self.agent_id),
            swarm_id=str(self.swarm_id or ""),
            task_id=str(task_id or ""),
            workflow_id=str(workflow_id or ""),
        )
        logger.info(
            "bee.task_cycle.start",
            role=self._agent.role.value,
            pollen_award_candidate=pollen_award_if_verified if verified_outcome else 0.0,
        )
        await self.cost_governor.assert_can_spend(self._db, delta_usd=0.0)
        started = datetime.now(tz=UTC)
        self._agent.status = AgentStatus.RUNNING
        self._agent.last_active_at = started
        await self._db.flush()
        try:
            outcome = await asyncio.wait_for(
                self.execute(payload=payload, task_id=task_id),
                timeout=float(settings.rapid_loop_timeout_sec),
            )
        except Exception as exc:  # noqa: BLE001 — bubble after marking failure state
            self._agent.status = AgentStatus.ERROR
            logger.error(
                "bee.task_cycle.failed",
                error_type=exc.__class__.__name__,
                error=str(exc),
            )
            await self._db.flush()
            raise
        else:
            self._agent.status = AgentStatus.IDLE
            if reflection:
                await self._write_learning_log(
                    task_id=task_id,
                    insight=reflection,
                    pollen_logged=pollen_award_if_verified if verified_outcome else 0.0,
                )
            if verified_outcome and pollen_award_if_verified > 0.0:
                await self._issue_pollen(
                    task_id=task_id,
                    amount=float(pollen_award_if_verified),
                    reason=pollen_reason,
                )
            await self._db.flush()
            logger.info(
                "bee.task_cycle.completed",
                role=self._agent.role.value,
                verified=verified_outcome,
            )
            return outcome
        finally:
            clear_contextvars()

    async def _issue_pollen(
        self,
        *,
        task_id: uuid.UUID | None,
        amount: float,
        reason: str,
    ) -> None:
        """Record PollenRewards and bump the mirrored counter on ``agents``.

        Args:
            task_id: Optional ``tasks.id`` lineage.
            amount: Verified pollen quantum.
            reason: Operator-facing rationale for ledger audits (<=500 chars).
        """

        safe_reason = reason[:500]
        reward = PollenReward(
            agent_id=self.agent_id,
            task_id=task_id,
            amount=float(amount),
            reason=safe_reason,
        )
        self._agent.pollen_points = float(self._agent.pollen_points) + float(amount)
        self._db.add(reward)

    async def _write_learning_log(
        self,
        *,
        task_id: uuid.UUID | None,
        insight: str,
        pollen_logged: float,
    ) -> None:
        """Persist imitation-friendly reflections referencing rapid-loop feedback.

        Args:
            task_id: Optional ``tasks.id`` binding.
            insight: Narrative distilled by the hive mind.
            pollen_logged: Pollen accrued during this cycle (possibly zero).
        """

        applied = datetime.now(tz=UTC) if pollen_logged > 0 else None
        log = LearningLog(
            agent_id=self.agent_id,
            task_id=task_id,
            insight_text=insight,
            applied_at=applied,
            pollen_earned=float(pollen_logged),
        )
        self._db.add(log)
