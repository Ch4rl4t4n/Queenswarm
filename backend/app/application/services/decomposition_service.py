"""LLM-backed goal decomposition service."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.llm_router import LiteLLMRouter
from app.core.logging import get_logger
from app.domain.goals.models import Goal, GoalAuditResult


class SubTaskSpec(BaseModel):
    """Validated decomposition unit consumed by the supervisor bridge."""

    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=3, max_length=180)
    description: str = Field(min_length=5, max_length=3000)
    agent_role_hint: str = Field(min_length=2, max_length=64)
    estimated_minutes: int = Field(ge=1, le=30)
    depends_on: list[int] = Field(default_factory=list)


def _prompt_file() -> Path:
    return Path(__file__).resolve().parents[1] / "prompts" / "goal_decomposition.md"


class DecompositionService:
    """Generate OODA-style sub-task plans from one goal."""

    def __init__(self, *, llm_router: LiteLLMRouter | None = None) -> None:
        """Initialize decomposition service with LiteLLM router dependency."""

        self._router = llm_router or LiteLLMRouter()
        self._logger = get_logger(__name__)
        self._system_prompt = _prompt_file().read_text(encoding="utf-8")
        self.last_cost_usd: float = 0.0

    async def decompose(
        self,
        session: AsyncSession,
        *,
        goal: Goal,
        previous_audit: GoalAuditResult | None,
    ) -> list[SubTaskSpec]:
        """Return validated sub-task specs, retrying schema failures up to 2 times."""

        payload = {
            "goal_title": goal.title,
            "goal_description_md": goal.description_md,
            "acceptance_criteria_md": goal.acceptance_criteria_md,
            "previous_audit": None
            if previous_audit is None
            else {
                "iteration": previous_audit.iteration,
                "is_done": previous_audit.is_done,
                "reasoning": previous_audit.reasoning,
                "remaining_work_md": previous_audit.remaining_work_md,
                "confidence": previous_audit.confidence,
            },
        }
        parse_error: str = "unknown"
        for attempt in range(1, 4):
            raw, cost_usd = await self._router.decompose(
                session,
                system_prompt=self._system_prompt,
                user_payload=json.dumps(payload, ensure_ascii=True),
                swarm_id=str(goal.tenant_id),
                task_id=f"goal-decompose-{goal.id}-i{goal.current_iteration}-a{attempt}",
            )
            self.last_cost_usd = float(cost_usd or 0.0)
            try:
                parsed = self._parse_response(raw)
                self._logger.info(
                    "goal.decompose.ok",
                    agent_id="goal_decomposer",
                    swarm_id=str(goal.tenant_id),
                    task_id=str(goal.id),
                    attempt=attempt,
                    item_count=len(parsed),
                )
                return parsed
            except (ValidationError, ValueError, TypeError, json.JSONDecodeError) as exc:
                parse_error = str(exc)
                self._logger.warning(
                    "goal.decompose.schema_retry",
                    agent_id="goal_decomposer",
                    swarm_id=str(goal.tenant_id),
                    task_id=str(goal.id),
                    attempt=attempt,
                    error=parse_error,
                )
                continue
        raise ValueError(f"Goal decomposition schema validation failed after retries: {parse_error}")

    @staticmethod
    def _parse_response(raw: str) -> list[SubTaskSpec]:
        """Parse raw LLM output as strict JSON list of `SubTaskSpec`."""

        text = raw.strip()
        if not text:
            raise ValueError("LLM returned empty decomposition payload.")
        blob: Any = json.loads(text)
        if not isinstance(blob, list):
            raise ValueError("LLM decomposition payload must be a JSON array.")
        out = [SubTaskSpec.model_validate(item) for item in blob]
        if len(out) == 0:
            raise ValueError("Decomposition list must not be empty.")
        if len(out) > 7:
            raise ValueError("Decomposition exceeds maximum 7 tasks.")
        for idx, item in enumerate(out):
            for dep in item.depends_on:
                if dep < 0 or dep >= idx:
                    raise ValueError("depends_on must reference prior task indexes.")
        return out


__all__ = ["DecompositionService", "SubTaskSpec"]
