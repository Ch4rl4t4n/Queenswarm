#!/usr/bin/env python3
"""Repair factory LLM routing — drop invalid Grok vault key when smoke proves it bad."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.infrastructure.persistence.models import load_all_models

load_all_models()

from app.application.services.llm_runtime_credentials import (
    delete_llm_provider_secret,
    get_cached_llm_key,
    provider_effective_anthropic,
    provider_effective_grok,
    provider_effective_openai,
    refresh_llm_secret_cache,
)
from app.core.database import async_session
from app.core.llm_router import LiteLLMRouter


def _grok_key_invalid(error_text: str) -> bool:
    lowered = error_text.lower()
    return "incorrect api key" in lowered and ("x.ai" in lowered or "xai/" in lowered or "grok" in lowered)


async def _smoke(session) -> tuple[bool, str]:
    router = LiteLLMRouter()
    try:
        await router.complete_with_fallback_messages(
            session,
            messages=[{"role": "user", "content": "Reply OK"}],
            max_tokens=5,
            swarm_id="factory_llm_auto_repair",
            task_id="smoke",
        )
        return True, ""
    except Exception as exc:
        return False, str(exc)


async def _run(*, apply: bool) -> int:
    async with async_session() as session:
        await refresh_llm_secret_cache(session)
        had_grok_vault = bool(get_cached_llm_key("grok"))

        ok, err = await _smoke(session)
        if ok:
            print("== Factory LLM auto repair ==")
            print("smoke=PASS — nothing to repair")
            return 0

        repaired = False
        if had_grok_vault and _grok_key_invalid(err):
            if apply:
                await delete_llm_provider_secret(session, provider="grok")
                await session.commit()
                await refresh_llm_secret_cache(session)
                repaired = True
                print("repaired: removed invalid grok key from LLM vault")
            else:
                print("dry_run: would remove invalid grok vault key (pass --apply)")

        ok2, err2 = await _smoke(session) if repaired else (ok, err)

        print("== Factory LLM auto repair ==")
        print(f"apply={apply} grok_vault_was={had_grok_vault} repaired={repaired}")
        print(
            f"effective grok={bool(provider_effective_grok())} "
            f"anthropic={bool(provider_effective_anthropic())} "
            f"openai={bool(provider_effective_openai())}",
        )
        if provider_effective_grok() and not get_cached_llm_key("grok"):
            print("hint: invalid GROK_API_KEY may still be set in .env.prod — clear it and redeploy")

        if ok2:
            print("smoke=PASS")
            return 0

        print(f"smoke=FAIL {err2[:400]}")
        if not provider_effective_openai():
            print("\nNEXT: add OpenAI key (Settings → AI · LLM keys) or top up Anthropic credits.")
        return 1


def main() -> None:
    apply = "--apply" in sys.argv
    raise SystemExit(asyncio.run(_run(apply=apply)))


if __name__ == "__main__":
    main()
