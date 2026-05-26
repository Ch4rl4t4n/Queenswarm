"""Bootstrap helper for the Sentinel ``Upgrade Backlog`` daily routine.

Idempotently registers a ``SupervisorRoutine`` that runs every day at
07:30 UTC. The routine asks the Sentinel manager to scan forager
intelligence + active research signals and produce **three** concrete
upgrade proposals (new MCP, new model, deprecated dependency, etc.),
then stage them as a Notion page via ``mcp_invoke`` in simulate mode.

The operator approves / rejects each proposal in the Notion review.

Per-routine guardrails:
- ``runtime_mode = "durable"`` so multi-step research+draft chains can run
  without HTTP timeouts.
- ``roles = ["researcher", "critic"]`` — research surfaces signal, critic
  filters obvious noise.
- ``skills = ["execution-studio", "context"]`` — simulate-first by default.

Returns the routine id (new or existing).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.supervisor.routine_service import create_supervisor_routine
from app.core.logging import get_logger
from app.infrastructure.persistence.models.supervisor_routine import SupervisorRoutine

logger = get_logger(__name__)

ROUTINE_NAME = "Sentinel · Upgrade Backlog"

GOAL_TEMPLATE = """\
Sentinel sweep — produce a daily Upgrade Backlog for the operator.

Scan the last 24 hours of forager intelligence, GitHub release feeds, and any
HiveMind notes tagged `upgrade-candidate`. Produce EXACTLY THREE proposals:

For each proposal include:
- title (5–9 words)
- type (one of: new_mcp · new_model · new_library · deprecated · cost_saver)
- rationale (2 sentences, evidence-led)
- expected_impact (low / medium / high)
- effort_estimate_hours (integer)
- evidence_link (URL or HiveMind node id)
- risk (1 sentence)

Stage the result as a Notion page titled "Queenswarm Upgrade Backlog — YYYY-MM-DD"
via mcp_invoke in **simulate mode only**. Do NOT publish live.

Output operator_reply in Slovak summarizing the three picks in 3 short bullets.
""".strip()


async def ensure_sentinel_upgrade_routine(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    created_by_subject: str | None = None,
) -> dict[str, object]:
    """Create the routine if it doesn't exist for this tenant; return summary."""

    existing_stmt = (
        select(SupervisorRoutine)
        .where(SupervisorRoutine.tenant_id == tenant_id)
        .where(SupervisorRoutine.name == ROUTINE_NAME)
        .limit(1)
    )
    existing = (await db.scalars(existing_stmt)).first()
    if existing is not None:
        logger.info(
            "sentinel_upgrade_backlog.exists",
            agent_id="sentinel_bootstrap",
            swarm_id="",
            task_id=str(existing.id),
            tenant_id=str(tenant_id),
        )
        return {
            "status": "exists",
            "routine_id": str(existing.id),
            "next_run_at": existing.next_run_at.isoformat() if existing.next_run_at else None,
        }

    row = await create_supervisor_routine(
        db,
        name=ROUTINE_NAME,
        goal_template=GOAL_TEMPLATE,
        tenant_id=tenant_id,
        created_by_subject=created_by_subject,
        schedule_kind="cron",
        interval_seconds=None,
        cron_expr="30 7 * * *",  # daily 07:30 UTC
        runtime_mode="durable",
        roles=["researcher", "critic"],
        retrieval_contract="upgrade_signals_last_24h",
        skills=["execution-studio", "context"],
        context_payload={
            "feature_flag": "sentinel_upgrade_backlog",
            "simulate_only": True,
            "max_proposals": 3,
            "deliverable": "notion_page_simulate",
        },
    )
    await db.flush()
    logger.info(
        "sentinel_upgrade_backlog.created",
        agent_id="sentinel_bootstrap",
        swarm_id="",
        task_id=str(row.id),
        tenant_id=str(tenant_id),
    )
    return {
        "status": "created",
        "routine_id": str(row.id),
        "next_run_at": row.next_run_at.isoformat() if row.next_run_at else None,
        "schedule": "cron 30 7 * * *",
        "created_at": datetime.now(tz=UTC).isoformat(),
    }


__all__ = ["GOAL_TEMPLATE", "ROUTINE_NAME", "ensure_sentinel_upgrade_routine"]
