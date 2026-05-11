"""Thin async entrypoint bridging FastAPI sessions into the compiled LangGraph runner."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger
from app.models.recipe import Recipe
from app.models.workflow import Workflow
from app.schemas.sub_swarm import RunWorkflowOnSwarmResponse
from app.services.outcome_verification import (
    assess_internal_step_outputs,
    build_operator_step_summaries,
    maybe_attach_internal_echo,
)
from app.services.recipe_chroma_sync import upsert_recipe_into_chroma_library
from app.services.simulation_ledger import record_swarm_simulation_row
from app.services.sub_swarm.graph import get_compiled_sub_swarm_workflow_runner
from app.services.verified_swarm_rewards import grant_pollen_for_verified_swarm_cycle

logger = get_logger(__name__)


async def run_sub_swarm_workflow_cycle(
    session: AsyncSession,
    *,
    swarm_id: uuid.UUID,
    workflow_id: uuid.UUID,
    task_id: uuid.UUID | None = None,
    payload: dict[str, Any] | None = None,
) -> RunWorkflowOnSwarmResponse:
    """Execute every workflow step through the local hive's agents and waggle feed.

    Args:
        session: Request-scoped Async SQLAlchemy session (caller commits).
        swarm_id: Target sub-swarm hosting the worker bees.
        workflow_id: Persisted Auto Workflow Breaker graph.
        task_id: Optional task lineage for validation + status updates.
        payload: Base JSON forwarded into each step's ``execute_task_cycle`` envelope.

    Returns:
        Structured trace plus per-step summaries for dashboards and audit logs.
    """

    graph = get_compiled_sub_swarm_workflow_runner()
    envelope: dict[str, Any] = {
        "swarm_id": str(swarm_id),
        "workflow_id": str(workflow_id),
        "task_uuid": str(task_id) if task_id else None,
        "payload": dict(payload or {}),
        "traces": [],
        "step_outputs": [],
        "step_manifest": [],
        "global_sync_recommended": False,
    }
    final = await graph.ainvoke(
        envelope,
        config={"configurable": {"session": session}},
    )
    err_code = final.get("error")
    internal = list(final.get("step_outputs") or [])
    verified, vnotes = assess_internal_step_outputs(
        internal,
        threshold=float(settings.reward_threshold_pass),
    )
    operator_rows = build_operator_step_summaries(
        internal,
        verified=verified,
        expose_raw=settings.expose_raw_step_outputs,
    )
    internal_echo = maybe_attach_internal_echo(
        internal,
        expose_raw=settings.expose_raw_step_outputs,
    )
    graph_err = err_code if isinstance(err_code, str) else None
    final_verified = verified and graph_err is None
    final_notes = vnotes if graph_err is None else [*vnotes, f"graph_error={graph_err}"]

    wf_row = await session.get(Workflow, workflow_id)
    recipe_for_wf: Recipe | None = None

    if final_verified:
        await grant_pollen_for_verified_swarm_cycle(
            session,
            internal_step_summaries=internal,
            task_id=task_id,
            swarm_id=swarm_id,
            workflow_id=workflow_id,
            amount_per_agent=float(settings.verified_swarm_pollen_per_bee),
        )

    if (
        wf_row is not None
        and wf_row.matching_recipe_id is not None
        and graph_err is None
    ):
        recipe_for_wf = await session.get(Recipe, wf_row.matching_recipe_id)
        if recipe_for_wf is not None:
            recipe_for_wf.last_used_at = datetime.now(tz=UTC)
            if final_verified:
                recipe_for_wf.success_count = int(recipe_for_wf.success_count) + 1
            else:
                recipe_for_wf.fail_count = int(recipe_for_wf.fail_count) + 1

    await record_swarm_simulation_row(
        session,
        task_id=task_id,
        swarm_id=swarm_id,
        workflow_id=workflow_id,
        internal_step_outputs=internal,
        graph_error=graph_err,
        verification_passed=final_verified,
        verification_notes=final_notes,
    )
    if (
        settings.recipe_chroma_auto_sync_on_verify
        and final_verified
        and graph_err is None
        and recipe_for_wf is not None
    ):
        sync_log = logger.bind(
            swarm_id=str(swarm_id),
            workflow_id=str(workflow_id),
            task_id=str(task_id) if task_id else "",
        )
        try:
            new_emb = await upsert_recipe_into_chroma_library(recipe_for_wf)
            recipe_for_wf.embedding_id = new_emb
        except Exception as exc:
            sync_log.warning(
                "recipe_chroma.sync_failed",
                error_type=type(exc).__name__,
                error=str(exc),
            )

    return RunWorkflowOnSwarmResponse(
        swarm_id=swarm_id,
        workflow_id=workflow_id,
        ok=graph_err is None,
        error_code=graph_err,
        error_detail=final.get("error_detail") if isinstance(final.get("error_detail"), str) else None,
        traces=list(final.get("traces") or []),
        step_summaries=operator_rows,
        internal_step_summaries=internal_echo,
        verification_passed=final_verified,
        verification_notes=final_notes,
        global_sync_recommended=bool(final.get("global_sync_recommended")),
    )


__all__ = ["run_sub_swarm_workflow_cycle"]
