#!/usr/bin/env python3
"""Bootstrap Social Intel swarm — foragers, harness block, optional first scrape.

Idempotent: skips harness append when marker present; reuses foragers by name.

Usage (inside backend container):
  python scripts/seed_social_intel_swarm.py
  python scripts/seed_social_intel_swarm.py --scrape
  python scripts/seed_social_intel_swarm.py --json
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
from app.core.config import settings
from app.core.database import async_session
from app.infrastructure.persistence.models import load_all_models
from app.infrastructure.persistence.models.forager import ForagerORM
from app.infrastructure.persistence.models.tenant import Tenant

HARNESS_MARKER = "## Social Intel Swarm"
GROK_GATE_MARKER = "pending-grok-verification"

GROK_GATE_APPEND = """\
### Grok truth gate (mandatory)
Raw scrape → tag `pending-grok-verification`. Promote to `hivemind-candidate` ONLY after
Grok truth arbiter (`xai/grok-3-mini`) confirms each factual claim. Drop `verdict=false`.
"""

HARNESS_BLOCK = """\
## Social Intel Swarm

After each YouTube/X forager scrape, run **researcher + critic** with skill
`social-intel-evaluator`:

1. Raw scrape lands in Knowledge tagged `pending-grok-verification` (NOT hivemind-candidate).
2. Summarize each item in 3 bullets; score tech fit (1–5) and business angle (1–5).
3. **Mandatory Grok truth arbiter** (`xai/grok-3-mini`) on EVERY factual bullet — drop `verdict=false`.
4. Verdict `keep` or `follow-up` only when Grok confirms true+high/medium or partial+medium.
5. Write HiveMind insight tagged `hivemind-candidate`, `social-intel` — available to all swarms.
6. Emit pollen only after simulation + Grok gate passes.

To add channels/accounts from chat, call `POST /foragers/{id}/sources` with
`platform` youtube|x and `sources` list.
"""

PROMPT_TEMPLATE = """\
Use skill social-intel-evaluator after ingest.

Raw scrape items are tagged pending-grok-verification — never promote to HiveMind without Grok.

