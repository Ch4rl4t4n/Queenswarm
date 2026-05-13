"""Auto Workflow Breaker — LLM-powered decomposition with Recipe Library recall."""

from __future__ import annotations

import json
import uuid
from typing import Any

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from structlog.contextvars import bind_contextvars, clear_contextvars

from app.core.chroma_client import find_similar_recipes
from app.agents.cost_governor import BudgetExceededError
from app.core.llm_router import LiteLLMRouter
from app.core.config import settings
from app.core.logging import get_logger
from app.models.enums import AgentRole, StepStatus, WorkflowStatus
from app.models.recipe import Recipe as RecipeRow
from app.models.workflow import Workflow, WorkflowStep
from app.schemas.workflow_breaker import (
    BreakerDecomposition,
    BreakerStepDraft,
    DecomposeWorkflowResponse,
    PreviewDecompositionResponse,
    PreviewWorkflowStep,
    RecipeMatchBrief,
    WorkflowStepBrief,
)
from app.services.workflow_breaker.parsing import extract_breaker_json
from app.workflows.prompts import DECOMPOSITION_SYSTEM_PROMPT
from app.workflows.validators import WorkflowValidator

logger = get_logger(__name__)


def _breaker_static_fallback(task_text: str) -> BreakerDecomposition:
    """Return a compliant 3-step scaffold when LLM output is unusable.

    Args:
        task_text: Operator narrative.

    Returns:
        Valid :class:`BreakerDecomposition` respecting min step count and rationale length.
    """

    safe_task = task_text.strip().replace("\n", " ")
    if len(safe_task) < 4:
        safe_task = "Expand the operator task narrative with explicit deliverables."
    chunk = safe_task[:880]
    rationale = (
        f"LLM decomposition failed or was invalid — scout→eval→report fallback for: {chunk}"
    )
    if len(rationale) < 16:
        rationale = f"{rationale} (auto-extended for validator)."

    guards: dict[str, object] = {"pii": "Strip secrets before outbound tools.", "budget": "Honor Cost Governor ceilings."}
    rubric: dict[str, object] = {
        "verification": "Simulator or human confirms output matches task intent.",
        "quality": "Evidence-backed, no fabricated URLs.",
    }

    steps: list[BreakerStepDraft] = [
        BreakerStepDraft(
            order=1,
            description=f"Scout gather factual inputs, sources, and constraints for: {chunk}",
            agent_role=AgentRole.SCRAPER,
            guardrails=guards,
            evaluation_criteria=rubric,
        ),
        BreakerStepDraft(
            order=2,
            description="Evaluator cross-check scout material, score confidence, flag gaps before delivery.",
            agent_role=AgentRole.EVALUATOR,
            guardrails=guards,
            evaluation_criteria=rubric,
        ),
        BreakerStepDraft(
            order=3,
            description=f"Reporter synthesize verified findings into the requested deliverable aligned with: {chunk}",
            agent_role=AgentRole.REPORTER,
            guardrails=guards,
            evaluation_criteria=rubric,
        ),
    ]

    return BreakerDecomposition(rationale=rationale, parallelizable_groups=[], estimated_duration_sec=600, steps=steps)


