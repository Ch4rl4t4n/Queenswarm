"""Skill Factory session prompt blocks for supervisor sub-agents."""

from __future__ import annotations

from app.application.services.supervisor.hivemind_verify import load_researcher_draft
from app.infrastructure.persistence.models.supervisor_session import SupervisorSession
from sqlalchemy.ext.asyncio import AsyncSession


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

    from app.infrastructure.persistence.models.supervisor_session import SubAgentSession

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
    "build_critic_factory_user_block",
    "is_skill_factory_context",
    "load_coder_draft_for_factory",
]