For each scraped item:
- Summarize (3 bullets), then run Grok truth arbiter on each factual claim (xai/grok-3-mini).
- Drop claims with verdict=false; never write hivemind-candidate for failed claims.
- Score tech fit 1–5 and business angle 1–5.
- Verdict keep | archive | follow-up — only keep/follow-up after Grok pass.
- Drop when tech ≤2 AND business ≤2 unless operator requests archive review.
- Default simulate; never auto-publish scraped content.
"""

DEFAULT_SCHEDULE: dict[str, Any] = {
    "enabled": True,
    "schedule_kind": "cron",
    "cron_expr": "0 7 * * *",
    "runtime_mode": "durable",
}

OPERATOR_YOUTUBE_CHANNELS = [
    "https://www.youtube.com/@sandyleeai",
    "https://www.youtube.com/@DavidOndrej",
    "https://www.youtube.com/@Itssssss_Jack",
    "https://www.youtube.com/@NavalR",
    "https://www.youtube.com/@aiDotEngineer",
    "https://www.youtube.com/@GregIsenberg",
    "https://www.youtube.com/@sabrina_ramonov",
    "https://www.youtube.com/@RyanDoserAI",
    "https://www.youtube.com/@JEVanClief",
    "https://www.youtube.com/@AllAboutAI",
]

STARTER_X = ["@sama", "@pmarca", "@naval", "@a16z", "@OpenAI"]

FORAGER_SPECS: tuple[dict[str, Any], ...] = (
    {
        "name": "YouTube Intel",
        "description": "Daily YouTube channel scrape → Knowledge/HiveMind with social-intel evaluator.",
        "source_type": "youtube",
        "source_config": {
            "channels": OPERATOR_YOUTUBE_CHANNELS,
            "backfill_limit": 50,
            "delta_limit": 15,
        },
        "filter_config": {
            "topic_tags": ["intel", "youtube", "social-intel"],
        },
    },
    {
        "name": "X Intel",
        "description": "Daily X/Twitter account scrape → Knowledge/HiveMind with social-intel evaluator.",
        "source_type": "twitter",
        "source_config": {
            "accounts": STARTER_X,
            "backfill_limit": 50,
            "delta_limit": 20,
        },
        "filter_config": {
            "topic_tags": ["intel", "x", "social-intel"],
        },
    },
)


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
    """Append social intel harness block to curated instructions."""

    service = CuratedMemoryService(db=session)
    bundle = await service.get_bundle(tenant_id)
    current = bundle.get(CuratedFileKind.INSTRUCTIONS, "") or ""
    if HARNESS_MARKER in current and not force:
        if GROK_GATE_MARKER in current:
            return "skipped_existing"
        merged = f"{current.rstrip()}\n\n{GROK_GATE_APPEND}"
        try:
            await service.upsert(
                tenant_id=tenant_id,
                kind=CuratedFileKind.INSTRUCTIONS,
                content_md=merged,
                user_id=None,
            )
            return "appended_grok_gate"
        except ValueError:
            return "skipped_limit"
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


async def _ensure_forager(
    service: ForagerService,
    *,
    tenant_id: uuid.UUID,
    spec: dict[str, Any],
    replace_youtube_channels: bool = False,
) -> tuple[ForagerORM, str]:
    """Create or refresh one social intel forager."""

    name = str(spec["name"])
    existing = await service._db.scalar(
        select(ForagerORM).where(
            ForagerORM.tenant_id == tenant_id,
            ForagerORM.name == name,
        ),
    )
    if existing is None:
        row = await service.create(
            tenant_id=tenant_id,
            name=name,
            description=str(spec["description"]),
            source_type=str(spec["source_type"]),
            source_config=dict(spec["source_config"]),
            filter_config=dict(spec["filter_config"]),
            prompt_template=PROMPT_TEMPLATE,
            tools=["hivemind", "retrieval"],
            is_active=True,
            agent_template_id=None,
            schedule=DEFAULT_SCHEDULE,
            created_by_subject="seed_social_intel_swarm",
        )
        return row, "created"

    cfg = dict(existing.source_config or {})
    list_key = "channels" if existing.source_type == "youtube" else "accounts"
    starter = spec["source_config"].get(list_key) or []
    if replace_youtube_channels and existing.source_type == "youtube":
        cfg[list_key] = list(starter)
        status = "replaced_channels"
    else:
        current_list = cfg.get(list_key) or []
        if not isinstance(current_list, list):
            current_list = []
        merged = list(dict.fromkeys([*current_list, *starter]))
        if merged == current_list:
            status = "exists"
        else:
            cfg[list_key] = merged
            status = "updated_sources"
    cfg.setdefault("backfill_limit", spec["source_config"].get("backfill_limit", 50))
    cfg.setdefault("delta_limit", spec["source_config"].get("delta_limit", 15))
    updated = await service.update(
        tenant_id=tenant_id,
        forager_id=existing.id,
        source_config=cfg,
        filter_config=dict(spec["filter_config"]),
        prompt_template=PROMPT_TEMPLATE,
        schedule=DEFAULT_SCHEDULE,
        created_by_subject="seed_social_intel_swarm",
    )
    if updated is not None:
        existing = updated
    return existing, status


async def seed(*, scrape: bool = False, force_harness: bool = False, replace_youtube_channels: bool = False) -> dict[str, Any]:
    """Provision social intel foragers and optional first scrape."""

    load_all_models()
    result: dict[str, Any] = {
        "harness": "",
        "foragers": {},
        "scrape": {},
        "youtube_api_key_set": bool(settings.youtube_api_key),
    }

    async with async_session() as session:
        rows = list((await session.scalars(select(Tenant).order_by(Tenant.created_at))).all())
        tenant = _resolve_operator_tenant(rows)
        result["tenant_id"] = str(tenant.id)
        result["tenant_name"] = tenant.name

        result["harness"] = await _append_harness(session, tenant_id=tenant.id, force=force_harness)

        service = ForagerService(db=session)
        for spec in FORAGER_SPECS:
            row, status = await _ensure_forager(
                service,
                tenant_id=tenant.id,
                spec=spec,
                replace_youtube_channels=replace_youtube_channels,
            )
            result["foragers"][row.name] = {"id": str(row.id), "status": status}

        await session.commit()

        if scrape:
            from app.application.services.social_intel_runner import run_social_intel_forager

            for spec in FORAGER_SPECS:
                name = str(spec["name"])
                forager_id = uuid.UUID(result["foragers"][name]["id"])
                try:
                    out = await run_social_intel_forager(
                        session,
                        tenant_id=tenant.id,
                        forager_id=forager_id,
                        trigger_evaluator=True,
                    )
                    result["scrape"][name] = out
                    await session.commit()
                except Exception as exc:  # noqa: BLE001 — seed reports per-forager errors
                    await session.rollback()
                    result["scrape"][name] = {"error": str(exc)[:240]}

    return result


def main() -> None:
    """CLI entrypoint."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scrape", action="store_true", help="Run initial backfill scrape after provision.")
    parser.add_argument("--replace-youtube-channels", action="store_true", help="Replace YouTube channel list with operator defaults.")
    parser.add_argument("--force-harness", action="store_true", help="Overwrite instructions with harness block.")
    parser.add_argument("--json", action="store_true", help="Emit JSON summary.")
    args = parser.parse_args()
    payload = asyncio.run(
        seed(
            scrape=args.scrape,
            force_harness=args.force_harness,
            replace_youtube_channels=args.replace_youtube_channels,
        ),
    )
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print("social_intel_swarm_seed:")
        print(f"  tenant: {payload.get('tenant_name')} ({payload.get('tenant_id')})")
        print(f"  harness: {payload.get('harness')}")
        print(f"  youtube_api_key_set: {payload.get('youtube_api_key_set')}")
        for name, meta in (payload.get("foragers") or {}).items():
            print(f"  forager {name}: {meta.get('status')} id={meta.get('id')}")
        for name, meta in (payload.get("scrape") or {}).items():
            print(f"  scrape {name}: {meta}")


if __name__ == "__main__":
    main()
