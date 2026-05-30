#!/usr/bin/env python3
"""Append Agentic OS operator harness block to curated memory instructions.

Usage:
    python scripts/bootstrap_agentic_os_harness.py [--force]
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
sys.path.insert(0, str(ROOT))

from sqlalchemy import select

from app.application.services.curated_memory_service import CuratedFileKind, CuratedMemoryService
from app.core.database import async_session
from app.infrastructure.persistence.models import load_all_models
from app.infrastructure.persistence.models.tenant import Tenant

MARKER = "=== BEHAVIORAL INSTRUCTIONS ==="
TEMPLATE_CANDIDATES = (
    ROOT / "agentic_os_harness_instructions.md.example",
    REPO / "docs/curated_memory_templates/operator_harness_instructions.md.example",
)


def _load_template() -> str:
    """Load harness template from repo or copied sibling path."""

    for path in TEMPLATE_CANDIDATES:
        if path.is_file():
            return path.read_text(encoding="utf-8").strip()
    msg = f"Template missing — tried: {', '.join(str(p) for p in TEMPLATE_CANDIDATES)}"
    raise SystemExit(msg)


async def apply(*, force: bool) -> str:
    """Merge Agentic OS harness template into tenant instructions."""

    block = _load_template()
    load_all_models()

    async with async_session() as session:
        rows = list((await session.scalars(select(Tenant).order_by(Tenant.created_at))).all())
        if not rows:
            raise SystemExit("No tenant rows in DB.")
        tenant = next(
            (
                row
                for row in rows
                if (row.name or "").strip().lower() in {"hive queen", "queenswarm solo", "queenswarm"}
            ),
            rows[-1],
        )

        service = CuratedMemoryService(db=session)
        bundle = await service.get_bundle(tenant.id)
        current = bundle.get(CuratedFileKind.INSTRUCTIONS, "") or ""

        if MARKER in current and not force:
            await session.commit()
            return "skipped_existing"

        if force or not current.strip():
            merged = block
        elif MARKER in current:
            merged = current
        else:
            merged = f"{current.rstrip()}\n\n---\n\n{block}"

        await service.upsert(
            tenant_id=tenant.id,
            kind=CuratedFileKind.INSTRUCTIONS,
            content_md=merged,
            user_id=None,
        )
        await session.commit()
    return "written"


def main() -> None:
    """CLI entrypoint."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    status = asyncio.run(apply(force=args.force))
    print(f"agentic_os_harness: {status}")


if __name__ == "__main__":
    main()
