"""Content Pack Factory session prompt blocks for supervisor sub-agents."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.persistence.models.supervisor_session import SubAgentSession, SupervisorSession


def is_content_pack_factory_context(summary: dict[str, Any] | None) -> bool:
    """Return True when a durable session was seeded for Content Pack Factory production."""

    context = dict(summary or {})
    if context.get("content_pack_factory") is True:
        return True
    raw = str(context.get("raw_goal") or "").lower()
    return "content pack factory" in raw or "content-pack-factory-ready" in raw


def resolve_content_pack_system_prompt(role: str) -> str:
    """Return a role-specific system prompt for sellable content pack production."""

    key = role.strip().lower()
    if key == "critic":
        return (
            "You are the Content Pack Factory Critic Bee.\n\n"
            "ROLE: review the coder's publish_pack and LISTING.md for sellable quality.\n"
            "INPUTS: session goal, coder draft, niche rationale, and quality gate.\n"
            "OUTPUT CONTRACT: concise markdown review ending with exactly one line: "
            "`Critic verdict: APPROVE` or `Critic verdict: REJECT`.\n"
            "GUARDRAILS: simulate-first only, no secrets, no fabricated proof, reject missing JSON."
        )
    if key == "coder":
        return (
            "You are the Content Pack Factory Coder Bee.\n\n"
            "ROLE: produce the actual buyer-facing social content pack artifact.\n"
            "INPUTS: niche, title, rationale, skills, retrieved context, and researcher notes.\n"
            "OUTPUT CONTRACT: one valid publish_pack JSON block plus one LISTING.md markdown block.\n"
            "GUARDRAILS: artifact_type=publish_pack, simulate_only=true, no live publishing, no secrets."
        )
    return (
        "You are the Content Pack Factory Research Bee.\n\n"
        "ROLE: turn the niche rationale into a buyer persona, channel angle, and practical content strategy.\n"
        "OUTPUT CONTRACT: concise markdown research brief for the coder; include sources where available.\n"
        "GUARDRAILS: simulate-first only, no unsupported market claims, no secrets."
    )


def build_content_pack_coder_execute_instruction() -> str:
    """Mandatory deliverable format for Content Pack Factory coder sub-agent."""

    return (
        "Execute now. Produce a Gumroad-ready content pack, not an audit or HiveMind finding.\n\n"
        "Required output:\n"
        "1. A fenced ```json block containing exactly one publish_pack artifact with:\n"
        "   - format, artifact_type=`publish_pack`, channel, title, body\n"
        "   - hashtags, cta, simulate_only=true\n"
        "   - 3+ snippets, each with text, cta, and hashtags\n"
        "2. A fenced ```markdown block starting with `# LISTING.md` containing Gumroad paste-ready copy:\n"
        "   - title, hook, target buyer, what's included, tags, and price anchor\n\n"
        "Do not return HiveMind finding blocks. End the message with `content-pack-factory-ready` on its own line."
    )


def build_content_pack_critic_user_block(*, coder_draft: str) -> str:
    """Extra critic context for Content Pack Factory quality gate."""

    excerpt = coder_draft.strip()[:12_000]
    return (
        "## Content Pack Factory — critic gate\n\n"
        "Review the coder draft below for sellable publish_pack quality.\n\n"
        "**Required to APPROVE:**\n"
        "- Valid publish_pack JSON with artifact_type=publish_pack\n"
        "- simulate_only=true\n"
        "- title, body, hashtags, cta\n"
        "- 3+ snippets with text, cta, and hashtags\n"
        "- LISTING.md copy suitable for Gumroad\n"
        "- No secret-shaped tokens or live publish actions\n\n"
        "**Your response MUST end with exactly one line:**\n"
        "`Critic verdict: APPROVE` or `Critic verdict: REJECT`\n\n"
        f"## Coder draft\n{excerpt or '(empty — REJECT)'}"
    )


async def load_content_pack_coder_draft(
    db: AsyncSession,
    *,
    supervisor_session_id: object,
    summary: dict[str, Any],
) -> str:
    """Load coder output for Content Pack Factory critic review."""

    cached = str(summary.get("content_pack_coder_draft") or "").strip()
    if cached:
        return cached

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
        return ""
    memory = dict(row.short_memory or {})
    return str(memory.get("last_summary") or row.last_output or "").strip()


async def enqueue_next_content_pack_sub_agent(
    db: AsyncSession,
    *,
    supervisor_session: SupervisorSession,
    completed_sub: SubAgentSession,
) -> int:
    """After each Content Pack Factory sub-agent completes, enqueue the next step."""

    if not is_content_pack_factory_context(dict(supervisor_session.context_summary or {})):
        return 0

    summary = dict(supervisor_session.context_summary or {})
    role = str(completed_sub.role or "").strip().lower()
    if role == "coder":
        summary["content_pack_coder_draft"] = str(
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

    from app.application.services.supervisor.session_service import enqueue_durable_sub_agent_step

    await enqueue_durable_sub_agent_step(
        db,
        supervisor_session=supervisor_session,
        sub_agent=next_sub,
        reason="content_pack_factory_chain",
    )
    return 1


def should_enqueue_only_first_content_pack_sub_agent(context_summary: dict[str, Any] | None) -> bool:
    """Content Pack Factory durable sessions run sequentially so critic sees coder draft."""

    return is_content_pack_factory_context(context_summary)


__all__ = [
    "build_content_pack_coder_execute_instruction",
    "build_content_pack_critic_user_block",
    "enqueue_next_content_pack_sub_agent",
    "is_content_pack_factory_context",
    "load_content_pack_coder_draft",
    "resolve_content_pack_system_prompt",
    "should_enqueue_only_first_content_pack_sub_agent",
]
