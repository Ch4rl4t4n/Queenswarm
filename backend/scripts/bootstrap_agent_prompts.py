#!/usr/bin/env python3
"""Seed system prompts for the 28 Virtual Company / Sentinel / Life-OS bees.

Idempotent — pulls the canonical prompts from
`app.application.services.agent_prompt_templates.AGENT_PROMPT_REGISTRY`
and writes them into `agent_configs.system_prompt` for every matching agent
in the operator's tenant.

Default behaviour skips agents whose `system_prompt` was already customised by
the operator (i.e., the current value does not match the legacy default
"Use Execution Studio policy ..." family). Use --force to overwrite anyway.

Usage:
    python scripts/bootstrap_agent_prompts.py [--force] [--dry-run]

Examples:
    python scripts/bootstrap_agent_prompts.py
    python scripts/bootstrap_agent_prompts.py --force
    python scripts/bootstrap_agent_prompts.py --dry-run
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sqlalchemy import select  # noqa: E402
from sqlalchemy.orm import selectinload  # noqa: E402

from app.application.services.agent_prompt_templates import AGENT_PROMPT_REGISTRY  # noqa: E402
from app.core.database import async_session  # noqa: E402
from app.infrastructure.persistence.models import load_all_models  # noqa: E402
from app.infrastructure.persistence.models.agent import Agent  # noqa: E402
from app.infrastructure.persistence.models.agent_config import AgentConfig  # noqa: E402
from app.infrastructure.persistence.models.tenant import Tenant  # noqa: E402


# Legacy default substrings — any existing prompt that contains one of these
# is considered "stock" and safe to overwrite without --force.
_LEGACY_DEFAULT_MARKERS: tuple[str, ...] = (
    "Use Execution Studio policy",
    "You are a helpful AI agent.",
    "You are the marketing department manager.",
    "You are the sales pipeline manager.",
    "You are the finance controller — read-only reports only.",
    "You are the digital/e-commerce manager.",
    "You are R&D lead — PR-only workflow.",
    "You are product manager.",
    "You are the sentinel manager.",
    "You are an overnight life-OS supervisor.",
    "Research topics from HiveMind",
    "Turn briefs into blog posts",
    "Stage publish packs in Notion",
    "Discover and enrich leads from HiveMind.",
    "Draft personalized outreach in Gmail simulate mode.",
    "Aggregate figures from HiveMind notes.",
    "Write finance report pages to Notion",
    "Audit flows and document UX findings.",
    "Propose A/B test ideas in Notion simulate mode.",
    "Inspect repo health and GitHub issue drafts",
    "Research mini-app opportunities from HiveMind.",
    "Decompose PRD slices into workflow steps.",
    "Materialize workflow steps as Kanban child tasks.",
    "Run simulation checks and link slices to GitHub simulate.",
    "Scan geopolitical and macro signals.",
    "Track industry trends from HiveMind.",
    "Identify mini-app opportunities.",
    "Ingest folder files and voice notes into hive memory.",
)


def _is_legacy_default(prompt: str | None) -> bool:
    if prompt is None:
        return True
    stripped = prompt.strip()
    if not stripped:
        return True
    return any(marker in stripped for marker in _LEGACY_DEFAULT_MARKERS)


async def _select_tenant(session) -> Tenant:
    rows = list((await session.scalars(select(Tenant).order_by(Tenant.created_at))).all())
    if not rows:
        raise SystemExit("No tenant rows in DB — bootstrap fails.")
    tenant = next(
        (
            row
            for row in rows
            if (row.name or "").strip().lower() in {"hive queen", "queenswarm solo", "queenswarm"}
        ),
        None,
    )
    return tenant or rows[-1]


async def seed(*, force: bool, dry_run: bool) -> dict[str, str]:
    """Apply prompt templates to matching agents; return per-agent status."""

    load_all_models()
    statuses: dict[str, str] = {}

    async with async_session() as session:
        # Tenant lookup is best-effort — included only so the operator log line
        # below ties prompt deployment to a recognisable workspace. The agent
        # registry itself is workspace-flat (no tenant_id on Agent rows).
        tenant = await _select_tenant(session)

        agents = list(
            (
                await session.scalars(
                    select(Agent).options(selectinload(Agent.agent_config_row))
                )
            ).all()
        )
        agents_by_name = {(a.name or "").strip(): a for a in agents}

        for spec_name, spec in AGENT_PROMPT_REGISTRY.items():
            agent = agents_by_name.get(spec_name)
            if agent is None:
                statuses[spec_name] = "missing_agent"
                continue

            cfg: AgentConfig | None = agent.agent_config_row
            if cfg is None:
                if dry_run:
                    statuses[spec_name] = "would_create"
                    continue
                cfg = AgentConfig(
                    agent_id=agent.id,
                    system_prompt=spec.system_prompt,
                )
                session.add(cfg)
                statuses[spec_name] = "created"
                continue

            current = cfg.system_prompt or ""
            if current.strip() == spec.system_prompt.strip():
                statuses[spec_name] = "unchanged"
                continue

            if not force and not _is_legacy_default(current):
                statuses[spec_name] = "skipped_custom"
                continue

            if dry_run:
                statuses[spec_name] = "would_update"
                continue

            cfg.system_prompt = spec.system_prompt
            statuses[spec_name] = "updated"

        if not dry_run:
            await session.commit()

    return statuses


def main() -> None:
    """CLI entrypoint."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="Overwrite operator-edited prompts.")
    parser.add_argument("--dry-run", action="store_true", help="Report only; do not write.")
    args = parser.parse_args()

    result = asyncio.run(seed(force=args.force, dry_run=args.dry_run))

    counts: dict[str, int] = {}
    for status in result.values():
        counts[status] = counts.get(status, 0) + 1

    print("agent_prompt_bootstrap:")
    for name in sorted(result):
        print(f"  {name:30s} -> {result[name]}")
    print("\nsummary:")
    for status in sorted(counts):
        print(f"  {status:20s} -> {counts[status]}")
    print(f"\ntotal: {sum(counts.values())}")


if __name__ == "__main__":
    main()