def _guardrail_summary(guards: dict[str, Any]) -> str:
    """Flatten guardrails for dashboard one-liners."""

    if not guards:
        return "Guardrail · bez explicitných obmedzení v návrhu."
    parts: list[str] = []
    for key, val in list(guards.items())[:6]:
        if isinstance(val, (str, int, float, bool)):
            parts.append(f"{key}: {val}")
        else:
            blob = json.dumps(val, default=str)
            parts.append(f"{key}: {blob[:120]}")
    return "Guardrail · " + "; ".join(parts)


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

    async def _build_recipe_hints(
        self,
        db: AsyncSession,
        *,
        prefer: uuid.UUID | None,
        task_text: str,
        enrich_from_chroma_recipes: bool,
    ) -> tuple[list[str], Any | None]:
        """Collect JSON hint blobs for the LLM and retain the optional Chroma hit for UI badges."""

        recipe_hints: list[str] = []
        chroma_hit: Any | None = None
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

        return recipe_hints, chroma_hit

    async def _run_decomposition_core(
        self,
        db: AsyncSession,
        *,
        task_text: str,
        matching_recipe_id: uuid.UUID | None,
        enrich_from_chroma_recipes: bool,
        max_steps: int,
        prefer_recipe: uuid.UUID | None,
        swarm_id: str,
        agent_task_id: str | None,
    ) -> tuple[BreakerDecomposition, float, uuid.UUID | None, Any | None]:
        """LLM decomposition through validation plus resolved matching recipe id."""

        prefer = prefer_recipe or matching_recipe_id
        _ = max(3, min(max_steps, 7))

        recipe_hints, chroma_hit = await self._build_recipe_hints(
            db,
            prefer=prefer,
            task_text=task_text,
            enrich_from_chroma_recipes=enrich_from_chroma_recipes,
        )

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

        try:
            raw_content, decomposition_cost_usd = await self._router.decompose(
                db,
                system_prompt=DECOMPOSITION_SYSTEM_PROMPT,
                user_payload=user_json,
                swarm_id=swarm_id,
                task_id=agent_task_id,
            )

            try:
                blob = extract_breaker_json(raw_content)
                ok, reasons = WorkflowValidator.validate_decomposition(blob)
                if not ok:
                    logger.warning("auto_workflow_breaker.preflight_failed", reasons=reasons)
                    raise ValueError(f"Invalid decomposition: {'; '.join(reasons)}")

                draft = BreakerDecomposition.model_validate(blob)
            except (
                ValidationError,
                ValueError,
                json.JSONDecodeError,
                RuntimeError,
            ) as exc:
                logger.warning(
                    "auto_workflow_breaker.fallback_scaffold",
                    error_type=type(exc).__name__,
                    error=str(exc)[:280],
                    swarm_id=swarm_id,
                )
                draft = _breaker_static_fallback(task_text)
                decomposition_cost_usd = 0.0
        except (RuntimeError, BudgetExceededError) as exc:
            logger.warning(
                "auto_workflow_breaker.fallback_scaffold",
                error_type=type(exc).__name__,
                error=str(exc)[:280],
                swarm_id=swarm_id,
            )
            draft = _breaker_static_fallback(task_text)
            decomposition_cost_usd = 0.0
        matched_id = await self._resolve_matching_recipe(
            db,
            task_text=task_text,
            explicit=prefer,
            enrich=enrich_from_chroma_recipes,
        )
        return draft, decomposition_cost_usd, matched_id, chroma_hit

    async def _recipe_match_brief(
        self,
        db: AsyncSession,
        *,
        prefer: uuid.UUID | None,
        chroma_hit: Any | None,
        matched_id: uuid.UUID | None,
    ) -> RecipeMatchBrief | None:
        """Surface explicit, Chroma, or Postgres-resolved recipe metadata."""

        if prefer is not None:
            row = await db.get(RecipeRow, prefer)
            if row is not None:
                return RecipeMatchBrief(name=row.name, similarity=1.0, postgres_recipe_id=row.id)
        if chroma_hit is not None:
            meta = dict(chroma_hit.metadata or {})
            name = meta.get("name") or (str(chroma_hit.document)[:48] if chroma_hit.document else "Recipe")
            rid_raw = meta.get("postgres_recipe_id")
            parsed: uuid.UUID | None = None
            if rid_raw:
                try:
                    parsed = uuid.UUID(str(rid_raw))
                except ValueError:
                    parsed = None
            return RecipeMatchBrief(
                name=str(name),
                similarity=float(chroma_hit.similarity),
                postgres_recipe_id=parsed,
            )
        if matched_id is not None:
            row = await db.get(RecipeRow, matched_id)
            if row is not None:
                return RecipeMatchBrief(name=row.name, similarity=0.92, postgres_recipe_id=row.id)
        return None

    async def preview_decompose(
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
    ) -> PreviewDecompositionResponse:
        """Run the breaker LLM path and return steps without persisting workflow rows."""

        bind_contextvars(
            swarm_id=swarm_id,
            agent_id=None,
            task_id=agent_task_id,
            workflow_id=None,
        )
        prefer = prefer_recipe or matching_recipe_id
        logger.info(
            "auto_workflow_breaker.preview_start",
            task_chars=len(task_text),
            enrich_recipe_chroma=enrich_from_chroma_recipes,
        )
        try:
            draft, cost_usd, matched_id, chroma_hit = await self._run_decomposition_core(
                db,
                task_text=task_text,
                matching_recipe_id=matching_recipe_id,
                enrich_from_chroma_recipes=enrich_from_chroma_recipes,
                max_steps=max_steps,
                prefer_recipe=prefer_recipe,
                swarm_id=swarm_id,
                agent_task_id=agent_task_id,
            )
            recipe_match = await self._recipe_match_brief(
                db,
                prefer=prefer,
                chroma_hit=chroma_hit,
                matched_id=matched_id,
            )
            ordered = sorted(draft.steps, key=lambda step: step.order)
            steps = [
                PreviewWorkflowStep(
                    step_order=step.order,
                    description=step.description,
                    agent_role=step.agent_role,
                    guardrail_summary=_guardrail_summary(step.guardrails),
                    guardrails=step.guardrails,
                    evaluation_criteria=step.evaluation_criteria,
                )
                for step in ordered
            ]
            return PreviewDecompositionResponse(
                steps=steps,
                decomposition_rationale=draft.rationale,
                parallel_groups=list(draft.parallelizable_groups or []),
                estimated_duration_sec=draft.estimated_duration_sec,
                decomposition_cost_usd=float(cost_usd),
                recipe_match=recipe_match,
            )
        except ValidationError:
            raise
        finally:
            clear_contextvars()

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
        logger.info(
            "auto_workflow_breaker.start",
            task_chars=len(task_text),
            enrich_recipe_chroma=enrich_from_chroma_recipes,
        )
        try:
            draft, _, matched_id, _chroma_hit = await self._run_decomposition_core(
                db,
                task_text=task_text,
                matching_recipe_id=matching_recipe_id,
                enrich_from_chroma_recipes=enrich_from_chroma_recipes,
                max_steps=max_steps,
                prefer_recipe=prefer_recipe,
                swarm_id=swarm_id,
                agent_task_id=agent_task_id,
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
