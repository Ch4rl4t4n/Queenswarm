#!/usr/bin/env python3
"""Stop content-pack factory builds when LLM smoke fails (no point burning Celery)."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.infrastructure.persistence.models import load_all_models

load_all_models()

from sqlalchemy import select

from app.application.services.content_pack_factory_service import reconcile_stale_awaiting_forge_opportunities
from app.application.services.llm_runtime_credentials import refresh_llm_secret_cache
from app.application.services.supervisor.session_service import apply_session_control
from app.core.database import async_session
from app.core.llm_router import LiteLLMRouter
from app.infrastructure.persistence.models.content_pack_opportunity import ContentPackOpportunityORM
from app.infrastructure.persistence.models.supervisor_session import SupervisorSession
from app.infrastructure.persistence.models.tenant import Tenant

_OPERATOR = "operator:factory-abort-llm-blocked"


async def _smoke_ok(session) -> bool:
    router = LiteLLMRouter()
    try:
        await router.complete_with_fallback_messages(
            session,
            messages=[{"role": "user", "content": "Reply OK"}],
            max_tokens=5,
            swarm_id="factory_abort_llm_blocked",
            task_id="smoke",
        )
        return True
    except Exception:
        return False


async def _run(*, force: bool) -> int:
    async with async_session() as session:
        tenant = await session.scalar(select(Tenant).order_by(Tenant.created_at.asc()).limit(1))
        if tenant is None:
            print("No tenant.")
            return 1

        await refresh_llm_secret_cache(session)
        if await _smoke_ok(session) and not force:
            print("llm_smoke=PASS — no abort needed")
            return 0

        building = list(
            (
                await session.scalars(
                    select(ContentPackOpportunityORM).where(
                        ContentPackOpportunityORM.tenant_id == tenant.id,
                        ContentPackOpportunityORM.status == "building",
                    ),
                )
            ).all(),
        )
        if not building:
            print("llm_smoke=FAIL — no building opportunities to abort")
            return 0

        stopped = 0
        for row in building:
            sid = row.supervisor_session_id
            if sid is not None:
                sup = await session.get(SupervisorSession, sid)
                if sup is not None and sup.status in {"running", "needs_input", "paused", "pending", "queued"}:
                    await apply_session_control(session, session_row=sup, action="stop")
                    stopped += 1
            row.status = "failed"
            row.supervisor_session_id = None

        opportunities = list(
            (
                await session.scalars(
                    select(ContentPackOpportunityORM).where(
                        ContentPackOpportunityORM.tenant_id == tenant.id,
                    ),
                )
            ).all(),
        )
        await reconcile_stale_awaiting_forge_opportunities(
            session,
            tenant_id=tenant.id,
            opportunities=opportunities,
        )
        await session.commit()

        print("== Factory abort LLM-blocked builds ==")
        print(f"llm_smoke={'PASS' if await _smoke_ok(session) else 'FAIL'} force={force}")
        print(f"building_aborted={len(building)} sessions_stopped={stopped}")
        for row in building:
            print(f"  failed: {row.niche!r} id={row.id}")
        print("\nFix LLM (OpenAI key), then Build top pending opportunity in Pack factory.")
        return 0


def main() -> None:
    force = "--force" in sys.argv
    raise SystemExit(asyncio.run(_run(force=force)))


if __name__ == "__main__":
    main()
