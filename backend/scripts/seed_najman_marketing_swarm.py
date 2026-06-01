#!/usr/bin/env python3
"""Bootstrap Najman Marketing colony — brand memory, competitor forager, analysis session.

Idempotent harness append; builds marketing-ops swarm if missing; optional Phase-0 analysis session.

Usage (inside backend container):
  python scripts/seed_najman_marketing_swarm.py
  python scripts/seed_najman_marketing_swarm.py --start-analysis
  python scripts/seed_najman_marketing_swarm.py --json
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

from app.application.services.curated_memory_service import CuratedFileKind, CuratedMemoryService
from app.application.services.forager_service import ForagerService
from app.application.services.supervisor.session_service import create_supervisor_session
from app.application.services.supervisor.shared_context import SharedContextService
from app.core.config import settings
from app.core.database import async_session
from app.infrastructure.persistence.models import load_all_models
from app.infrastructure.persistence.models.forager import ForagerORM
from app.infrastructure.persistence.models.tenant import Tenant

HARNESS_MARKER = "## Najman Marketing Colony"
MISSION_MARKER = "### Rodinné včelařství Najman"

PHASE0_ANALYSIS_GOAL = """\
Najman — fáze 0 tržní analýza (operátor zvolil variantu D: nejdřív analýza a doporučení webové architektury).

## Klient
Rodinné včelařství Najman, Na Samotě 1029, 253 01 Hostivice, ČR.
Kontakt: vcelahostivice@seznam.cz · +420 603 887 482

## Aktiva
- vcelarstvinajman.cz — info web, novinky
- beebrdy.cz — WooCommerce e-shop (dobírka, ~6 produktů)
- rozvozmedu.cz — lokální rozvoz medu Hostivice
- Instagram: @vcelarstvi.najman
- YouTube: Rodinné včelařství Najman - Hostivice

## Produkty (highlight)
7 druhů medů (Brdy, Křivoklát, lipový…), včelí matky, oddělky, propolisová mastička, medový balzám.

## Úkol (výstup v češtině, simulate-first)
1. SWOT Najman vs top CZ/SK včelařské e-shopy (Pleva, JaHan, Vceliobchod, iVčelárskePotreby, Vcelo.sk, …).
2. Porovnat webové modely konkurence: jedna doména vs hub+spoke vs více značek.
3. **Doporučit jednu variantu A/B/C/D** pro naše 3 weby s jasným odůvodněním:
   - A) beebrdy.cz = hlavní shop, ostatní = příběh/blog + lokální rozvoz
   - B) sloučit vše pod vcelarstvinajman.cz
   - C) ponechat 3 weby, jen redesign každého
   - D) jiné (navrhni)
4. Keyword map CZ (med, včelařství, rozvoz medu Hostivice, matky, oddělky, propolis…).
5. Slabiny vs konkurence + kde být 3× lepší (UX, obsah, SEO, social, platby).
6. Quick wins pro Instagram do 30.6.2026 (organika, bez placených reklam zatím).
7. Návrh fází 1–4: social kalendář → redesign brief → blog → launch kampaň.

Použij skills: marketing-campaign-playbook, competitor-scrape-analyze.
Ulož verified brief do HiveMind s tagy: najman-marketing, phase-0, web-architecture.
Default simulate — žádný live publish.
"""

HARNESS_BLOCK = """\
## Najman Marketing Colony

**firm_id:** `najman`
**Jazyk:** čeština (veřejný obsah, blog, social)
**Schvalovatelé:** operátor + Katka Najmanová — simulate vždy před live

### Značka
Rodinné včelařství Najman · Hostivice · šlechtitelský chov včely kraňské
Weby: vcelarstvinajman.cz · beebrdy.cz (eshop) · rozvozmedu.cz (lokální rozvoz)
Social: @vcelarstvi.najman · YouTube kanál Najman

### Cíle 2026
- Fáze 0: tržní analýza + doporučení webové architektury (A/B/C/D)
- Social first: roční IG/FB kalendář, simulate → approve → publish
- Redesign WordPress/WooCommerce (brief pro externí nástroje, ne live deploy bez schválení)
- Blog SEO (včelařství, med, Hostivice, matky, oddělky)
- Launch kampaň 15.–30.6.2026

