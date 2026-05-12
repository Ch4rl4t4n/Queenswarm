#!/usr/bin/env python3
"""Ensure at least one :class:`~app.models.agent_config.AgentConfig` row exists for smoke tests."""

from __future__ import annotations

import asyncio

from sqlalchemy import select

from app.core.database import async_session
from app.models import load_all_models
from app.models.agent import Agent
from app.models.agent_config import AgentConfig


async def main() -> None:
    """Attach a crypto-analyst template to the first agent that lacks configuration."""

    load_all_models()
    async with async_session() as session:
        agents = list((await session.execute(select(Agent).order_by(Agent.name))).scalars().all())
        if not agents:
            print("NO_AGENTS")
            return

        configured_ids = set(
            (await session.execute(select(AgentConfig.agent_id))).scalars().all(),
        )
        target = next((a for a in agents if a.id not in configured_ids), agents[0])

        existing = await session.scalar(select(AgentConfig).where(AgentConfig.agent_id == target.id))
        if existing is not None:
            print(f"CONFIG_EXISTS {target.name} {target.id}")
            return

        session.add(
            AgentConfig(
                agent_id=target.id,
                system_prompt="You are a crypto market analyst. Be concise and data-driven.",
                user_prompt_template=(
                    "Search for latest headlines about Bitcoin. Give: "
                    "1) sentiment (bull/bear/neutral) 2) top 3 bullets 3) one-sentence outlook."
                ),
                tools=["web_search"],
                output_format="markdown",
                output_destination="dashboard",
                output_config={},
                schedule_type="on_demand",
                schedule_value=None,
                is_active=True,
            )
        )
        await session.commit()
        print(f"SEEDED_CONFIG {target.name} {target.id}")


if __name__ == "__main__":
    asyncio.run(main())
