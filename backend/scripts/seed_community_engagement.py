#!/usr/bin/env python3
"""Bootstrap Community Engagement (POS-CE) — forager, harness block, optional scrape.

Idempotent: skips harness when marker present; reuses forager by name.

Usage (inside backend container):
  python scripts/seed_community_engagement.py
  python scripts/seed_community_engagement.py --scrape
  python scripts/seed_community_engagement.py --json
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any

from sqlalchemy import select

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.application.services.community_engagement_policy import (  # noqa: E402
    COMMUNITY_ENGAGEMENT_HARNESS_MARKER,
    COMMUNITY_FORAGER_PROMPT,
    COMMUNITY_HARNESS_BLOCK,
)
from app.application.services.curated_memory_service import CuratedFileKind, CuratedMemoryService  # noqa: E402
from app.application.services.forager_service import ForagerService  # noqa: E402
from app.core.config import settings  # noqa: E402
from app.core.database import async_session  # noqa: E402
from app.infrastructure.persistence.models import load_all_models  # noqa: E402
from app.infrastructure.persistence.models.forager import ForagerORM  # noqa: E402
from app.infrastructure.persistence.models.tenant import Tenant  # noqa: E402

FORAGER_NAME = "Community Engagement Intel"

DEFAULT_SCHEDULE: dict[str, Any] = {
    "enabled": True,
    "schedule_kind": "cron",
    "cron_expr": "0 8 * * *",
    "runtime_mode": "durable",
}

STARTER_REDDIT_FEEDS: list[str] = [
    "https://www.reddit.com/r/Beekeeping/.rss",
    "https://www.reddit.com/r/slovakia/.rss",
    "https://www.reddit.com/r/LocalLLaMA/.rss",
]

FORAGER_SPEC: dict[str, Any] = {
    "name": FORAGER_NAME,
    "description": "Reddit/community RSS → engagement-candidate rows for marketing digest (simulate-first).",
    "source_type": "rss",
    "source_config": {
        "feeds": STARTER_REDDIT_FEEDS,
    },
    "filter_config": {
        "topic_tags": ["community", "engagement-candidate", "community-intel"],
        "default_tags": ["community", "engagement-candidate", "community-intel"],
        "monitor_niche": "community",
        "extract_schema": "community_engagement",
    },
}


def _resolve_operator_tenant(rows: list[Tenant]) -> Tenant:
    """Pick Hive Queen / solo tenant when present."""

    if not rows:
        raise SystemExit("No tenant rows in DB.")
    tenant = next(
        (
            row
            for row in rows
            if (row.name or "").strip().lower() in {"hive queen", "queenswarm solo", "queenswarm"}
        ),
        None,
    )
    return tenant if tenant is not None else rows[-1]


async def _append_harness(session, *, tenant_id: uuid.UUID, force: bool) -> str:
    """Append POS-CE harness block to curated instructions."""

    service = CuratedMemoryService(db=session)
    bundle = await service.get_bundle(tenant_id)
    current = bundle.get(CuratedFileKind.INSTRUCTIONS, "") or ""
    if COMMUNITY_ENGAGEMENT_HARNESS_MARKER in current and not force:
        return "skipped_existing"
    merged = (
        COMMUNITY_HARNESS_BLOCK
        if force or not current.strip()
        else f"{current.rstrip()}\n\n{COMMUNITY_HARNESS_BLOCK}"
    )
    try:
        await service.upsert(
            tenant_id=tenant_id,
            kind=CuratedFileKind.INSTRUCTIONS,
            content_md=merged,
            user_id=None,
        )
        return "written"
    except ValueError:
        return "skipped_limit"


async def _ensure_forager(
    service: ForagerService,
    *,
    tenant_id: uuid.UUID,
) -> tuple[ForagerORM, str]:
    """Create or refresh community engagement forager."""

    existing = await service._db.scalar(
        select(ForagerORM).where(
            ForagerORM.tenant_id == tenant_id,
            ForagerORM.name == FORAGER_NAME,
        ),
    )
    if existing is None:
        row = await service.create(
            tenant_id=tenant_id,
            name=FORAGER_NAME,
            description=str(FORAGER_SPEC["description"]),
            source_type=str(FORAGER_SPEC["source_type"]),
            source_config=dict(FORAGER_SPEC["source_config"]),
            filter_config=dict(FORAGER_SPEC["filter_config"]),
            prompt_template=COMMUNITY_FORAGER_PROMPT,
            tools=["rss", "web_search", "hivemind", "retrieval"],
            is_active=True,
            agent_template_id=None,
            schedule=DEFAULT_SCHEDULE,
            created_by_subject="seed_community_engagement",
        )
        return row, "created"

    cfg = dict(existing.source_config or {})
    feeds = cfg.get("feeds") or []
    if not isinstance(feeds, list):
        feeds = []
    merged_feeds = list(dict.fromkeys([*feeds, *STARTER_REDDIT_FEEDS]))
    cfg["feeds"] = merged_feeds
    existing.source_config = cfg
    existing.prompt_template = COMMUNITY_FORAGER_PROMPT
    existing.is_active = True
    await service._db.flush()
    return existing, "updated"


async def seed(*, scrape: bool = False, force_harness: bool = False) -> dict[str, Any]:
    """Provision POS-CE forager + harness."""

    load_all_models()
    async with async_session() as session:
        tenants = list((await session.scalars(select(Tenant))).all())
        tenant = _resolve_operator_tenant(tenants)
        tenant_id = tenant.id

        harness_status = await _append_harness(session, tenant_id=tenant_id, force=force_harness)
        service = ForagerService(db=session)
        forager, forager_status = await _ensure_forager(service, tenant_id=tenant_id)

        scrape_result: dict[str, Any] | None = None
        if scrape:
            from app.application.services.forager_rss_scraper import scrape_rss_forager_feeds
            from app.application.services.forager_service import ForagerService as FS

            items = await scrape_rss_forager_feeds(forager)
            ingested = 0
            if items:
                ingested = await FS(db=session).ingest_records(
                    tenant_id=tenant_id,
                    forager_id=forager.id,
                    records=items,
                )
            scrape_result = {"scraped": len(items), "ingested": ingested}

        await session.commit()
        return {
            "tenant_id": str(tenant_id),
            "harness": harness_status,
            "forager_id": str(forager.id),
            "forager_status": forager_status,
            "forager_name": FORAGER_NAME,
            "scrape": scrape_result,
            "guide": "docs/COMMUNITY_ENGAGEMENT_SETUP.md",
        }


def main() -> None:
    """CLI entry."""

    parser = argparse.ArgumentParser(description="Seed Community Engagement (POS-CE)")
    parser.add_argument("--scrape", action="store_true", help="Run first RSS scrape after create")
    parser.add_argument("--force-harness", action="store_true", help="Replace harness block")
    parser.add_argument("--json", action="store_true", help="Print JSON result")
    args = parser.parse_args()

    result = asyncio.run(seed(scrape=args.scrape, force_harness=args.force_harness))
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(result)


if __name__ == "__main__":
    main()
