"""LLM-backed goal completion auditor."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.llm_router import LiteLLMRouter
from app.core.logging import get_logger
from app.domain.goals.models import Goal, GoalAuditResult


class _GoalAuditPayload(BaseModel):
    """Strict JSON payload expected from the audit prompt."""

    model_config = ConfigDict(extra="forbid")

    iteration: int = Field(ge=1)
    is_done: bool
    reasoning: str = Field(min_length=3, max_length=6000)
    remaining_work_md: str = Field(default="", max_length=12000)
    confidence: float = Field(ge=0.0, le=1.0)


def _prompt_file() -> Path:
    return Path(__file__).resolve().parents[1] / "prompts" / "goal_audit.md"


class AuditorService:
    """Evaluate whether a goal is done using acceptance criteria and task evidence."""

    def __init__(self, *, llm_router: LiteLLMRouter | None = None) -> None:
        """Initialize auditor service with LiteLLM router dependency."""

        self._router = llm_router or LiteLLMRouter()
        self._logger = get_logger(__name__)
        self._system_prompt = _prompt_file().read_text(encoding="utf-8")
        self.last_cost_usd: float = 0.0

    async def audit(
        self,
        session: AsyncSession,
        *,
        goal: Goal,
        iteration: int,
        completed_sub_tasks: list[dict[str, Any]],
    ) -> GoalAuditResult:
        """Run conservative completion audit for one iteration."""

        payload = {
            "goal_title": goal.title,
            "goal_description_md": goal.description_md,
            "acceptance_criteria_md": goal.acceptance_criteria_md,
            "completed_sub_tasks": completed_sub_tasks,
            "iteration": iteration,
        }
        raw, cost_usd = await self._router.decompose(
            session,
            system_prompt=self._system_prompt,
            user_payload=json.dumps(payload, ensure_ascii=True),
            swarm_id=str(goal.tenant_id),
            task_id=f"goal-audit-{goal.id}-i{iteration}",
        )
        self.last_cost_usd = float(cost_usd or 0.0)
        parsed = _GoalAuditPayload.model_validate(json.loads(raw.strip()))

        is_done = bool(parsed.is_done)
        remaining = parsed.remaining_work_md.strip()
        # Conservative guardrail: non-empty remaining work cannot be "done".
        if is_done and remaining:
            is_done = False
        result = GoalAuditResult(
            iteration=parsed.iteration,
            is_done=is_done,
            reasoning=parsed.reasoning.strip(),
            remaining_work_md=remaining,
            confidence=float(parsed.confidence),
        )
        self._logger.info(
            "goal.audit.ok",
            agent_id="goal_auditor",
            swarm_id=str(goal.tenant_id),
            task_id=str(goal.id),
            iteration=iteration,
            is_done=result.is_done,
            confidence=result.confidence,
        )
        return result


__all__ = ["AuditorService"]
