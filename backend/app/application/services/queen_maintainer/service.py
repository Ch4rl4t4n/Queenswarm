"""Queen Maintainer routine bootstrap and supervisor session triggers."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.queen_maintainer.maintainer_guard import (
    append_maintainer_budget_goal_footer,
    build_maintainer_session_seed,
    maintainer_run_precheck,
)
from app.application.services.queen_maintainer.pre_tool_denylist import scan_maintainer_text_for_violations
from app.application.services.queen_maintainer.tech_health import build_tech_health_report
from app.application.services.supervisor.routine_service import (
    compute_next_run_at,
    create_supervisor_routine,
    trigger_supervisor_routine_now,
)
from app.application.services.supervisor.skills import SkillLibrary
from app.core.config import settings
from app.core.logging import get_logger
from app.infrastructure.persistence.models.supervisor_routine import SupervisorRoutine

logger = get_logger(__name__)

MAINTAINER_ROUTINE_KIND = "queen_maintainer"
MAINTAINER_ROUTINE_NAME = "Queen Maintainer — weekly tech health"
MAINTAINER_WEEKLY_INTERVAL_SEC = 7 * 24 * 3600

MAINTAINER_ROLES: list[str] = ["researcher", "coder", "critic"]
MAINTAINER_SKILLS: list[str] = [
    "queen-maintainer",
    "execution-studio",
    "self-review-loop",
    "tdd",
    "multi-step-reasoning",
]


def load_instructions_excerpt(*, max_chars: int = 1200) -> str:
    """Load behavioral instructions excerpt for supervisor goal context."""

    from app.application.services.queen_maintainer.tech_health import resolve_repo_root

    path = resolve_repo_root() / "docs" / "harness" / "QUEEN_MAINTAINER_INSTRUCTIONS.md"
    if not path.is_file():
        return "Follow queen-maintainer skill: PR-only, simulate-first, scoped denylist."
    return path.read_text(encoding="utf-8")[:max_chars].strip()


def build_maintainer_goal(*, tech_health: dict[str, Any] | None = None) -> str:
    """Compose supervisor goal from tech health report + behavioral instructions."""

    report = tech_health or build_tech_health_report()
    signals = report.get("signals") or []
    score = report.get("health_score", 0.0)
    instructions = load_instructions_excerpt(max_chars=800)

    base = (
        "Queen Maintainer weekly run — PR-only codebase health review.\n\n"
        f"Tech health score: {score:.2f}\n"
        f"Signals: {', '.join(signals) if signals else 'none'}\n"
        f"Backend pinned deps: {report.get('backend', {}).get('requirements_pinned_count', 0)}\n"
        f"Frontend deps: {report.get('frontend', {}).get('dependency_count', 0)}\n\n"
        "Deliverables:\n"
        "1. Tracer bullet plan (max 7 steps)\n"
        "2. Minimal safe diff proposal (denylist enforced)\n"
        "3. Test evidence (pytest/vitest paths)\n"
        "4. Open GitHub PR on branch queen-maintainer/* — never merge\n\n"
        f"Behavioral instructions excerpt:\n{instructions}"
    )
    return append_maintainer_budget_goal_footer(base)


def build_post_merge_maintainer_goal(*, merge_meta: dict[str, Any]) -> str:
    """Compose Maintainer goal after a merge to default branch (post-merge trigger)."""

    report = build_tech_health_report()
    base_goal = build_maintainer_goal(tech_health=report)
    kind = str(merge_meta.get("kind") or "post_merge")
    title = str(merge_meta.get("title") or merge_meta.get("commit_message") or "recent merge")
    ref = str(merge_meta.get("base_ref") or merge_meta.get("ref") or "main")
    sha = str(merge_meta.get("merge_commit_sha") or merge_meta.get("head_commit_sha") or "")[:12]
    repo = str(merge_meta.get("repo_full_name") or "repository")

    return (
        f"{base_goal}\n\n"
        "Post-merge trigger context:\n"
        f"- Event: {kind}\n"
        f"- Repository: {repo}\n"
        f"- Target ref: {ref}\n"
        f"- Change: {title}\n"
        f"- Commit: {sha or 'unknown'}\n\n"
        "Focus this run on regression risk from the merge: run tech health diff, "
        "propose tracer-bullet fixes only via PR on queen-maintainer/* branch."
    )


async def ensure_queen_maintainer_routine(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    created_by_subject: str | None,
    enabled: bool = True,
) -> SupervisorRoutine:
    """Create or update tenant Queen Maintainer weekly routine."""

    stmt = select(SupervisorRoutine).where(
        SupervisorRoutine.tenant_id == tenant_id,
        SupervisorRoutine.name == MAINTAINER_ROUTINE_NAME,
    )
    row = await db.scalar(stmt)
    now = datetime.now(tz=UTC)
    goal = build_maintainer_goal()

    if row is None:
        row = await create_supervisor_routine(
            db,
            name=MAINTAINER_ROUTINE_NAME,
            goal_template=goal,
            created_by_subject=created_by_subject,
            schedule_kind="interval",
            interval_seconds=MAINTAINER_WEEKLY_INTERVAL_SEC,
            cron_expr=None,
            runtime_mode="durable",
            roles=list(MAINTAINER_ROLES),
            retrieval_contract="default_v2",
            skills=list(MAINTAINER_SKILLS),
            context_payload={
                "routine_kind": MAINTAINER_ROUTINE_KIND,
                "pr_only": True,
                "self_healing_enabled": True,
                "simulate_first": True,
            },
            tenant_id=tenant_id,
        )
    else:
        row.goal_template = goal
        row.roles = list(MAINTAINER_ROLES)
        row.skills = list(MAINTAINER_SKILLS)
        row.runtime_mode = "durable"
        row.interval_seconds = MAINTAINER_WEEKLY_INTERVAL_SEC
        row.schedule_kind = "interval"
        payload = dict(row.context_payload or {})
        payload.update(
            {
                "routine_kind": MAINTAINER_ROUTINE_KIND,
                "pr_only": True,
                "self_healing_enabled": True,
                "simulate_first": True,
            },
        )
        row.context_payload = payload

    row.is_active = bool(enabled and settings.queen_maintainer_enabled)
    if row.is_active and row.next_run_at is None:
        row.next_run_at = compute_next_run_at(
            now=now,
            schedule_kind="interval",
            interval_seconds=MAINTAINER_WEEKLY_INTERVAL_SEC,
            cron_expr=None,
        )
    await db.flush()

    logger.info(
        "queen_maintainer.routine_ensured",
        agent_id="queen_maintainer",
        swarm_id=str(tenant_id),
        task_id="",
        routine_id=str(row.id),
        active=row.is_active,
    )
    return row


async def queue_maintainer_run(
    db: AsyncSession,
    *,
    routine: SupervisorRoutine,
    trigger_source: str,
    goal_override: str | None = None,
    pre_approved: bool = False,
    proposal_id: str | None = None,
) -> dict[str, Any]:
    """Precheck budget, inject guardrails, and spawn Maintainer supervisor session."""

    precheck = await maintainer_run_precheck(db, tenant_id=routine.tenant_id)
    if not precheck.get("ok"):
        logger.info(
            "queen_maintainer.run_blocked",
            agent_id="queen_maintainer",
            swarm_id=str(routine.tenant_id or ""),
            task_id="",
            reason=str(precheck.get("error") or "blocked"),
        )
        return precheck

    report = build_tech_health_report()
    goal = goal_override or build_maintainer_goal(tech_health=report)
    if goal_override and "Maintainer budget policy" not in goal:
        goal = append_maintainer_budget_goal_footer(goal)

    violations = scan_maintainer_text_for_violations(goal)
    if violations:
        logger.info(
            "queen_maintainer.run_blocked",
            agent_id="queen_maintainer",
            swarm_id=str(routine.tenant_id or ""),
            task_id="",
            reason="pre_tool_denylist",
            violations=violations,
        )
        return {
            "ok": False,
            "error": "pre_tool_denylist",
            "blocked_patterns": violations,
            "message": f"Goal contains blocked patterns: {', '.join(violations)}",
        }

    routine.goal_template = goal
    payload = dict(routine.context_payload or {})
    payload["last_tech_health"] = report
    payload["maintainer_triggered_at"] = datetime.now(tz=UTC).isoformat()
    payload["maintainer_trigger_source"] = trigger_source
    payload["maintainer_session_seed"] = build_maintainer_session_seed(
        trigger_source=trigger_source,
        pre_approved=pre_approved,
        proposal_id=proposal_id,
    )
    routine.context_payload = payload
    await db.flush()

    session_id = await trigger_supervisor_routine_now(db, routine=routine)
    logger.info(
        "queen_maintainer.run_triggered",
        agent_id="queen_maintainer",
        swarm_id=str(routine.tenant_id or ""),
        task_id=str(session_id),
        trigger_source=trigger_source,
    )
    return {
        "ok": True,
        "session_id": str(session_id),
        "routine_id": str(routine.id),
        **precheck,
    }


async def trigger_maintainer_run(
    db: AsyncSession,
    *,
    routine: SupervisorRoutine,
    trigger_source: str = "manual",
    goal_override: str | None = None,
    pre_approved: bool = False,
    proposal_id: str | None = None,
) -> uuid.UUID:
    """Spawn Maintainer session; raises ValueError when daily budget blocks run."""

    result = await queue_maintainer_run(
        db,
        routine=routine,
        trigger_source=trigger_source,
        goal_override=goal_override,
        pre_approved=pre_approved,
        proposal_id=proposal_id,
    )
    if not result.get("ok"):
        msg = str(result.get("message") or result.get("error") or "maintainer_run_blocked")
        raise ValueError(msg)
    return uuid.UUID(str(result["session_id"]))


def is_queen_maintainer_routine(row: SupervisorRoutine) -> bool:
    """Return True when routine payload marks Queen Maintainer kind."""

    payload = dict(row.context_payload or {})
    from app.application.services.solo_operator_four_lanes import FOUR_LANE_PAYLOAD_KEY, FOUR_LANE_IDS

    lane = str(payload.get(FOUR_LANE_PAYLOAD_KEY) or "").strip().lower()
    if lane in FOUR_LANE_IDS:
        return False
    return str(payload.get("routine_kind") or "").strip().lower() == MAINTAINER_ROUTINE_KIND


__all__ = [
    "MAINTAINER_ROUTINE_KIND",
    "MAINTAINER_ROUTINE_NAME",
    "build_maintainer_goal",
    "build_post_merge_maintainer_goal",
    "ensure_queen_maintainer_routine",
    "is_queen_maintainer_routine",
    "load_instructions_excerpt",
    "queue_maintainer_run",
    "trigger_maintainer_run",
]
