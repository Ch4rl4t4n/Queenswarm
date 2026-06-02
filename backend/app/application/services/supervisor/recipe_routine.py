"""Create supervisor routines from verified Recipe Library entries (Automation Ladder L3)."""

from __future__ import annotations

import uuid
from typing import Any, Literal

from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.supervisor.routine_service import (
    RoutineScheduleKind,
    create_supervisor_routine,
)
from app.infrastructure.persistence.models.recipe import Recipe

AGENT_ROLE_TO_SUPERVISOR: dict[str, str] = {
    "scraper": "researcher",
    "evaluator": "critic",
    "reporter": "researcher",
    "simulator": "critic",
    "blog_writer": "designer",
    "writer": "designer",
    "researcher": "researcher",
    "critic": "critic",
    "coder": "coder",
}


def _dedupe_roles(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for role in items:
        norm = role.strip().lower()
        if not norm or norm in seen:
            continue
        seen.add(norm)
        out.append(norm)
    return out


def infer_supervisor_roles_from_recipe(recipe: Recipe) -> list[str]:
    """Map recipe workflow steps to supervisor sub-agent roles."""

    wf = dict(recipe.workflow_template or {})
    steps = wf.get("steps") if isinstance(wf.get("steps"), list) else []
    roles: list[str] = []
    for step in steps:
        if not isinstance(step, dict):
            continue
        agent_role = str(step.get("agent_role") or "").strip().lower()
        mapped = AGENT_ROLE_TO_SUPERVISOR.get(agent_role, "researcher")
        roles.append(mapped)
    if not roles:
        roles = ["researcher", "critic"]
    deduped = _dedupe_roles(roles)
    if "critic" not in deduped:
        deduped.append("critic")
    return deduped[:5]


def build_goal_template_from_recipe(recipe: Recipe) -> str:
    """Compose a durable supervisor goal from recipe metadata."""

    wf = dict(recipe.workflow_template or {})
    description = (recipe.description or wf.get("description") or "").strip()
    steps = wf.get("steps") if isinstance(wf.get("steps"), list) else []
    lines = [
        f"Verified recipe run: {recipe.name}",
        "",
        description or "Execute the verified workflow below with simulate-first guardrails.",
        "",
        "Workflow steps:",
    ]
    for step in steps[:7]:
        if not isinstance(step, dict):
            continue
        order = step.get("order", "?")
        desc = str(step.get("description") or "").strip()
        if desc:
            lines.append(f"- Step {order}: {desc}")
    lines.extend(
        [
            "",
            "Constraints: simulate before live · Critic APPROVE before operator-facing output.",
        ],
    )
    return "\n".join(lines)[:4000]


def suggest_routine_name(recipe: Recipe) -> str:
    """Default routine name from recipe catalog entry."""

    base = recipe.name.strip().lower().replace(" ", "-")[:80]
    return f"recipe-{base}"


async def create_routine_from_recipe(
    db: AsyncSession,
    *,
    recipe: Recipe,
    name: str | None,
    schedule_kind: RoutineScheduleKind,
    interval_seconds: int | None,
    cron_expr: str | None,
    runtime_mode: Literal["inprocess", "durable"],
    enable_webhook: bool,
    created_by_subject: str | None,
    tenant_id: uuid.UUID | None,
) -> tuple[Any, dict[str, object]]:
    """Persist one SupervisorRoutine wired to a verified recipe."""

    from app.application.services.supervisor.routine_webhook import enable_routine_webhook

    roles = infer_supervisor_roles_from_recipe(recipe)
    goal = build_goal_template_from_recipe(recipe)
    skills = [tag.strip().lower() for tag in list(recipe.topic_tags or []) if str(tag).strip()][:8]
    if not skills:
        skills = ["context", "decide", "tdd"]

    context_payload: dict[str, object] = {
        "recipe_id": str(recipe.id),
        "recipe_name": recipe.name,
        "automation_ladder_level": 4 if enable_webhook else 3,
        "source": "recipe_routine",
    }
    if enable_webhook:
        context_payload["watch_mode"] = True

    row = await create_supervisor_routine(
        db,
        name=(name or suggest_routine_name(recipe)).strip(),
        goal_template=goal,
        created_by_subject=created_by_subject,
        schedule_kind="event" if enable_webhook else schedule_kind,
        interval_seconds=interval_seconds,
        cron_expr=cron_expr,
        runtime_mode=runtime_mode,
        roles=roles,
        retrieval_contract="wiki_only",
        skills=skills,
        context_payload=context_payload,
        tenant_id=tenant_id,
    )

    webhook_token: str | None = None
    if enable_webhook:
        webhook_token, row.context_payload = enable_routine_webhook(context_payload=dict(row.context_payload or {}))
        await db.flush()

    meta = {
        "recipe_id": str(recipe.id),
        "roles": roles,
        "webhook_token": webhook_token,
    }
    return row, meta


__all__ = [
    "build_goal_template_from_recipe",
    "create_routine_from_recipe",
    "infer_supervisor_roles_from_recipe",
    "suggest_routine_name",
]