### Konkurence CZ (inspirace, ne kopírovat)
pleva.cz · jahan.cz · vceliobchod.cz · vcest.cz · eshop.ceskavcela.cz · trebonsky-med.cz · ceskejmed.cz

### Konkurence SK
ivcelarskepotreby.sk · vcelo.sk · vcelarsky-obchod.sk · baranik.sk · medar.sk

### Guardrails
- Tag všechny výstupy `firm_id=najman` + `najman-marketing`
- Nikdy nemíchat assety jiných firem
- Platby: doporuč Comgate/GoPay — live až po operátorovi
- Meta Ads: jen po analýze a 4–6 týdnech organiky
"""

MISSION_APPEND = """\
### Rodinné včelařství Najman (marketing klient)

Rodinné včelařství z Hostivic — medy z Brd a Křivoklátu, matky a oddělky kraňské včely,
propolisové výrobky. Tři weby (info, eshop, rozvoz). Cíl: několikanásobně lepší online
prezentace než CZ/SK konkurence — redesign, blog, social, SEO, simulate-first publish.
"""

COMPETITOR_FORAGER = {
    "name": "Vcelarstvi Competitor Intel",
    "description": "CZ/SK včelařská konkurence — web + social signály pro Najman marketing swarm.",
    "source_type": "twitter",
    "source_config": {
        "accounts": [
            "@pleva",
            "@Vcelo_vcelarske_potreby",
        ],
        "websites": [
            "https://www.pleva.cz",
            "https://www.jahan.cz",
            "https://www.vceliobchod.cz",
            "https://www.vcest.cz",
            "https://eshop.ceskavcela.cz",
            "https://www.trebonsky-med.cz",
            "https://www.ivcelarskepotreby.sk",
            "https://www.vcelo.sk",
            "https://www.medar.sk",
        ],
        "backfill_limit": 30,
        "delta_limit": 15,
    },
    "filter_config": {
        "topic_tags": ["najman-marketing", "competitor-intel", "vcelarstvi"],
    },
}

DEFAULT_SCHEDULE: dict[str, Any] = {
    "enabled": True,
    "schedule_kind": "cron",
    "cron_expr": "0 8 * * 2,5",
    "runtime_mode": "durable",
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
    """Append Najman harness block to curated instructions."""

    service = CuratedMemoryService(db=session)
    bundle = await service.get_bundle(tenant_id)
    current = bundle.get(CuratedFileKind.INSTRUCTIONS, "") or ""
    if HARNESS_MARKER in current and not force:
        return "skipped_existing"
    merged = HARNESS_BLOCK if force or not current.strip() else f"{current.rstrip()}\n\n{HARNESS_BLOCK}"
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


async def _append_mission(session, *, tenant_id: uuid.UUID, force: bool) -> str:
    """Append Najman client block to curated mission memory."""

    service = CuratedMemoryService(db=session)
    bundle = await service.get_bundle(tenant_id)
    current = bundle.get(CuratedFileKind.MISSION, "") or ""
    if MISSION_MARKER in current and not force:
        return "skipped_existing"
    merged = MISSION_APPEND if force or not current.strip() else f"{current.rstrip()}\n\n{MISSION_APPEND}"
    try:
        await service.upsert(
            tenant_id=tenant_id,
            kind=CuratedFileKind.MISSION,
            content_md=merged,
            user_id=None,
        )
        return "written"
    except ValueError:
        return "skipped_limit"


async def _ensure_competitor_forager(
    service: ForagerService,
    *,
    tenant_id: uuid.UUID,
) -> tuple[ForagerORM, str]:
    """Create or refresh competitor intel forager."""

    name = str(COMPETITOR_FORAGER["name"])
    existing = await service._db.scalar(
        select(ForagerORM).where(
            ForagerORM.tenant_id == tenant_id,
            ForagerORM.name == name,
        ),
    )
    prompt = (
        "Competitor intel for Najman marketing. Summarize pricing, UX, social cadence, SEO hooks. "
        "Tag najman-marketing. Default simulate."
    )
    if existing is None:
        row = await service.create(
            tenant_id=tenant_id,
            name=name,
            description=str(COMPETITOR_FORAGER["description"]),
            source_type=str(COMPETITOR_FORAGER["source_type"]),
            source_config=dict(COMPETITOR_FORAGER["source_config"]),
            filter_config=dict(COMPETITOR_FORAGER["filter_config"]),
            prompt_template=prompt,
            tools=["hivemind", "retrieval"],
            is_active=True,
            agent_template_id=None,
            schedule=DEFAULT_SCHEDULE,
            created_by_subject="seed_najman_marketing_swarm",
        )
        return row, "created"

    existing.source_config = dict(COMPETITOR_FORAGER["source_config"])
    existing.filter_config = dict(COMPETITOR_FORAGER["filter_config"])
    existing.description = str(COMPETITOR_FORAGER["description"])
    existing.is_active = True
    await service._db.flush()
    return existing, "updated"


async def _start_phase0_analysis(session, *, tenant_id: uuid.UUID) -> dict[str, Any]:
    """Queue Phase-0 market analysis supervisor session."""

    created = await create_supervisor_session(
        session,
        goal=PHASE0_ANALYSIS_GOAL,
        created_by_subject="seed_najman_marketing_swarm",
        runtime_mode="durable",
        roles=["researcher", "critic"],
        shared_context=SharedContextService(),
        retrieval_contract="customer_history+policy+last_3_tasks",
        skill_slugs=["marketing-campaign-playbook", "competitor-scrape-analyze", "context", "decide"],
        tenant_id=tenant_id,
    )
    await session.commit()
    return {
        "session_id": str(created.id),
        "status": str(created.status),
        "goal_preview": PHASE0_ANALYSIS_GOAL[:120],
    }


async def main(*, start_analysis: bool, force_harness: bool, as_json: bool) -> int:
    """Run Najman marketing bootstrap."""

    load_all_models()
    report: dict[str, Any] = {"ok": True, "steps": {}}

    async with async_session() as session:
        tenants = list((await session.scalars(select(Tenant))).all())
        tenant = _resolve_operator_tenant(tenants)
        tenant_id = tenant.id
        report["tenant_id"] = str(tenant_id)
        report["tenant_name"] = tenant.name

        report["steps"]["harness"] = await _append_harness(session, tenant_id=tenant_id, force=force_harness)
        report["steps"]["mission"] = await _append_mission(session, tenant_id=tenant_id, force=force_harness)
        await session.commit()

        if settings.solo_mode_enabled:
            report["steps"]["marketing_ops_swarm"] = {
                "status": "skipped",
                "reason": "SOLO_MODE — use four-lane bootstrap instead of Virtual Company marketing-ops",
            }
        else:
            from app.application.services.virtual_company_swarm_builder import build_department_swarm

            build = await build_department_swarm(
                session,
                tenant=tenant,
                template_id="marketing-ops",
                created_by_subject="seed_najman_marketing_swarm",
                skip_if_exists=True,
            )
            await session.commit()
            report["steps"]["marketing_ops_swarm"] = build

        forager_service = ForagerService(db=session)
        row, status = await _ensure_competitor_forager(forager_service, tenant_id=tenant_id)
        await session.commit()
        report["steps"]["competitor_forager"] = {"id": str(row.id), "status": status}

        if start_analysis:
            analysis = await _start_phase0_analysis(session, tenant_id=tenant_id)
            report["steps"]["phase0_analysis_session"] = analysis

    if as_json:
        print(json.dumps(report, indent=2))
    else:
        print("Najman Marketing colony bootstrap OK")
        for key, val in report["steps"].items():
            print(f"  {key}: {val}")
        if start_analysis and "phase0_analysis_session" in report["steps"]:
            sid = report["steps"]["phase0_analysis_session"]["session_id"]
            print(f"\nPhase-0 analysis running — track: /agents#sessions (session {sid})")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed Najman Marketing colony")
    parser.add_argument("--start-analysis", action="store_true", help="Start Phase-0 supervisor analysis session")
    parser.add_argument("--force-harness", action="store_true", help="Replace harness block")
    parser.add_argument("--json", action="store_true", help="JSON output")
    args = parser.parse_args()
    raise SystemExit(asyncio.run(main(
        start_analysis=args.start_analysis,
        force_harness=args.force_harness,
        as_json=args.json,
    )))
