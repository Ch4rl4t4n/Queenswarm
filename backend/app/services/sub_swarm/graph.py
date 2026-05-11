"""LangGraph subgraph wiring sub-swarms to decomposed workflow steps."""

from __future__ import annotations

import uuid
from typing import Any, cast

from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.agents.cost_governor import BudgetExceededError
from app.agents.factory import instantiate_agent
from app.core.logging import get_logger
from app.models.enums import StepStatus, TaskStatus, WorkflowStatus
from app.models.swarm import SubSwarm
from app.models.task import Task
from app.models.workflow import Workflow
from app.services.sub_swarm.plan import plan_execution_batches
from app.services.sub_swarm.selection import pick_agent_for_step
from app.services.sub_swarm.state import SubSwarmWorkflowState
from app.services.waggle_dance import broadcast_waggle_dance

logger = get_logger(__name__)

_compiled_sub_swarm_runner: CompiledStateGraph | None = None


def _append_trace(message: str) -> dict[str, Any]:
    """Return a partial state update with a single trace line."""

    return {"traces": [message]}


async def prepare_sub_swarm_context(
    state: SubSwarmWorkflowState,
    config: RunnableConfig,
) -> dict[str, Any]:
    """Load swarm + workflow rows, validate task lineage, and serialize step manifest."""

    sess = config["configurable"].get("session")
    if sess is None:
        return {
            "error": "missing_session",
            "error_detail": "RunnableConfig.configurable.session is required.",
            **_append_trace("prepare.failed: missing_session"),
        }

    swarm_uuid = uuid.UUID(str(state["swarm_id"]))
    workflow_uuid = uuid.UUID(str(state["workflow_id"]))

    swarm_stmt = (
        select(SubSwarm)
        .where(SubSwarm.id == swarm_uuid)
        .options(
            selectinload(SubSwarm.members),
            selectinload(SubSwarm.queen),
        )
    )
    swarm_result = await sess.execute(swarm_stmt)
    swarm = swarm_result.scalar_one_or_none()
    if swarm is None:
        return {
            "error": "swarm_not_found",
            "error_detail": str(swarm_uuid),
            **_append_trace(f"prepare.failed: swarm_not_found {swarm_uuid}"),
        }

    wf_stmt = (
        select(Workflow)
        .where(Workflow.id == workflow_uuid)
        .options(selectinload(Workflow.steps))
    )
    wf_result = await sess.execute(wf_stmt)
    workflow = wf_result.scalar_one_or_none()
    if workflow is None:
        return {
            "error": "workflow_not_found",
            "error_detail": str(workflow_uuid),
            **_append_trace(f"prepare.failed: workflow_not_found {workflow_uuid}"),
        }

    if not swarm.members:
        return {
            "error": "no_agents",
            "error_detail": str(swarm_uuid),
            **_append_trace("prepare.failed: sub_swarm_has_zero_members"),
        }

    task_uuid_raw = state.get("task_uuid")
    if task_uuid_raw:
        task_pk = uuid.UUID(str(task_uuid_raw))
        task_row = await sess.get(Task, task_pk)
        if task_row is None:
            return {
                "error": "task_not_found",
                "error_detail": str(task_pk),
                **_append_trace(f"prepare.failed: task_not_found {task_pk}"),
            }
        if task_row.swarm_id != swarm.id:
            return {
                "error": "task_swarm_mismatch",
                "error_detail": f"task {task_pk} not bound to swarm {swarm_uuid}",
                **_append_trace("prepare.failed: task_swarm_mismatch"),
            }

    ordered_steps = sorted(workflow.steps, key=lambda s: s.step_order)
    manifest: list[dict[str, Any]] = [
        {
            "id": str(step.id),
            "order": step.step_order,
            "agent_role": step.agent_role.value,
            "description": step.description,
        }
        for step in ordered_steps
    ]

    workflow.status = WorkflowStatus.EXECUTING
    await sess.flush()

    ctx_log = logger.bind(
        agent_id="sub_swarm_graph",
        swarm_id=str(swarm.id),
        task_id=str(task_uuid_raw) if task_uuid_raw else "",
    )
    ctx_log.info(
        "sub_swarm_graph.prepare_completed",
        workflow_id=str(workflow.id),
        steps=len(manifest),
    )
    return {
        "step_manifest": manifest,
        "global_sync_recommended": False,
        **_append_trace(f"prepare.ready steps={len(manifest)}"),
    }


