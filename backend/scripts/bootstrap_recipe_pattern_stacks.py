"""Bootstrap orchestration pattern stacks on existing Recipe Library rows."""

from __future__ import annotations

import asyncio
import json

from sqlalchemy import select

from app.core.database import async_session
from app.domain.recipes.orchestration_pattern_stacks import enrich_workflow_template_patterns, infer_orchestration_template
from app.infrastructure.persistence.models.recipe import Recipe


async def bootstrap_recipe_pattern_stacks(*, dry_run: bool = True) -> dict[str, int]:
    """Backfill ``pattern_stack`` metadata on recipes missing explicit tags.

    Args:
        dry_run: When True, report changes without committing.

    Returns:
        Counts of scanned, updated, and skipped rows.
    """
    scanned = 0
    updated = 0
    skipped = 0

    async with async_session() as session:
        rows = list(await session.scalars(select(Recipe).order_by(Recipe.name.asc())))
        for row in rows:
            scanned += 1
            tmpl = dict(row.workflow_template or {})
            if tmpl.get("pattern_stack"):
                skipped += 1
                continue
            template_id = infer_orchestration_template(name=row.name, workflow_template=tmpl)
            if template_id is None:
                skipped += 1
                continue
            enriched = enrich_workflow_template_patterns(tmpl)
            if enriched == tmpl:
                skipped += 1
                continue
            updated += 1
            if not dry_run:
                row.workflow_template = enriched

        if not dry_run and updated:
            await session.commit()

    return {"scanned": scanned, "updated": updated, "skipped": skipped, "dry_run": dry_run}


def main() -> None:
    """CLI entrypoint."""

    import os

    dry_run = os.environ.get("DRY_RUN", "1") != "0"
    result = asyncio.run(bootstrap_recipe_pattern_stacks(dry_run=dry_run))
    print(json.dumps(result))


if __name__ == "__main__":
    main()
