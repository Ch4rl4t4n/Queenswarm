"""Persist hive Simulation audit rows aligned with swarm outcome gate."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger
from app.models.enums import SimulationResult
from app.models.simulation import Simulation
from app.services.hive_ephemeral_sandbox import run_ephemeral_sandbox_probe
from app.services.outcome_verification import max_simulator_confidence_fraction

logger = get_logger(__name__)


def _clamp_pct(value: float) -> float:
    """Clamp human-facing percent telemetry into ``[0, 100]``."""

    if value < 0.0:
        return 0.0
    if value > 100.0:
        return 100.0
    return value


def _truncate_audit_text(blob: str, max_chars: int) -> str:
    """Truncate Docker log payloads to stay within column budgets."""

    if len(blob) <= max_chars:
        return blob
    return blob[:max_chars]


async def record_swarm_simulation_row(
    session: AsyncSession,
    *,
    task_id: uuid.UUID | None,
    swarm_id: uuid.UUID,
    workflow_id: uuid.UUID,
    internal_step_outputs: list[dict[str, Any]],
    graph_error: str | None,
    verification_passed: bool,
    verification_notes: list[str],
) -> Simulation | None:
    """Insert a simulation audit record when enabled (synthetic until Docker binds)."""

    if not settings.simulation_audit_rows_enabled:
        return None

    peak_frac = max_simulator_confidence_fraction(internal_step_outputs)
    peak_pct = _clamp_pct((peak_frac or 0.0) * 100.0)
    gate_pct = _clamp_pct(float(settings.reward_threshold_pass) * 100.0)

    if graph_error is not None:
        outcome = SimulationResult.FAIL
        confidence_pct = 0.0
    elif verification_passed:
        outcome = SimulationResult.PASS
        confidence_pct = max(peak_pct, gate_pct)
    elif internal_step_outputs:
        outcome = SimulationResult.INCONCLUSIVE
        confidence_pct = peak_pct if peak_pct > 0.0 else 0.0
    else:
        outcome = SimulationResult.FAIL
        confidence_pct = 0.0

    notes_compact = "; ".join(verification_notes)[:8000]

    sandbox = None
    if settings.simulation_docker_execution_enabled:
        sandbox = await run_ephemeral_sandbox_probe(
            swarm_id=swarm_id,
            workflow_id=workflow_id,
            task_id=task_id,
        )
    sandbox_ok = sandbox is not None
    truncate = settings.simulation_docker_log_truncate_chars

    scenario: dict[str, Any] = {
        "kind": "swarm_langgraph_cycle",
        "swarm_id": str(swarm_id),
        "workflow_id": str(workflow_id),
        "step_count": len(internal_step_outputs),
        "graph_error_code": graph_error,
        "docker_probe_attempted": settings.simulation_docker_execution_enabled,
        "docker_probe_succeeded": sandbox_ok,
        "synthetic_audit": (not settings.simulation_docker_execution_enabled) or (not sandbox_ok),
    }

    result_blob: dict[str, Any] = {
        "verification_passed": verification_passed,
        "verification_notes_compact": notes_compact,
        "confidence_peak_fraction": peak_frac,
        "sandbox_container_attached": sandbox_ok,
    }

    docker_id = sandbox.container_id if sandbox else None
    stdout_txt = _truncate_audit_text(sandbox.stdout, truncate) if sandbox else None
    stderr_txt = _truncate_audit_text(sandbox.stderr, truncate) if sandbox else None
    duration_sec = sandbox.duration_sec if sandbox else None

    entity = Simulation(
        task_id=task_id,
        scenario=scenario,
        result_data=result_blob,
        result_type=outcome,
        confidence_pct=confidence_pct,
        docker_container_id=docker_id,
        stdout=stdout_txt,
        stderr=stderr_txt,
        duration_sec=duration_sec,
    )
    session.add(entity)
    await session.flush()

    ctx_log = logger.bind(
        swarm_id=str(swarm_id),
        workflow_id=str(workflow_id),
        task_id=str(task_id) if task_id else "",
    )
    ctx_log.info(
        "simulation_audit.persisted",
        result_type=outcome.value,
        confidence_pct=confidence_pct,
    )
    return entity


__all__ = ["record_swarm_simulation_row"]
