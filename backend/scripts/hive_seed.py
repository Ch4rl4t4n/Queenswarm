#!/usr/bin/env python3
"""Bootstrap swarms, bees, and catalog recipes (idempotent)."""

from __future__ import annotations

import asyncio
import datetime as dt
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import select

from app.core.database import async_session
from app.learning.reward_tracker import grant_weighted_pollen
from app.models.agent import Agent
from app.models.enums import AgentRole, AgentStatus, SwarmPurpose, TaskType
from app.models.recipe import Recipe
from app.models.swarm import SubSwarm
from app.models.task import Task
from app.services.agent_catalog import create_agent_record
from app.services.task_ledger import create_task_record


PLAN: list[tuple[str, SwarmPurpose, int, AgentRole]] = [
    ("colony-scout", SwarmPurpose.SCOUT, 8, AgentRole.SCRAPER),
    ("colony-eval", SwarmPurpose.EVAL, 6, AgentRole.EVALUATOR),
    ("colony-sim", SwarmPurpose.SIMULATION, 5, AgentRole.SIMULATOR),
    ("colony-action", SwarmPurpose.ACTION, 10, AgentRole.REPORTER),
]

SEED_RECIPES: list[dict[str, object]] = [
    {
        "name": "CRYPTO_ACKIE",
        "description": "Ackie crypto narrative digest + risk flags",
        "topic_tags": ["crypto", "ackie"],
        "workflow_template": {
            "steps": [
                {"role": "scraper", "description": "Ingest social + on-chain feeds"},
                {"role": "evaluator", "description": "Score sentiment vs hive guardrails"},
                {"role": "simulator", "description": "Docker verify claims before operator reply"},
            ]
        },
    },
    {
        "name": "BLOG_POST",
        "description": "Long-form hive blog with verification loop",
        "topic_tags": ["blog", "seo"],
        "workflow_template": {
            "steps": [
                {"role": "scraper", "description": "Collect reference facts"},
                {"role": "reporter", "description": "Draft markdown + internal links"},
                {"role": "simulator", "description": "Simulate reader cohort reactions"},
            ]
        },
    },
    {
        "name": "INSTAGRAM_POST",
        "description": "Short-form visual caption + compliance",
        "topic_tags": ["social", "instagram"],
        "workflow_template": {
            "steps": [
                {"role": "marketer", "description": "Hook + CTA"},
                {"role": "evaluator", "description": "Brand safety scan"},
            ]
        },
    },
    {
        "name": "YOUTUBE_DIGEST",
        "description": "Hourly YouTube crypto sentiment rollup (mock data until API key)",
        "topic_tags": ["youtube", "crypto"],
        "workflow_template": {
            "steps": [
                {"role": "scraper", "description": "Pull trending crypto clips (mock JSON if no key)"},
                {"role": "evaluator", "description": "Sentiment + volatility tags"},
                {"role": "reporter", "description": "Ops-facing digest"},
            ]
        },
    },
]


async def _ensure_swarm(session, name: str, purpose: SwarmPurpose) -> tuple[SubSwarm, bool]:
    existing = await session.scalar(select(SubSwarm).where(SubSwarm.name == name))
    if existing:
        return existing, False
    row = SubSwarm(
        name=name,
        purpose=purpose,
        local_memory={"seeded": True},
        is_active=True,
    )
    session.add(row)
    await session.flush()
    return row, True


async def _seed_agents_for_swarm(
    session,
    swarm: SubSwarm,
    count: int,
    role: AgentRole,
) -> int:
    inserted = 0
    base = swarm.name.replace("colony-", "")
    for idx in range(1, count + 1):
        name = f"qsw-{base}-bee-{idx:02d}"
        exists = await session.scalar(select(Agent).where(Agent.name == name))
        if exists:
            continue
        await create_agent_record(
            session,
            name=name,
            role=role,
            status=AgentStatus.IDLE,
            swarm_id=swarm.id,
            config={"seed_profile": base, "slot": idx},
        )
        inserted += 1
    await session.flush()
    return inserted


async def _ensure_recipes(session) -> int:
    added = 0
    verified = dt.datetime.now(tz=dt.UTC)
    for body in SEED_RECIPES:
        exists = await session.scalar(select(Recipe).where(Recipe.name == str(body["name"])))
        if exists:
            continue
        session.add(
            Recipe(
                name=str(body["name"]),
                description=str(body["description"]),
                topic_tags=list(body["topic_tags"]),  # type: ignore[arg-type]
                workflow_template=dict(body["workflow_template"]),  # type: ignore[arg-type]
                verified_at=verified,
            ),
        )
        added += 1
    await session.flush()
    return added


async def seed_hive() -> dict[str, int]:
    """Insert bootstrap rows."""

    stats = {"swarms_new": 0, "agents_new": 0, "recipes_new": 0, "tasks_new": 0}
    async with async_session() as session:
        for name, purpose, count, role in PLAN:
            swarm, created_swarm = await _ensure_swarm(session, name, purpose)
            if created_swarm:
                stats["swarms_new"] += 1
            stats["agents_new"] += await _seed_agents_for_swarm(session, swarm, count, role)

        stats["recipes_new"] = await _ensure_recipes(session)

        scout = await session.scalar(select(SubSwarm).where(SubSwarm.name == "colony-scout"))
        if scout is not None:
            title = "YouTube crypto sentiment — scheduled ingest (mock)"
            exists_task = await session.scalar(select(Task).where(Task.title == title))
            if exists_task is None:
                await create_task_record(
                    session,
                    title=title,
                    task_type_value=TaskType.SCRAPE,
                    priority=3,
                    payload={"source": "youtube", "topic": "crypto", "mode": "mock_if_no_key"},
                    swarm_id=scout.id,
                    workflow_id=None,
                    parent_task_id=None,
                )
                stats["tasks_new"] += 1

            first_bee = await session.scalar(
                select(Agent).where(Agent.swarm_id == scout.id).order_by(Agent.name).limit(1),
            )
            if first_bee is not None and float(first_bee.pollen_points or 0.0) < 0.05:
                await grant_weighted_pollen(
                    session,
                    allocations={first_bee.id: 2.5},
                    task_id=None,
                    reason="Hive seed celebration grant",
                )

        await session.commit()
    return stats


def main() -> None:
    stats = asyncio.run(seed_hive())
    print(f"hive_seed_complete {stats}")


if __name__ == "__main__":
    main()
