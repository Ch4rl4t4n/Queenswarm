"""Thin facade over the Phase C :class:`AutoWorkflowBreaker` engine."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.workflow_breaker import DecomposeWorkflowResponse, PreviewDecompositionResponse
from app.workflows.breaker import AutoWorkflowBreaker


class WorkflowBreakerService:
    """Compatibility shim for LangGraph loaders and REST ingress."""

    async def build_workflow_plan(
        self,
        db: AsyncSession,
        *,
        task_text: str,
        matching_recipe_id: uuid.UUID | None = None,
        enrich_from_chroma_recipes: bool = False,
        max_steps: int = 7,
        swarm_id: str | None = None,
        agent_task_id: str | None = None,
    ) -> DecomposeWorkflowResponse:
        """Decompose text into SQL-backed ``Workflow`` + ``WorkflowStep`` rows."""

        breaker = AutoWorkflowBreaker()
        return await breaker.decompose(
            db,
            task_text=task_text,
            matching_recipe_id=matching_recipe_id,
            enrich_from_chroma_recipes=enrich_from_chroma_recipes,
            max_steps=max_steps,
            prefer_recipe=None,
            swarm_id=swarm_id or "",
            agent_task_id=agent_task_id,
        )

    async def preview_workflow_plan(
        self,
        db: AsyncSession,
        *,
        task_text: str,
        matching_recipe_id: uuid.UUID | None = None,
        enrich_from_chroma_recipes: bool = False,
        max_steps: int = 7,
        swarm_id: str | None = None,
        agent_task_id: str | None = None,
    ) -> PreviewDecompositionResponse:
        """Run LLM decomposition and return preview rows without persisting a workflow."""

        breaker = AutoWorkflowBreaker()
        return await breaker.preview_decompose(
            db,
            task_text=task_text,
            matching_recipe_id=matching_recipe_id,
            enrich_from_chroma_recipes=enrich_from_chroma_recipes,
            max_steps=max_steps,
            prefer_recipe=None,
            swarm_id=swarm_id or "",
            agent_task_id=agent_task_id,
        )


__all__ = ["WorkflowBreakerService"]
