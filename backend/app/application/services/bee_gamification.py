"""Bee gamification — verified-workflow badges derived from pollen + performance."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any, Literal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.verified_pollen_leaderboard import fetch_verified_pollen_leaderboard
from app.core.config import settings
from app.infrastructure.persistence.models.agent import Agent
from app.infrastructure.persistence.models.enums import TaskStatus
from app.infrastructure.persistence.models.task import Task

BadgeTier = Literal["bronze", "silver", "gold", "special"]


@dataclass(frozen=True, slots=True)
class BadgeDefinition:
    """One earnable hive badge."""

    id: str
    label: str
    description: str
    tier: BadgeTier
    emoji: str


BADGE_CATALOG: tuple[BadgeDefinition, ...] = (
    BadgeDefinition(
        id="verified_rookie",
        label="Verified Rookie",
        description="Earned first simulation-verified pollen.",
        tier="bronze",
        emoji="🐝",
    ),
    BadgeDefinition(
        id="pollen_bronze",
        label="Bronze Forager",
        description="10+ verified pollen from gated workflows.",
        tier="bronze",
        emoji="🥉",
    ),
    BadgeDefinition(
        id="pollen_silver",
        label="Silver Scout",
        description="50+ verified pollen — consistent verified output.",
        tier="silver",
        emoji="🥈",
    ),
    BadgeDefinition(
        id="pollen_gold",
        label="Gold Queen's Guard",
        description="100+ verified pollen — top-tier hive contributor.",
        tier="gold",
        emoji="🥇",
    ),
    BadgeDefinition(
        id="hive_ace",
        label="Hive Ace",
        description="Performance score ≥ 85% with verified rewards.",
        tier="special",
        emoji="⚡",
    ),
    BadgeDefinition(
        id="imitation_star",
        label="Imitation Star",
        description="High performance + verified pollen — neighbors copy this bee.",
        tier="special",
        emoji="✨",
    ),
    BadgeDefinition(
        id="recipe_keeper",
        label="Recipe Keeper",
        description="Curates verified workflows for the Recipe Library.",
        tier="special",
        emoji="📜",
    ),
    BadgeDefinition(
        id="rapid_loop",
        label="Rapid Loop",
        description="5+ verified tasks — rapid learning loop champion.",
        tier="special",
        emoji="🔄",
    ),
)

_CATALOG_BY_ID = {b.id: b for b in BADGE_CATALOG}


def bee_gamification_enabled() -> bool:
    """Return whether badge surfaces are active."""

    return bool(settings.bee_gamification_enabled)


def list_badge_catalog() -> list[dict[str, str]]:
    """Static badge catalog for UI tooltips."""

    return [
        {
            "id": b.id,
            "label": b.label,
            "description": b.description,
            "tier": b.tier,
            "emoji": b.emoji,
        }
        for b in BADGE_CATALOG
    ]


def compute_agent_badges(
    *,
    agent_role: str,
    verified_pollen: float,
    total_pollen: float,
    performance_score: float,
    verified_task_count: int,
) -> list[dict[str, str]]:
    """Evaluate which badges one bee has earned."""

    earned: list[dict[str, str]] = []
    role = agent_role.strip().lower()

    def _append(badge_id: str) -> None:
        spec = _CATALOG_BY_ID.get(badge_id)
        if spec is None:
            return
        earned.append(
            {
                "id": spec.id,
                "label": spec.label,
                "description": spec.description,
                "tier": spec.tier,
                "emoji": spec.emoji,
            },
        )

    if verified_pollen >= 0.1 or verified_task_count >= 1:
        _append("verified_rookie")
    if verified_pollen >= 10.0:
        _append("pollen_bronze")
    if verified_pollen >= 50.0:
        _append("pollen_silver")
    if verified_pollen >= 100.0:
        _append("pollen_gold")
    if performance_score >= 0.85 and verified_pollen >= 1.0:
        _append("hive_ace")
    if performance_score >= 0.9 and verified_pollen >= 5.0:
        _append("imitation_star")
    if role in {"recipe_keeper", "learner"} and verified_pollen >= 3.0:
        _append("recipe_keeper")
    if verified_task_count >= 5:
        _append("rapid_loop")

    return earned


async def _verified_task_counts(session: AsyncSession, agent_ids: list[uuid.UUID]) -> dict[uuid.UUID, int]:
    if not agent_ids:
        return {}
    exec_result = await session.execute(
        select(Task.agent_id, func.count(Task.id))
        .where(
            Task.agent_id.in_(agent_ids),
            Task.status == TaskStatus.COMPLETED,
            Task.pollen_awarded > 0.0,
        )
        .group_by(Task.agent_id),
    )
    out: dict[uuid.UUID, int] = {}
    for agent_id, count in exec_result.all():
        if agent_id is not None:
            out[agent_id] = int(count or 0)
    return out


async def build_bee_badge_profiles(
    session: AsyncSession,
    *,
    limit: int = 16,
) -> list[dict[str, Any]]:
    """Build ranked bee profiles with earned badges."""

    leaderboard = await fetch_verified_pollen_leaderboard(session, limit=max(limit, 32))
    verified_map: dict[str, float] = {str(row["agent_id"]): float(row["verified_pollen"]) for row in leaderboard}

    exec_result = await session.execute(
        select(Agent).order_by(Agent.pollen_points.desc()).limit(max(limit * 2, 32)),
    )
    agents = list(exec_result.scalars().all())
    if not agents:
        return []

    agent_ids = [a.id for a in agents]
    task_counts = await _verified_task_counts(session, agent_ids)

    profiles: list[dict[str, Any]] = []
    for agent in agents:
        aid = str(agent.id)
        verified = verified_map.get(aid, 0.0)
        vtasks = task_counts.get(agent.id, 0)
        badges = compute_agent_badges(
            agent_role=agent.role.value,
            verified_pollen=verified,
            total_pollen=float(agent.pollen_points or 0.0),
            performance_score=float(agent.performance_score or 0.0),
            verified_task_count=vtasks,
        )
        if not badges and verified <= 0 and vtasks == 0:
            continue
        profiles.append(
            {
                "agent_id": aid,
                "agent_name": agent.name,
                "agent_role": agent.role.value,
                "swarm_id": str(agent.swarm_id) if agent.swarm_id else None,
                "verified_pollen": round(verified, 2),
                "total_pollen": round(float(agent.pollen_points or 0.0), 2),
                "performance_pct": int(round(min(1.0, max(0.0, float(agent.performance_score or 0.0))) * 100)),
                "verified_task_count": vtasks,
                "badges": badges,
                "badge_count": len(badges),
            },
        )

    profiles.sort(
        key=lambda row: (row["badge_count"], row["verified_pollen"], row["total_pollen"]),
        reverse=True,
    )
    return profiles[:limit]


__all__ = [
    "BADGE_CATALOG",
    "bee_gamification_enabled",
    "build_bee_badge_profiles",
    "compute_agent_badges",
    "list_badge_catalog",
]