async def execute_workflow_steps_on_swarm(
    state: SubSwarmWorkflowState,
    config: RunnableConfig,
) -> dict[str, Any]:
    """Hydrate bees from the factory and run :meth:`execute_task_cycle` per step."""

    err = state.get("error")
    if err:
        return {}

    sess = cast(AsyncSession, config["configurable"]["session"])
    swarm_uuid = uuid.UUID(str(state["swarm_id"]))
    workflow_uuid = uuid.UUID(str(state["workflow_id"]))

    swarm_stmt = (
        select(SubSwarm)
        .where(SubSwarm.id == swarm_uuid)
        .options(
            selectinload(SubSwarm.members),
            selectinload(SubSwarm.queen),
        )
    )
    swarm = (await sess.execute(swarm_stmt)).scalar_one()
    wf_stmt = (
        select(Workflow)
        .where(Workflow.id == workflow_uuid)
        .options(selectinload(Workflow.steps))
    )
    workflow = (await sess.execute(wf_stmt)).scalar_one()

    task_uuid: uuid.UUID | None = None
    if state.get("task_uuid"):
        task_uuid = uuid.UUID(str(state["task_uuid"]))

    ordered_steps = sorted(workflow.steps, key=lambda s: s.step_order)
    try:
        batches = plan_execution_batches(
            ordered_steps=ordered_steps,
            parallel_groups=workflow.parallelizable_groups,
        )
    except ValueError as exc:
        workflow.status = WorkflowStatus.FAILED
        await sess.flush()
        return {
            "error": "invalid_workflow_plan",
            "error_detail": str(exc),
            "step_outputs": [],
            "traces": [f"execute.plan_failed: {exc}"],
        }

    outputs: list[dict[str, Any]] = []
    trace_lines: list[str] = []
    base_payload = dict(state.get("payload") or {})

    for batch_ix, batch in enumerate(batches):
        batch_orders = sorted(int(s.step_order) for s in batch)
        trace_lines.append(f"execute.batch_start ix={batch_ix} orders={batch_orders}")

        batch_log = logger.bind(
            agent_id="sub_swarm_graph",
            swarm_id=str(swarm.id),
            task_id=str(task_uuid) if task_uuid else "",
        )
        batch_log.info(
            "sub_swarm_graph.parallel_batch_ready",
            workflow_id=str(workflow.id),
            batch_index=batch_ix,
            orders=batch_orders,
        )

        for step in sorted(batch, key=lambda s: s.step_order):
            role = step.agent_role
            try:
                agent_row = pick_agent_for_step(
                    swarm.members,
                    queen=swarm.queen,
                    preferred_role=role,
                )
            except ValueError as exc:
                workflow.status = WorkflowStatus.FAILED
                return {
                    "error": "routing_failed",
                    "error_detail": str(exc),
                    "step_outputs": outputs,
                    "traces": trace_lines + [f"execute.routing_failed: {exc}"],
                }

            bee_ctx = logger.bind(
                agent_id=str(agent_row.id),
                swarm_id=str(swarm.id),
                task_id=str(task_uuid) if task_uuid else "",
            )
            bee_ctx.info(
                "sub_swarm_graph.step_start",
                workflow_id=str(workflow.id),
                step_order=step.step_order,
                role=role.value,
            )

            step.status = StepStatus.RUNNING
            await sess.flush()
            bee = instantiate_agent(db=sess, agent_row=agent_row)
            step_payload = {
                **base_payload,
                "step_order": step.step_order,
                "step_description": step.description,
                "guardrails": step.guardrails,
                "evaluation_criteria": step.evaluation_criteria,
            }
            try:
                outcome = await bee.execute_task_cycle(
                    payload=step_payload,
                    task_id=task_uuid,
                    workflow_id=workflow.id,
                    verified_outcome=False,
                    pollen_award_if_verified=0.0,
                )
            except BudgetExceededError as exc:
                step.status = StepStatus.FAILED
                step.error_msg = str(exc)
                workflow.status = WorkflowStatus.FAILED
                await sess.flush()
                outputs.append(
                    {
                        "step_id": str(step.id),
                        "order": step.step_order,
                        "agent_id": str(agent_row.id),
                        "agent_role": role.value,
                        "status": "budget_blocked",
                        "error": str(exc),
                    },
                )
                return {
                    "error": "budget_exceeded",
                    "error_detail": str(exc),
                    "step_outputs": outputs,
                    "traces": trace_lines + ["execute.budget_exceeded"],
                }
            except TimeoutError as exc:
                step.status = StepStatus.FAILED
                step.error_msg = str(exc)
                workflow.status = WorkflowStatus.FAILED
                await sess.flush()
                outputs.append(
                    {
                        "step_id": str(step.id),
                        "order": step.step_order,
                        "agent_id": str(agent_row.id),
                        "agent_role": role.value,
                        "status": "timeout",
                        "error": str(exc),
                    },
                )
                return {
                    "error": "step_timeout",
                    "error_detail": str(exc),
                    "step_outputs": outputs,
                    "traces": trace_lines + ["execute.step_timeout"],
                }
            else:
                step.status = StepStatus.COMPLETED
                step.result = outcome
                workflow.completed_steps += 1
                await sess.flush()
                outputs.append(
                    {
                        "step_id": str(step.id),
                        "order": step.step_order,
                        "agent_id": str(agent_row.id),
                        "agent_role": role.value,
                        "status": "completed",
                        "result": outcome,
                    },
                )
                bee_ctx.info(
                    "sub_swarm_graph.step_completed",
                    workflow_id=str(workflow.id),
                    step_order=step.step_order,
                )

    workflow.status = WorkflowStatus.COMPLETED

    if task_uuid is not None:
        task_row = await sess.get(Task, task_uuid)
        if task_row is not None:
            task_row.status = TaskStatus.COMPLETED
            await sess.flush()

    return {
        "step_outputs": outputs,
        "traces": trace_lines
        + [f"execute.done steps={len(outputs)} batches={len(batches)}"],
    }


