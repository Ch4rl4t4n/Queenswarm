"""Skill Factory session prompt blocks for supervisor sub-agents."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.supervisor.hivemind_verify import load_researcher_draft
from app.infrastructure.persistence.models.supervisor_session import SubAgentSession, SupervisorSession


def is_skill_factory_context(summary: dict) -> bool:
    """True when durable session was seeded for Skill Factory production."""

    if summary.get("skill_factory") is True:
        return True
    raw = str(summary.get("raw_goal") or "").lower()
    return "skill factory" in raw or "skill-factory-ready" in raw


def build_coder_factory_execute_instruction() -> str:
    """Mandatory deliverable format for factory coder sub-agent."""

    return (
        "Execute now. Deliver a **complete sellable SKILL.md** inside one ```markdown fenced block. "
        "Required structure:\n"
        "- YAML frontmatter: name (kebab-case niche slug), description\n"
        "- `# Title` heading\n"
        "- `When to use:` section with guardrails\n"
        "- 3–7 numbered workflow steps (roles + simulate-first)\n"
        "- Optional HARNESS.md excerpt as second fenced block\n"
        "End the message with the tag `skill-factory-ready` on its own line."
    )


def build_critic_factory_execute_instruction() -> str:
    """Mandatory response format for factory critic sub-agent."""

    return (
        "Execute now. Review only the Skill Factory coder draft. Do not return HiveMind findings, "
        "Finding blocks, insight write-backs, or research notes. If the draft satisfies the required "
        "SKILL.md quality bar, end with exactly `Critic verdict: APPROVE` on its own final line. "
        "Otherwise end with exactly `Critic verdict: REJECT` on its own final line."
    )


def build_critic_factory_user_block(*, coder_draft: str) -> str:
    """Extra critic context for Skill Factory quality gate."""

    excerpt = coder_draft.strip()[:12_000]
    return (
        "## Skill Factory — critic gate\n\n"
        "Review the coder draft below for Gumroad-ready SKILL.md quality.\n\n"
        "**Required to APPROVE:**\n"
        "- Valid frontmatter (name, description) — not skill-factory-output\n"
        "- 3+ numbered workflow steps\n"
        "- When to use / guardrails section\n"
        "- Simulate-first discipline\n\n"
        "**Your response MUST end with exactly one line:**\n"
        "`Critic verdict: APPROVE` or `Critic verdict: REJECT`\n\n"
        f"## Coder draft\n{excerpt or '(empty — REJECT)'}"
    )


async def enqueue_next_factory_sub_agent(
    db: AsyncSession,
    *,
    supervisor_session: SupervisorSession,
    completed_sub: SubAgentSession,
) -> int:
    """After each factory sub-agent completes, enqueue the next by spawn_order."""

    from app.application.services.supervisor.session_service import enqueue_durable_sub_agent_step

    if not is_skill_factory_context(dict(supervisor_session.context_summary or {})):
        return 0

    summary = dict(supervisor_session.context_summary or {})
    role = str(completed_sub.role or "").strip().lower()
    if role == "coder":
        summary["factory_coder_draft"] = str(
            (completed_sub.short_memory or {}).get("last_summary") or completed_sub.last_output or "",
        )[:50_000]
        supervisor_session.context_summary = summary

    next_sub = await db.scalar(
        select(SubAgentSession)
        .where(
            SubAgentSession.supervisor_session_id == supervisor_session.id,
            SubAgentSession.spawn_order > int(completed_sub.spawn_order or 0),
            SubAgentSession.status.in_(("pending", "queued")),
        )
        .order_by(SubAgentSession.spawn_order.asc())
        .limit(1),
    )
    if next_sub is None:
        return 0
    await enqueue_durable_sub_agent_step(
        db,
        supervisor_session=supervisor_session,
        sub_agent=next_sub,
        reason="skill_factory_chain",
    )
    return 1


def should_enqueue_only_first_factory_sub_agent(context_summary: dict[str, Any] | None) -> bool:
    """Factory durable sessions run sub-agents sequentially so critic sees coder draft."""

    return is_skill_factory_context(dict(context_summary or {}))


async def load_coder_draft_for_factory(
    db: AsyncSession,
    *,
    supervisor_session_id: object,
    summary: dict,
) -> str:
    """Load coder output for factory critic review."""

    cached = str(summary.get("factory_coder_draft") or "").strip()
    if cached:
        return cached

    from sqlalchemy import select

    row = await db.scalar(
        select(SubAgentSession)
        .where(
            SubAgentSession.supervisor_session_id == supervisor_session_id,
            SubAgentSession.role == "coder",
        )
        .order_by(SubAgentSession.spawn_order.asc())
        .limit(1),
    )
    if row is None:
        return await load_researcher_draft(db, supervisor_session_id=supervisor_session_id)  # type: ignore[arg-type]
    memory = dict(row.short_memory or {})
    return str(memory.get("last_summary") or row.last_output or "").strip()


__all__ = [
    "build_coder_factory_execute_instruction",
    "build_critic_factory_execute_instruction",
    "build_critic_factory_user_block",
    "enqueue_next_factory_sub_agent",
    "is_skill_factory_context",
    "load_coder_draft_for_factory",
    "should_enqueue_only_first_factory_sub_agent",
]
