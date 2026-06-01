#!/usr/bin/env python3
"""Patch curated memory with canonical operator identity (Jakub Chvostek → Najman client).

Usage:
  python scripts/patch_operator_identity.py
  python scripts/patch_operator_identity.py --force
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sqlalchemy import select

from app.application.services.curated_memory_service import CuratedFileKind, CuratedMemoryService
from app.core.database import async_session
from app.infrastructure.persistence.models import load_all_models
from app.infrastructure.persistence.models.tenant import Tenant

DEFAULT_TENANT_ID = "e098b808-8974-4bae-a6e1-de10bf6a2880"
MARKER = "## Operator identity (canonical)"

OPERATOR_BLOCK = """\
## Operator identity (canonical)

**Platform operator:** Jakub Chvostek — not a member of the Najman family.
**Client project:** Rodinné včelařství Najman (Najman family) — websites and social media.
**Role:** Help improve vcelarstvinajman.cz, beebrdy.cz, rozvozmedu.cz, and @vcelarstvi.najman.
Simulate-first always; live publish only after Jakub + Katka Najmanová approve.

**Lane mapping:**
- Lane A (marketing_najman) + Lane C (eshop_research) → Najman client deliverables (CZ copy).
- Lane B (tech_scv) + Lane D (automation) → Queenswarm platform (Jakub's harness).

Never address the operator as "Najman" or imply the operator is the beekeeping business.
"""

SOUL_PATCH = (
    "Voice: pragmatic Slovak/Czech — Jakub Chvostek operating Queenswarm for Najman client work."
)


async def _run(*, tenant_id: uuid.UUID, force: bool) -> dict[str, str]:
    load_all_models()
    async with async_session() as db:
        tenant = await db.get(Tenant, tenant_id)
        if tenant is None:
            raise SystemExit(f"Tenant not found: {tenant_id}")

        service = CuratedMemoryService(db=db)
        bundle = await service.get_bundle(tenant_id)
        instructions = bundle.get(CuratedFileKind.INSTRUCTIONS, "") or ""
        soul = bundle.get(CuratedFileKind.SOUL, "") or ""

        status = "skipped"
        if MARKER not in instructions or force:
            if MARKER in instructions and force:
                head, _, _tail = instructions.partition(MARKER)
                instructions = head.rstrip()
            merged = f"{instructions.rstrip()}\n\n---\n\n{OPERATOR_BLOCK.strip()}\n"
            await service.upsert(
                tenant_id=tenant_id,
                kind=CuratedFileKind.INSTRUCTIONS,
                content_md=merged,
                user_id=None,
            )
            status = "instructions_updated"

        if "Jakub Chvostek" not in soul:
            soul_merged = soul.replace(
                "Voice: pragmatic Slovak operator.",
                SOUL_PATCH,
            )
            if soul_merged == soul:
                soul_merged = f"{soul.rstrip()}\n\n{SOUL_PATCH}\n"
            await service.upsert(
                tenant_id=tenant_id,
                kind=CuratedFileKind.SOUL,
                content_md=soul_merged,
                user_id=None,
            )
            status = "instructions_and_soul_updated" if status != "skipped" else "soul_updated"

        await db.commit()
        return {"ok": status, "tenant_id": str(tenant_id)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tenant-id", default=DEFAULT_TENANT_ID)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    result = asyncio.run(_run(tenant_id=uuid.UUID(args.tenant_id), force=bool(args.force)))
    print(result)


if __name__ == "__main__":
    main()
