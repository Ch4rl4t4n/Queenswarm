"""Shared factory LLM credential readiness — Skill + Content Pack factories."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.application.services.llm_runtime_credentials import (
    provider_effective_anthropic,
    provider_effective_grok,
    provider_effective_openai,
    refresh_llm_secret_cache,
)
from app.core.config import settings
from app.core.llm_router import LiteLLMRouter, model_slug_has_configured_credentials
from sqlalchemy.ext.asyncio import AsyncSession


class FactoryLlmReadinessOut(BaseModel):
    """LLM decomposition readiness for factory build lanes."""

    model_config = ConfigDict(extra="ignore")

    grok_configured: bool = False
    anthropic_configured: bool = False
    openai_configured: bool = False
    chain_usable: bool = False
    build_allowed: bool = False
    grok_primary: bool = False
    recommended_action: str = ""
    decomposition_chain: list[str] = Field(default_factory=list)
    smoke_ok: bool | None = None
    smoke_error: str | None = None


def _decomposition_models() -> tuple[str, str, str]:
    return (
        settings.workflow_breaker_primary_model,
        settings.workflow_breaker_fallback_model,
        settings.workflow_breaker_tertiary_model,
    )


def _is_grok_model_slug(model_name: str) -> bool:
    lowered = model_name.lower()
    return lowered.startswith("xai/") or "grok" in lowered


def _usable_decomposition_chain() -> list[str]:
    primary, fallback, tertiary = _decomposition_models()
    usable: list[str] = []
    seen: set[str] = set()
    for model in (primary, fallback, tertiary):
        if model in seen:
            continue
        seen.add(model)
        if model_slug_has_configured_credentials(model):
            usable.append(model)
    return usable


def _recommended_action(
    *,
    grok: bool,
    anthropic: bool,
    openai: bool,
    chain_usable: bool,
    grok_primary: bool,
) -> str:
    if not chain_usable:
        if grok:
            return (
                "Grok key saved but primary model is not routable — re-test in Settings → AI · LLM keys."
            )
        return "Add Grok API key in Settings → AI · LLM keys — primary provider for factory builds."

    if grok_primary and grok:
        return "Grok ready — run smoke test, then start factory builds."

    if openai:
        return "LLM ready — OpenAI configured. Run smoke test before bulk auto-build."

    if anthropic:
        return "Anthropic configured — run smoke test. Optional: add Grok or OpenAI as primary."

    return "LLM chain ready — run smoke test before factory builds."


async def resolve_factory_llm_readiness(session: AsyncSession) -> FactoryLlmReadinessOut:
    """Resolve credential presence for factory builds (no live smoke)."""

    await refresh_llm_secret_cache(session)
    grok = bool(provider_effective_grok())
    anthropic = bool(provider_effective_anthropic())
    openai = bool(provider_effective_openai())
    primary = settings.workflow_breaker_primary_model
    grok_primary = _is_grok_model_slug(primary)
    usable = _usable_decomposition_chain()
    chain_usable = bool(usable)
    build_allowed = chain_usable

    return FactoryLlmReadinessOut(
        grok_configured=grok,
        anthropic_configured=anthropic,
        openai_configured=openai,
        chain_usable=chain_usable,
        build_allowed=build_allowed,
        grok_primary=grok_primary,
        recommended_action=_recommended_action(
            grok=grok,
            anthropic=anthropic,
            openai=openai,
            chain_usable=chain_usable,
            grok_primary=grok_primary,
        ),
        decomposition_chain=usable,
    )


async def run_factory_llm_smoke(session: AsyncSession) -> FactoryLlmReadinessOut:
    """Run live LiteLLM ping and attach smoke_ok / smoke_error."""

    status = await resolve_factory_llm_readiness(session)
    if not status.build_allowed:
        return status.model_copy(
            update={
                "smoke_ok": False,
                "smoke_error": status.recommended_action,
            },
        )

    router = LiteLLMRouter()
    primary = settings.workflow_breaker_primary_model
    messages = [{"role": "user", "content": "Reply OK"}]
    grok_model = primary if _is_grok_model_slug(primary) else "xai/grok-3-mini"
    use_grok_only = status.grok_configured and _is_grok_model_slug(grok_model)

    try:
        if use_grok_only:
            await router.complete_single_model(
                session,
                model_name=grok_model,
                messages=messages,
                max_tokens=5,
                swarm_id="factory_llm_readiness",
                task_id="smoke",
            )
        else:
            await router.complete_with_fallback_messages(
                session,
                messages=messages,
                max_tokens=5,
                swarm_id="factory_llm_readiness",
                task_id="smoke",
            )
        return status.model_copy(update={"smoke_ok": True, "smoke_error": None})
    except Exception as exc:
        return status.model_copy(
            update={
                "smoke_ok": False,
                "smoke_error": str(exc)[:500],
            },
        )


async def assert_factory_build_llm_ready(session: AsyncSession) -> None:
    """Raise ValueError when factory build cannot proceed due to missing LLM."""

    status = await resolve_factory_llm_readiness(session)
    if status.build_allowed and status.chain_usable:
        return
    msg = status.recommended_action or "Factory LLM not configured."
    raise ValueError(msg)


__all__ = [
    "FactoryLlmReadinessOut",
    "assert_factory_build_llm_ready",
    "resolve_factory_llm_readiness",
    "run_factory_llm_smoke",
]