async def finalize_waggle_broadcast(
    state: SubSwarmWorkflowState,
    config: RunnableConfig,
) -> dict[str, Any]:
    """Publish telemetry and surface whether a global hive sync is due."""

    swarm_uuid = uuid.UUID(str(state["swarm_id"]))
    workflow_uuid = uuid.UUID(str(state["workflow_id"]))
    task_uuid: uuid.UUID | None = None
    if state.get("task_uuid"):
        task_uuid = uuid.UUID(str(state["task_uuid"]))

    errs = state.get("error")

    sess = cast(AsyncSession, config["configurable"]["session"])

    swarm_stmt = (
        select(SubSwarm)
        .where(SubSwarm.id == swarm_uuid)
        .options(selectinload(SubSwarm.members))
    )
    swarm = (await sess.execute(swarm_stmt)).scalar_one_or_none()

    needs_sync = bool(swarm.needs_sync) if swarm is not None else False

    telemetry: dict[str, Any] = {
        "steps_reported": len(state.get("step_outputs") or []),
        "error": errs,
        "error_detail": state.get("error_detail"),
        "needs_global_sync": needs_sync,
    }

    await broadcast_waggle_dance(
        dance_type="sub_swarm_workflow_pulse",
        swarm_id=swarm_uuid,
        workflow_id=workflow_uuid,
        task_id=task_uuid,
        payload=telemetry,
    )

    suffix = "error" if errs else "ok"
    return {
        "global_sync_recommended": needs_sync,
        **_append_trace(f"waggle.finalized:{suffix} global_sync={needs_sync}"),
    }


def build_sub_swarm_workflow_graph() -> StateGraph:
    """Construct the uncompiled hive routing graph (compile once per process)."""

    graph = StateGraph(SubSwarmWorkflowState)
    graph.add_node("prepare", prepare_sub_swarm_context)
    graph.add_node("execute_steps", execute_workflow_steps_on_swarm)
    graph.add_node("waggle", finalize_waggle_broadcast)
    graph.add_edge(START, "prepare")
    graph.add_edge("prepare", "execute_steps")
    graph.add_edge("execute_steps", "waggle")
    graph.add_edge("waggle", END)
    return graph


def get_compiled_sub_swarm_workflow_runner() -> CompiledStateGraph:
    """Return a process-wide compiled graph for API requests."""

    global _compiled_sub_swarm_runner  # noqa: PLW0603 — singleton cache
    if _compiled_sub_swarm_runner is None:
        _compiled_sub_swarm_runner = build_sub_swarm_workflow_graph().compile()
    return _compiled_sub_swarm_runner


__all__ = [
    "build_sub_swarm_workflow_graph",
    "execute_workflow_steps_on_swarm",
    "finalize_waggle_broadcast",
    "get_compiled_sub_swarm_workflow_runner",
    "prepare_sub_swarm_context",
]
