"""Queen Maintainer cost guard — daily run cap, session budget, economy models."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.session_cost_guardian import DEFAULT_SESSION_CAP_USD
from app.core.config import settings
from app.infrastructure.persistence.models.supervisor_session import SupervisorSession

MAINTAINER_LANE_KEY = "queen_maintainer_lane"


def maintainer_session_cap_usd() -> float:
    """Per-session LLM spend ceiling for Maintainer runs."""

    return float(settings.queen_maintainer_session_cap_usd)


def maintainer_daily_run_limit() -> int:
    """Maximum Maintainer supervisor sessions per tenant per UTC day."""

    return max(1, int(settings.queen_maintainer_daily_run_limit))


def maintainer_economy_models() -> dict[str, str]:
    """Cheap model slugs for Maintainer sub-agent roles."""

    return {
        "researcher": settings.queen_maintainer_researcher_model.strip(),
        "coder": settings.queen_maintainer_coder_model.strip(),
        "critic": settings.queen_maintainer_critic_model.strip(),
        "default": settings.queen_maintainer_coder_model.strip(),
    }


def is_maintainer_session(context_summary: dict[str, Any] | None) -> bool:
    """Return True when supervisor context marks a Queen Maintainer lane."""

    if not isinstance(context_summary, dict):
        return False
    return bool(context_summary.get(MAINTAINER_LANE_KEY))


def maintainer_approval_scan_text(*, goal: str, context_summary: dict[str, Any] | None) -> str:
    """Narrow text for keyword guard — exclude curated memory false positives (e.g. 'DROP the claim')."""

    if not is_maintainer_session(context_summary):
        return goal
    if "=== END CONTEXT ===" in goal:
        return goal.split("=== END CONTEXT ===", 1)[-1]
    raw = str((context_summary or {}).get("raw_goal") or "").strip()
    return raw or goal


def maintainer_treats_context_satisfied(*, goal: str, context_summary: dict[str, Any] | None) -> bool:
    """Maintainer runs embed tech-health in goal — do not loop on empty retrieval sections."""

    if not is_maintainer_session(context_summary):
        return False
    tail = maintainer_approval_scan_text(goal=goal, context_summary=context_summary).lower()
    return "tech health score" in tail or "queen maintainer" in tail


def session_cap_from_summary(context_summary: dict[str, Any] | None) -> float:
    """Resolve session cost cap from context or global Maintainer default."""

    if not isinstance(context_summary, dict):
        return maintainer_session_cap_usd()
    raw = context_summary.get("session_cost_cap_usd")
    if isinstance(raw, (int, float)) and raw > 0:
        return float(raw)
    return maintainer_session_cap_usd()


def maintainer_self_heal_max_attempts() -> int:
    """Reduced retry budget for Maintainer to limit LLM hops."""

    return max(1, int(settings.queen_maintainer_self_heal_max_attempts))


def build_maintainer_session_seed(
    *,
    trigger_source: str,
    pre_approved: bool = False,
    proposal_id: str | None = None,
) -> dict[str, object]:
    """Context seed merged into supervisor sessions for Maintainer runs."""

    models = maintainer_economy_models()
    seed: dict[str, object] = {
        MAINTAINER_LANE_KEY: True,
        "maintainer_trigger_source": trigger_source,
        "session_cost_cap_usd": maintainer_session_cap_usd(),
        "session_cost_warn_ratio": float(settings.queen_maintainer_session_warn_ratio),
        "llm_routing_mode_override": settings.queen_maintainer_routing_mode,
        "maintainer_model_overrides": models,
        "maintainer_self_heal_max_attempts": maintainer_self_heal_max_attempts(),
        "execution_studio_codebase_mode": "simulate",
        "codebase_pr_only": True,
        "live_codebase_requires_approval": True,
        "maintainer_budget_policy": {
            "daily_run_limit": maintainer_daily_run_limit(),
            "session_cap_usd": maintainer_session_cap_usd(),
            "routing_mode": settings.queen_maintainer_routing_mode,
            "models": models,
            "simulate_first": True,
            "pr_only": True,
        },
    }
    if pre_approved:
        seed["approval_state"] = "approve"
        seed["maintainer_proposal_pre_approved"] = True
    if proposal_id:
        seed["maintainer_proposal_id"] = proposal_id
    return seed


def append_maintainer_budget_goal_footer(goal: str) -> str:
    """Append operator-facing cost guardrails to Maintainer goal text."""

    models = maintainer_economy_models()
    return (
        f"{goal.rstrip()}\n\n"
        "--- Maintainer budget policy (mandatory) ---\n"
        f"- Session LLM cap: ${maintainer_session_cap_usd():.2f} — stop and return plan if exceeded.\n"
        f"- Routing: {settings.queen_maintainer_routing_mode} models only "
        f"(researcher={models['researcher']}, coder={models['coder']}, critic={models['critic']}).\n"
        "- Execution mode: simulate-first; open GitHub PR only after simulation passes.\n"
        "- PR-only on branch queen-maintainer/* — never merge to main.\n"
        "- Denylist enforced — no .env*, billing, prod compose, config.py.\n"
        "- Max self-heal attempts: "
        f"{maintainer_self_heal_max_attempts()}.\n"
        "- Operator merges PR in Cursor IDE after review.\n"
    )


async def count_maintainer_runs_today(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
) -> int:
    """Count Maintainer supervisor sessions started today (UTC) for tenant."""

    start_of_day = datetime.now(tz=UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    stmt = (
        select(func.count())
        .select_from(SupervisorSession)
        .where(
            SupervisorSession.tenant_id == tenant_id,
            SupervisorSession.created_at >= start_of_day,
            SupervisorSession.context_summary[MAINTAINER_LANE_KEY].as_boolean().is_(True),
        )
    )
    return int(await db.scalar(stmt) or 0)


async def maintainer_run_precheck(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID | None,
) -> dict[str, Any]:
    """Validate Maintainer can run under daily budget before queueing session."""

    if not settings.queen_maintainer_enabled:
        return {"ok": False, "error": "queen_maintainer_disabled"}
    if tenant_id is None:
        return {"ok": False, "error": "tenant_missing"}

    runs_today = await count_maintainer_runs_today(db, tenant_id=tenant_id)
    daily_limit = maintainer_daily_run_limit()
    if runs_today >= daily_limit:
        return {
            "ok": False,
            "error": "daily_limit_reached",
            "runs_today": runs_today,
            "daily_limit": daily_limit,
            "message": (
                f"Queen Maintainer daily limit reached ({runs_today}/{daily_limit}). "
                "Try again tomorrow or approve an existing pending proposal."
            ),
        }

    return {
        "ok": True,
        "runs_today": runs_today,
        "daily_limit": daily_limit,
        "remaining_runs_today": daily_limit - runs_today,
    }


def maintainer_budget_snapshot(*, runs_today: int = 0) -> dict[str, Any]:
    """Static budget config for API/UI."""

    daily_limit = maintainer_daily_run_limit()
    return {
        "session_cap_usd": maintainer_session_cap_usd(),
        "session_warn_ratio": float(settings.queen_maintainer_session_warn_ratio),
        "daily_run_limit": daily_limit,
        "runs_today": runs_today,
        "remaining_runs_today": max(0, daily_limit - runs_today),
        "routing_mode": settings.queen_maintainer_routing_mode,
        "models": maintainer_economy_models(),
        "self_heal_max_attempts": maintainer_self_heal_max_attempts(),
        "simulate_first": True,
        "pr_only": True,
        "cursor_role": "review_only",
    }


__all__ = [
    "MAINTAINER_LANE_KEY",
    "append_maintainer_budget_goal_footer",
    "build_maintainer_session_seed",
    "count_maintainer_runs_today",
    "is_maintainer_session",
    "maintainer_approval_scan_text",
    "maintainer_treats_context_satisfied",
    "maintainer_budget_snapshot",
    "maintainer_daily_run_limit",
    "maintainer_economy_models",
    "maintainer_run_precheck",
    "maintainer_self_heal_max_attempts",
    "maintainer_session_cap_usd",
    "session_cap_from_summary",
]
