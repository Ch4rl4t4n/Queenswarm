"""Auto Workflow Breaker — LLM-powered decomposition with Recipe Library recall."""

from __future__ import annotations

import json
import uuid

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from structlog.contextvars import bind_contextvars, clear_contextvars

from app.core.chroma_client import find_similar_recipes
from app.core.llm_router import LiteLLMRouter
from app.core.config import settings
from app.core.logging import get_logger
from app.models.enums import StepStatus, WorkflowStatus
from app.models.recipe import Recipe as RecipeRow
from app.models.workflow import Workflow, WorkflowStep
from app.schemas.workflow_breaker import (
    BreakerDecomposition,
    DecomposeWorkflowResponse,
    WorkflowStepBrief,
)
from app.services.workflow_breaker.parsing import extract_breaker_json
from app.workflows.prompts import DECOMPOSITION_SYSTEM_PROMPT
from app.workflows.validators import WorkflowValidator

logger = get_logger(__name__)


class AutoWorkflowBreaker:
    """Intelligent task decomposition engine (Phase C)."""

    def __init__(self) -> None:
        """Construct breaker with a fresh LiteLLM router."""

        self._router = LiteLLMRouter()

    async def _resolve_matching_recipe(
        self,
        db: AsyncSession,
        *,
        task_text: str,
        explicit: uuid.UUID | None,
        enrich: bool,
    ) -> uuid.UUID | None:
        """Pick a Recipe row from hints, similarity search, or leave unset."""

        if explicit is not None:
            row = await db.get(RecipeRow, explicit)
            if row is None:
                msg = "matching_recipe_id does not reference a persisted recipe."
                raise ValueError(msg)
            return explicit

        if not enrich:
            return None

        try:
            hit = await find_similar_recipes(task_text)
        except (
            ConnectionError,
            OSError,
            TimeoutError,
            ValueError,
            RuntimeError,
        ) as exc:
            logger.warning("workflow_breaker.chroma_unavailable", error=str(exc))
            return None

        if hit is None:
            return None

        metadata = dict(hit.metadata or {})
        rid = metadata.get("postgres_recipe_id")
        if not rid:
            return None
        try:
            rid_uuid = uuid.UUID(str(rid))
        except ValueError:
            return None
        recipe = await db.get(RecipeRow, rid_uuid)
        return recipe.id if recipe is not None else None

    async def decompose(
        self,
        db: AsyncSession,
        *,
        task_text: str,
        matching_recipe_id: uuid.UUID | None = None,
        enrich_from_chroma_recipes: bool = False,
        max_steps: int = 7,
        prefer_recipe: uuid.UUID | None = None,
        swarm_id: str = "",
        agent_task_id: str | None = None,
    ) -> DecomposeWorkflowResponse:
        """Decompose ``task_text`` into persisted Workflow + WorkflowStep rows.

        Args:
            db: Active async session (caller commits).
            task_text: Operator narrative to break down.
            matching_recipe_id: Optional FK hint (same as ``prefer_recipe`` if provided).
            enrich_from_chroma_recipes: When True, cosine-match Recipe Library context.
            max_steps: Hard cap (3-7 enforced by schema).
            prefer_recipe: Alias for ``matching_recipe_id``.
            swarm_id: Hive tracing id.
            agent_task_id: LangGraph / Celery correlation id.

        Returns:
            API-oriented projection of the stored workflow graph.

        Raises:
            ValueError: On validation failures.
            ValidationError: When pydantic rejects payload shape.
            RuntimeError: When LLM stack exhausts.
        """

        bind_contextvars(
            swarm_id=swarm_id,
            agent_id=None,
            task_id=agent_task_id,
            workflow_id=None,
        )
        prefer = prefer_recipe or matching_recipe_id
        _ = max(3, min(max_steps, 7))

        logger.info(
            "auto_workflow_breaker.start",
            task_chars=len(task_text),
            enrich_recipe_chroma=enrich_from_chroma_recipes,
        )
        try:
            recipe_hints: list[str] = []
            if prefer is not None:
                recipe_row = await db.get(RecipeRow, prefer)
                if recipe_row is None:
                    msg = "prefer_recipe / matching_recipe_id does not reference a persisted recipe."
                    raise ValueError(msg)
                recipe_hints.append(
                    json.dumps(
                        {
                            "recipe_name": recipe_row.name,
                            "topic_tags": recipe_row.topic_tags,
                            "template": recipe_row.workflow_template,
                        },
                        default=str,
                    ),
                )

            if enrich_from_chroma_recipes:
                try:
                    chroma_hit = await find_similar_recipes(task_text)
                except (
                    ConnectionError,
                    OSError,
                    TimeoutError,
                    ValueError,
                    RuntimeError,
                ) as exc:
                    logger.warning("workflow_breaker.chroma_unavailable", error=str(exc))
                    chroma_hit = None
                if chroma_hit is not None:
                    recipe_hints.append(chroma_hit.model_dump_json())

            user_payload = {
                "task": task_text,
                "recipe_hints": recipe_hints,
                "hive_directives": {
                    "rapid_loop_timeout_sec": settings.rapid_loop_timeout_sec,
                    "reward_threshold_pass": settings.reward_threshold_pass,
                    "max_steps_cap": max_steps,
                },
            }
            user_json = json.dumps(user_payload, default=str)

            raw_content, _decomposition_cost_usd = await self._router.decompose(
                db,
                system_prompt=DECOMPOSITION_SYSTEM_PROMPT,
                user_payload=user_json,
                swarm_id=swarm_id,
                task_id=agent_task_id,
            )

            blob = extract_breaker_json(raw_content)
            ok, reasons = WorkflowValidator.validate_decomposition(blob)
            if not ok:
                logger.warning("auto_workflow_breaker.preflight_failed", reasons=reasons)
                raise ValueError(f"Invalid decomposition: {'; '.join(reasons)}")

            draft = BreakerDecomposition.model_validate(blob)

            matched_id = await self._resolve_matching_recipe(
                db,
                task_text=task_text,
                explicit=prefer,
                enrich=enrich_from_chroma_recipes,
            )

            workflow = Workflow(
                original_task_text=task_text,
                decomposition_rationale=draft.rationale,
                status=WorkflowStatus.EXECUTING,
                total_steps=len(draft.steps),
                completed_steps=0,
                parallelizable_groups=draft.parallelizable_groups,
                matching_recipe_id=matched_id,
                estimated_duration_sec=draft.estimated_duration_sec,
            )
            db.add(workflow)
            await db.flush()

            bind_contextvars(workflow_id=str(workflow.id))

            ordered = sorted(draft.steps, key=lambda step: step.order)
            for step in ordered:
                row = WorkflowStep(
                    workflow_id=workflow.id,
                    step_order=step.order,
                    description=step.description,
                    agent_role=step.agent_role,
                    status=StepStatus.PENDING,
                    input_schema=step.input_schema,
                    output_schema=step.output_schema,
                    guardrails=step.guardrails,
                    evaluation_criteria=step.evaluation_criteria,
                )
                db.add(row)

            await db.flush()
            hydrated = await db.scalar(
                select(Workflow)
                .options(selectinload(Workflow.steps))
                .where(Workflow.id == workflow.id),
            )
            if hydrated is None:
                msg = "Failed to reload workflow after decomposition."
                raise RuntimeError(msg)

            briefs = [
                WorkflowStepBrief(
                    id=step.id,
                    step_order=step.step_order,
                    description=step.description,
                    agent_role=step.agent_role,
                )
                for step in sorted(hydrated.steps, key=lambda s: s.step_order)
            ]
            return DecomposeWorkflowResponse(
                workflow_id=hydrated.id,
                status=hydrated.status.value,
                total_steps=hydrated.total_steps,
                parallel_groups=list(hydrated.parallelizable_groups or []),
                steps=briefs,
                decomposition_rationale=hydrated.decomposition_rationale,
            )
        except ValidationError:
            raise
        finally:
            clear_contextvars()

    async def _find_matching_recipe(self, task_text: str, db: AsyncSession) -> RecipeRow | None:
        """Semantic Recipe Library lookup above the hive cosine threshold."""

        matched_id = await self._resolve_matching_recipe(
            db,
            task_text=task_text,
            explicit=None,
            enrich=True,
        )
        if matched_id is None:
            return None
        row = await db.get(RecipeRow, matched_id)
        return row


__all__ = ["AutoWorkflowBreaker"]
