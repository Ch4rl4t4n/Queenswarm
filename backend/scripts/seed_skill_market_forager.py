#!/usr/bin/env python3
"""Bootstrap Skill Market forager — RSS intel for Skill Factory research.

Idempotent: reuses forager by name; appends harness marker when missing.

Usage (inside backend container):
  python scripts/seed_skill_market_forager.py
  python scripts/seed_skill_market_forager.py --scrape
  python scripts/seed_skill_market_forager.py --json
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import uuid
from pathlib import Path
from typing import Any

from sqlalchemy import select

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.application.services.curated_memory_service import CuratedMemoryService
from app.application.services.forager_service import ForagerService
from app.core.config import settings
from app.core.database import async_session
from app.domain.memory.curated import CuratedFileKind
from app.infrastructure.persistence.models import load_all_models
from app.infrastructure.persistence.models.forager import ForagerORM
from app.infrastructure.persistence.models.tenant import Tenant

HARNESS_MARKER = "## Skill Market Forager"
FORAGER_NAME = "Skill Market Intel"

HARNESS_BLOCK = """\
## Skill Market Forager

RSS + blog feeds tagged `skill-market` feed Skill Factory research scoring.

1. Forager ingests → Knowledge tagged `skill-market`, `skill-market-intel`.
2. Celery embeds unindexed rows into HiveMind every 15 min.
3. Skill Factory research uses HiveMind + library competition to rank niches.
4. Operator approves forge output → Library → GitHub pack for external sale.

Do not promote raw RSS to verified skills without factory session + critic APPROVE.
"""

PROMPT_TEMPLATE = """\
Summarize each ingested item for Skill Factory market intel.

Tag every Knowledge row: skill-market, skill-market-intel.
Extract: niche keywords, buyer pain, price signals, competitor mentions.
Never auto-publish as tenant skill — research lane only.
Default simulate; drop promotional fluff without actionable workflow signal.
"""

DEFAULT_SCHEDULE: dict[str, Any] = {
    "enabled": True,
    "schedule_kind": "cron",
    "cron_expr": "0 6 * * *",
    "runtime_mode": "durable",
}

RSS_FEEDS: tuple[str, ...] = (
    "https://hnrss.org/newest?q=cursor+OR+agent+skill+OR+n8n",
    "https://hnrss.org/newest?q=automation+workflow",
    "https://www.reddit.com/r/ChatGPT/.rss",
    "https://www.reddit.com/r/LocalLLaMA/.rss",
)


async def _resolve_tenant(session) -> Tenant:
    tenant = await session.scalar(select(Tenant).order_by(Tenant.created_at.asc()).limit(1))
    if tenant is None:
        raise RuntimeError("No tenant found — run dashboard seed first.")
    return tenant


async def _ensure_forager(
    service: ForagerService,
    *,
    tenant_id: uuid.UUID,
) -> tuple[ForagerORM, bool]:
    existing = await service._db.scalar(
        select(ForagerORM).where(
            ForagerORM.tenant_id == tenant_id,
            ForagerORM.name == FORAGER_NAME,
        ),
    )
    if existing is not None:
        return existing, False

    row = await service.create(
        tenant_id=tenant_id,
        name=FORAGER_NAME,
        description="RSS skill-market intel for Skill Factory demand scoring.",
        source_type="rss",
        source_config={"feeds": list(RSS_FEEDS)},
        filter_config={
            "default_tags": ["skill-market", "skill-market-intel"],
            "topic_tags": ["skill-market"],
        },
        prompt_template=PROMPT_TEMPLATE,
        tools=["hivemind", "retrieval"],
        is_active=True,
        agent_template_id=None,
        schedule=DEFAULT_SCHEDULE,
        created_by_subject="seed:skill_market_forager",
    )
    return row, True


async def _ensure_harness(session, *, tenant_id: uuid.UUID) -> bool:
    svc = CuratedMemoryService(db=session)
    bundle = await svc.get_bundle(tenant_id)
    body = str(bundle.get(CuratedFileKind.INSTRUCTIONS, "") or "")
    if HARNESS_MARKER in body:
        return False
    merged = f"{body.rstrip()}\n\n{HARNESS_BLOCK}".strip()
    await svc.upsert(
        tenant_id=tenant_id,
        kind=CuratedFileKind.INSTRUCTIONS,
        content_md=merged,
        user_id=None,
    )
    return True


async def main(*, scrape: bool, as_json: bool) -> dict[str, Any]:
    load_all_models()
    if not settings.skill_factory_enabled:
        return {"skipped": True, "reason": "skill_factory_disabled"}

    async with async_session() as session:
        tenant = await _resolve_tenant(session)
        service = ForagerService(db=session)
        forager, created = await _ensure_forager(service, tenant_id=tenant.id)
        harness_added = await _ensure_harness(session, tenant_id=tenant.id)
        scraped = 0
        if scrape:
            from app.application.services.forager_rss_scraper import scrape_rss_forager_feeds

            records = await scrape_rss_forager_feeds(forager)
            if records:
                scraped = await service.ingest_records(
                    tenant_id=tenant.id,
                    forager_id=forager.id,
                    records=records,
                )
        await session.commit()

    result = {
        "tenant_id": str(tenant.id),
        "forager_id": str(forager.id),
        "forager_created": created,
        "harness_appended": harness_added,
        "scraped_records": scraped,
        "feeds": list(RSS_FEEDS),
    }
    if as_json:
        print(json.dumps(result, indent=2))
    else:
        print(f"Skill Market forager: {forager.id} (created={created}, scraped={scraped})")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed Skill Market forager for Skill Factory.")
    parser.add_argument("--scrape", action="store_true", help="Run initial RSS scrape.")
    parser.add_argument("--json", action="store_true", help="Print JSON result.")
    args = parser.parse_args()
    asyncio.run(main(scrape=args.scrape, as_json=args.json))
