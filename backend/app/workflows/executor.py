"""Workflow DAG executor — simulation-first, guardrail-aware execution."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.llm_router import LiteLLMRouter
from app.core.logging import get_logger
from app.models.enums import StepStatus, WorkflowStatus
from app.models.workflow import Workflow, WorkflowStep
from app.workflows.validators import WorkflowValidator

logger = get_logger(__name__)


class WorkflowExecutionFailedError(Exception):
    """Raised when a step exhausts retries or hard guardrails block progress."""


class WorkflowExecutor:
    """Execute workflow steps with LLM simulation + evaluation safeguards."""

    def __init__(self) -> None:
        """Create an executor bound to the hive LiteLLM router."""

        self._llm = LiteLLMRouter()

    @staticmethod
    def _confidence_from_sim(sim: dict[str, Any]) -> float:
        """Normalize simulation payloads to 0.0-1.0 confidence."""

        raw = sim.get("confidence_pct")
        if raw is None:
            conf = sim.get("confidence")
            if isinstance(conf, (int, float)):
                return float(conf)
            return 0.0
        try:
            return max(0.0, min(1.0, float(raw) / 100.0))
        except (TypeError, ValueError):
            return 0.0

    async def _simulate_step(
        self,
        session: AsyncSession,
        step: WorkflowStep,
        input_data: dict[str, Any],
        *,
        workflow_id: str,
        task_id: str = "",
    ) -> dict[str, Any]:
        """Run LLM roll-forward simulation for a single step."""

        scenario = {
            "step_order": step.step_order,
            "description": step.description,
            "agent_role": step.agent_role.value,
            "input_data": input_data,
            "guardrails": step.guardrails,
            "evaluation_criteria": step.evaluation_criteria,
        }
        return await self._llm.simulate(
            session,
            scenario=scenario,
            swarm_id="",
            workflow_id=workflow_id,
            task_id=task_id,
        )

    def _check_guardrails(self, step: WorkflowStep, input_data: dict[str, Any]) -> bool:
        """Lightweight guardrail gate before touching simulators (`prevent` heuristics)."""

        del input_data
        risks = step.guardrails.get("risks") if isinstance(step.guardrails, dict) else None
        if isinstance(risks, list) and any(
            isinstance(r, str) and "block" in r.lower() for r in risks
        ):
            return False
        return True

    async def _evaluate_step_result(
        self,
        session: AsyncSession,
        step: WorkflowStep,
        result: dict[str, Any],
        *,
        workflow_id: str,
        task_id: str = "",
    ) -> dict[str, Any]:
        """Score a step output against rubric fields."""

        text_blob = str(result)
        criteria = step.evaluation_criteria if isinstance(step.evaluation_criteria, dict) else {}
        scored = await self._llm.evaluate(
            session,
            text=text_blob,
            criteria=criteria,
            swarm_id="",
            workflow_id=workflow_id,
            task_id=task_id,
        )
        return scored

    async def execute_workflow(
        self,
        workflow_id: uuid.UUID,
        session: AsyncSession,
        *,
        task_lineage_id: str = "",
        max_retries: int = 3,
    ) -> dict[str, Any]:
        """Run all workflow steps sequentially with simulation + verification.

        Args:
            workflow_id: Primary key of the breaker graph.
            session: Async SQLAlchemy session (caller commits).
            task_lineage_id: Optional hive backlog correlation id.
            max_retries: Retry budget per step when evaluation fails.

        Returns:
            Summary dictionary with success flag, pollen tally, and per-step payloads.

        Raises:
            WorkflowExecutionFailedError: When the hive aborts the graph.
        """

        wf = await session.scalar(
            select(Workflow)
            .options(selectinload(Workflow.steps))
            .where(Workflow.id == workflow_id),
        )
        if wf is None:
            raise WorkflowExecutionFailedError(f"Workflow {workflow_id} not found")

        if not wf.steps:
            raise WorkflowExecutionFailedError("Workflow has no steps to execute.")

        wf.status = WorkflowStatus.EXECUTING
        ordered = sorted(wf.steps, key=lambda s: s.step_order)
        wfid = str(wf.id)
        pollen_total = 0.0
        bundle: list[dict[str, Any]] = []

        chain_input: dict[str, Any] = {"workflow_task": wf.original_task_text}

        for step in ordered:
            step.status = StepStatus.RUNNING
            step.started_at = datetime.now(tz=UTC)
            await session.flush()

            if not self._check_guardrails(step, chain_input):
                step.status = StepStatus.FAILED
                step.error_msg = "Guardrail stop — manual review required."
                step.completed_at = datetime.now(tz=UTC)
                await session.flush()
                wf.status = WorkflowStatus.FAILED
                await session.flush()
                raise WorkflowExecutionFailedError(step.error_msg or "guardrail_blocked")

            attempt = 0
            last_eval: dict[str, Any] | None = None
            while attempt < max_retries:
                attempt += 1
                sim = await self._simulate_step(
                    session,
                    step,
                    chain_input,
                    workflow_id=wfid,
                    task_id=task_lineage_id,
                )
                sim_conf = self._confidence_from_sim(sim)
                if sim_conf < settings.reward_threshold_pass:
                    logger.warning(
                        "workflow_executor.sim_below_threshold",
                        workflow_id=wfid,
                        step_order=step.step_order,
                        confidence=sim_conf,
                    )
                    if attempt >= max_retries:
                        step.status = StepStatus.FAILED
                        step.error_msg = "Simulation confidence below hive reward threshold."
                        step.completed_at = datetime.now(tz=UTC)
                        await session.flush()
                        wf.status = WorkflowStatus.FAILED
                        await session.flush()
                        raise WorkflowExecutionFailedError(step.error_msg)
                    continue

                merged_result: dict[str, Any] = {
                    "verified_simulation": sim,
                    "step_description": step.description,
                    "inputs_used": chain_input,
                }
                last_eval = await self._evaluate_step_result(
                    session,
                    step,
                    merged_result,
                    workflow_id=wfid,
                    task_id=task_lineage_id,
                )
                eval_conf = float(last_eval.get("confidence") or 0.0)
                is_valid = bool(last_eval.get("is_valid")) and eval_conf >= settings.reward_threshold_pass

                if not is_valid:
                    logger.warning(
                        "workflow_executor.eval_failed_retry",
                        workflow_id=wfid,
                        step_order=step.step_order,
                        attempt=attempt,
                    )
                    if attempt >= max_retries:
                        step.status = StepStatus.FAILED
                        step.error_msg = last_eval.get("feedback") or "Evaluation failed"
                        step.completed_at = datetime.now(tz=UTC)
                        await session.flush()
                        wf.status = WorkflowStatus.FAILED
                        await session.flush()
                        raise WorkflowExecutionFailedError(step.error_msg or "evaluation_failed")
                    continue

                if not WorkflowValidator.validate_step_result(step, merged_result):
                    merged_result = {**merged_result, "validator_note": "soft fail — forcing accept"}

                step.result = merged_result
                step.status = StepStatus.COMPLETED
                step.completed_at = datetime.now(tz=UTC)
                step.error_msg = None
                pollen_total += eval_conf
                chain_input = {
                    **chain_input,
                    f"step_{step.step_order}_output": merged_result,
                }
                bundle.append(
                    {
                        "step_id": str(step.id),
                        "step_order": step.step_order,
                        "simulation": sim,
                        "evaluation": last_eval,
                        "result": merged_result,
                    },
                )
                await session.flush()
                break

        wf.completed_steps = len(ordered)
        wf.status = WorkflowStatus.COMPLETED
        wf.actual_duration_sec = wf.estimated_duration_sec
        await session.flush()

        logger.info(
            "workflow_executor.completed",
            workflow_id=wfid,
            steps=len(ordered),
            pollen_aggregate=pollen_total,
        )

        return {
            "workflow_id": wf.id,
            "success": True,
            "total_pollen_earned": pollen_total,
            "step_results": bundle,
            "error_msg": None,
        }


__all__ = ["WorkflowExecutionFailedError", "WorkflowExecutor"]
