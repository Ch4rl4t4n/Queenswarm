#!/usr/bin/env python3
"""ST3 — Seed Tech SCV Innovation Lab proposal drafts (simulate, no LLM)."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Literal

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import select

from app.application.services.hive_innovation_lab import (
    InnovationBrainstormRequest,
    brainstorm_innovation_proposal,
    count_pending_innovation_proposals,
)
from app.core.database import async_session
from app.infrastructure.persistence.models import load_all_models
from app.infrastructure.persistence.models.tenant import Tenant

load_all_models()

InnovationCategory = Literal["feature", "ux", "integration", "swarm", "factory"]

TECH_SCV_PROMPTS: list[tuple[InnovationCategory, str]] = [
    (
        "integration",
        "Tech SCV: expose four-lane Grok routing health in Innovation Lab cockpit snapshot.",
    ),
    (
        "ux",
        "Tech SCV: Mission Home strategic today strip demotes clutter — add operator dismiss per lane.",
    ),
    (
        "factory",
        "Tech SCV: Skill Factory LOOP5 preset links to analytics report critic gate automatically.",
    ),
]


def _resolve_tenant(rows: list[Tenant]) -> Tenant:
    for row in rows:
        if (row.name or "").strip().lower() in {"hive queen", "queenswarm solo", "queenswarm"}:
            return row
    return rows[-1]


async def _run(*, target: int) -> dict[str, object]:
    async with async_session() as session:
        rows = list((await session.scalars(select(Tenant).order_by(Tenant.created_at))).all())
        if not rows:
            return {"ok": False, "error": "no_tenant"}
        tenant = _resolve_tenant(rows)
        pending_before = await count_pending_innovation_proposals(session, tenant_id=tenant.id)
        created: list[str] = []
        if pending_before < target:
            for category, prompt in TECH_SCV_PROMPTS:
                if pending_before + len(created) >= target:
                    break
                out = await brainstorm_innovation_proposal(
                    session,
                    tenant_id=tenant.id,
                    body=InnovationBrainstormRequest(prompt=prompt, category=category),
                )
                created.append(out.id)
        await session.commit()
        pending_after = await count_pending_innovation_proposals(session, tenant_id=tenant.id)
        return {
            "ok": True,
            "tenant_id": str(tenant.id),
            "pending_before": pending_before,
            "pending_after": pending_after,
            "created_ids": created,
        }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", type=int, default=3, help="Minimum pending proposals")
    args = parser.parse_args()
    result = asyncio.run(_run(target=max(1, args.target)))
    print(json.dumps(result, indent=2))
    if not result.get("ok"):
        raise SystemExit(1)
    if int(result.get("pending_after") or 0) < args.target:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
