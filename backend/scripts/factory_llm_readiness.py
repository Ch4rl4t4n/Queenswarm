#!/usr/bin/env python3
"""Check LLM router credentials and optional smoke ping for factory builds."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.infrastructure.persistence.models import load_all_models

load_all_models()

from app.application.services.factory_llm_readiness_service import (
    resolve_factory_llm_readiness,
    run_factory_llm_smoke,
)
from app.application.services.research_runtime_credentials import resolve_research_keys
from app.core.database import async_session


async def _run(*, smoke: bool) -> int:
    async with async_session() as session:
        await resolve_research_keys(session)
        status = await resolve_factory_llm_readiness(session)

    print("== Factory LLM readiness ==")
    print(
        f"grok={status.grok_configured} anthropic={status.anthropic_configured} "
        f"openai={status.openai_configured} grok_primary={status.grok_primary}",
    )
    print(f"decomposition_chain_usable={status.decomposition_chain or 'NONE'}")
    print(f"build_allowed={status.build_allowed}")
    print(f"hint: {status.recommended_action}")

    if not status.build_allowed:
        print("\nBLOCKED: No routable LLM for factory builds.")
        return 1

    if smoke:
        async with async_session() as session:
            smoked = await run_factory_llm_smoke(session)
        if smoked.smoke_ok:
            print("\nsmoke_test=PASS")
            return 0
        print(f"\nsmoke_test=FAIL error={smoked.smoke_error}")
        if status.grok_primary:
            print("\nTypical fixes:")
            print("• Re-test Grok in Settings → AI · LLM keys")
            print("• Check xAI billing / API key permissions")
        return 1

    print("\nRun with --smoke to verify Grok with a live ping.")
    return 0


def main() -> None:
    smoke = "--smoke" in sys.argv
    raise SystemExit(asyncio.run(_run(smoke=smoke)))


if __name__ == "__main__":
    main()
