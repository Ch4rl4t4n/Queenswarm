#!/usr/bin/env python3
"""Content Pack Factory operator cycle status — research → build → approve → export."""

from __future__ import annotations

import asyncio
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import select

from app.application.services.content_pack_factory_gumroad_listing import (
    gumroad_listing_ready,
    gumroad_publish_ready,
    read_gumroad_listing_ref,
)
from app.application.services.content_pack_factory_service import compose_content_pack_factory_snapshot
from app.core.config import settings
from app.core.database import async_session
from app.infrastructure.persistence.models.content_pack_opportunity import ContentPackOpportunityORM
from app.infrastructure.persistence.models.tenant import Tenant
from app.infrastructure.persistence.models.tenant_content_pack import TenantContentPackORM


async def _run() -> int:
    async with async_session() as session:
        tenant = await session.scalar(select(Tenant).order_by(Tenant.created_at.asc()).limit(1))
        if tenant is None:
            print("No tenant.")
            return 1

        await compose_content_pack_factory_snapshot(session, tenant_id=tenant.id)
        await session.commit()

        opp_rows = (
            await session.scalars(
                select(ContentPackOpportunityORM)
                .where(ContentPackOpportunityORM.tenant_id == tenant.id)
                .order_by(ContentPackOpportunityORM.created_at.desc()),
            )
        ).all()
        pack_rows = (
            await session.scalars(
                select(TenantContentPackORM)
                .where(
                    TenantContentPackORM.tenant_id == tenant.id,
                    TenantContentPackORM.is_active.is_(True),
                )
                .order_by(TenantContentPackORM.created_at.desc()),
            )
        ).all()

        by_status = Counter(str(row.status or "unknown") for row in opp_rows)
        gumroad_draft_ready = await gumroad_listing_ready(session)
        gumroad_live_ready = await gumroad_publish_ready(session)

        print("== Content Pack Factory cycle status ==")
        print(f"factory_enabled={settings.content_pack_factory_enabled}")
        print(f"opportunities_total={len(opp_rows)} by_status={dict(by_status)}")
        print(f"library_active={len(pack_rows)}")
        print(
            "export_flags:",
            f"gumroad_draft={gumroad_draft_ready}",
            f"gumroad_publish={gumroad_live_ready}",
        )

        awaiting = [row for row in opp_rows if row.status == "awaiting_forge"]
        if awaiting:
            print(f"\n-- Queue: {len(awaiting)} awaiting forge approve --")
            for row in awaiting[:5]:
                print(f"  {row.niche!r} score={row.composite_score:.2f} id={row.id}")

        failed = [row for row in opp_rows if row.status == "failed"]
        if failed:
            print(f"\n-- Failed builds: {len(failed)} (fix LLM keys, then re-build) --")
            for row in failed[:3]:
                print(f"  {row.niche!r} id={row.id}")

        if pack_rows:
            print("\n-- Library export state --")
            for pack in pack_rows[:10]:
                opp = next((o for o in opp_rows if o.tenant_content_pack_id == pack.id), None)
                gumroad_ref = read_gumroad_listing_ref(opp)
                print(
                    f"  {pack.slug}: github_exported={bool(pack.github_exported_at)} "
                    f"gumroad_product={bool(gumroad_ref and gumroad_ref.get('product_id'))} "
                    f"gumroad_live={bool(gumroad_ref and gumroad_ref.get('published'))}",
                )

        print("\n-- Recommended next step --")
        if awaiting:
            print("Approve verified_content_pack_forge in Agents → forge report.")
        elif failed and not pack_rows:
            print("Fix LLM keys (Settings → AI · LLM keys). Run: python scripts/factory_llm_readiness.py")
            print("Then Content Factory → Pack factory → Build top pending opportunity.")
        elif not pack_rows:
            print("Content Factory → Pack factory → Run research → Build top opportunity.")
        elif not any(pack.github_exported_at for pack in pack_rows):
            print("Library → Export bundle on best verified pack.")
        elif gumroad_draft_ready and not gumroad_live_ready:
            print("Library → Gumroad draft (enable SKILL_FACTORY_GUMROAD_PUBLISH_ENABLED for live).")
        elif gumroad_live_ready:
            print("Library → Gumroad publish, or research next vertical niche.")
        else:
            print("Configure Gumroad env flags or manual upload from export bundle.")

        return 0


def main() -> None:
    raise SystemExit(asyncio.run(_run()))


if __name__ == "__main__":
    main()
