"""Shared factory LLM credential readiness — Skill + Content Pack factories."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict, Field

from app.application.services.llm_runtime_credentials import (
    provider_effective_anthropic,
    provider_effective_grok,
    provider_effective_openai,
    provider_effective_openrouter,
    refresh_llm_secret_cache,
)
from app.core.config import settings
from app.core.litellm_model_registry import normalize_factory_model_slug
from app.core.llm_router import LiteLLMRouter, model_slug_has_configured_credentials
from sqlalchemy.ext.asyncio import AsyncSession

FACTORY_LLM_PRESET_OPTIONS: tuple[tuple[str, str], ...] = (
    ("openrouter/nvidia/nemotron-3-ultra-550b-a55b:free", "Nemotron 3 Ultra (OpenRouter · free)"),
    ("xai/grok-3-mini", "Grok 3 Mini (xAI)"),
    ("xai/grok-3", "Grok 3 (xAI)"),
    ("openai/gpt-4o-mini", "GPT-4o mini (OpenAI)"),
    ("anthropic/claude-haiku-4-5-20251001", "Claude Haiku 4.5"),
)


class FactoryLlmOptionOut(BaseModel):
    """Selectable factory primary model."""

    model_config = ConfigDict(extra="ignore")

    value: str
    label: str
    configured: bool = False


class FactoryLlmReadinessOut(BaseModel):
    """LLM decomposition readiness for factory build lanes."""

    model_config = ConfigDict(extra="ignore")

    grok_configured: bool = False
    anthropic_configured: bool = False
    openai_configured: bool = False
    openrouter_configured: bool = False
    chain_usable: bool = False
    build_allowed: bool = False
    grok_primary: bool = False
    openrouter_primary: bool = False
    primary_model: str = ""
    recommended_action: str = ""
    decomposition_chain: list[str] = Field(default_factory=list)
    available_models: list[FactoryLlmOptionOut] = Field(default_factory=list)
    smoke_ok: bool | None = None
    smoke_error: str | None = None


def _decomposition_models(*, primary_override: str | None = None) -> tuple[str, str, str]:
    primary = primary_override or settings.workflow_breaker_primary_model
    return (
        primary,
        settings.workflow_breaker_fallback_model,
        settings.workflow_breaker_tertiary_model,
    )


def _is_grok_model_slug(model_name: str) -> bool:
    lowered = model_name.lower()
    return lowered.startswith("xai/") or "grok" in lowered


def _is_openrouter_model_slug(model_name: str) -> bool:
    return model_name.lower().startswith("openrouter/")


def _allowed_factory_primary_models() -> set[str]:
    allowed = {slug for slug, _ in FACTORY_LLM_PRESET_OPTIONS}
    allowed.update(
        {
            settings.workflow_breaker_primary_model,
            settings.workflow_breaker_fallback_model,
            settings.workflow_breaker_tertiary_model,
        },
    )
    return allowed


def _usable_decomposition_chain(*, primary_override: str | None = None) -> list[str]:
    primary, fallback, tertiary = _decomposition_models(primary_override=primary_override)
    usable: list[str] = []
    seen: set[str] = set()
    for model in (primary, fallback, tertiary):
        if model in seen:
            continue
        seen.add(model)
        if model_slug_has_configured_credentials(model):
            usable.append(model)
    return usable


def _available_model_options() -> list[FactoryLlmOptionOut]:
    return [
        FactoryLlmOptionOut(
            value=slug,
            label=label,
            configured=model_slug_has_configured_credentials(slug),
        )
        for slug, label in FACTORY_LLM_PRESET_OPTIONS
    ]


def _recommended_action(
    *,
    grok: bool,
    anthropic: bool,
    openai: bool,
    openrouter: bool,
    chain_usable: bool,
    grok_primary: bool,
    openrouter_primary: bool,
    primary_model: str,
) -> str:
    if not chain_usable:
        if openrouter_primary and openrouter:
            return (
                "OpenRouter key saved but primary model is not routable — re-test in Settings → AI · LLM keys."
            )
        if grok_primary and grok:
            return (
                "Grok key saved but primary model is not routable — re-test in Settings → AI · LLM keys."
            )
        if openrouter:
            return "Add OpenRouter API key in Settings → AI · LLM keys — primary provider for factory builds."
        return "Add Grok or OpenRouter API key in Settings → AI · LLM keys — required for factory builds."

    if openrouter_primary and openrouter:
        return f"Nemotron/OpenRouter ready ({primary_model}) — run smoke test, then start factory builds."

    if grok_primary and grok:
        return f"Grok ready ({primary_model}) — run smoke test, then start factory builds."

    if openai:
        return f"LLM ready — OpenAI configured ({primary_model}). Run smoke test before bulk auto-build."

    if anthropic:
        return f"Anthropic configured ({primary_model}) — run smoke test. Optional: add Grok or OpenRouter as primary."

    return f"LLM chain ready ({primary_model}) — run smoke test before factory builds."


async def resolve_effective_factory_primary_model(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID | None = None,
) -> str:
    """Tenant-selected factory primary, else deployment WORKFLOW_BREAKER_PRIMARY_MODEL."""

    if tenant_id is not None:
        from app.infrastructure.persistence.models.tenant import Tenant

        tenant = await session.get(Tenant, tenant_id)
        if tenant is not None:
            block = dict((tenant.operator_settings or {}).get("factory_llm") or {})
            raw = block.get("primary_model")
            if isinstance(raw, str) and raw.strip():
                return normalize_factory_model_slug(raw)
    return normalize_factory_model_slug(settings.workflow_breaker_primary_model)


async def save_factory_llm_primary(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    primary_model: str,
) -> str:
    """Persist tenant factory primary model selection."""

    cleaned = normalize_factory_model_slug(primary_model)
    if cleaned not in _allowed_factory_primary_models():
        raise ValueError(f"Unsupported factory LLM model: {primary_model}")

    from app.infrastructure.persistence.models.tenant import Tenant

    tenant = await session.get(Tenant, tenant_id)
    if tenant is None:
        raise ValueError("Tenant not found.")

    settings_block = dict(tenant.operator_settings or {})
    factory_block = dict(settings_block.get("factory_llm") or {})
    factory_block["primary_model"] = cleaned
    settings_block["factory_llm"] = factory_block
    tenant.operator_settings = settings_block
    await session.flush()
    return cleaned


async def resolve_factory_llm_readiness(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID | None = None,
) -> FactoryLlmReadinessOut:
    """Resolve credential presence for factory builds (no live smoke)."""

    await refresh_llm_secret_cache(session)
    grok = bool(provider_effective_grok())
    anthropic = bool(provider_effective_anthropic())
    openai = bool(provider_effective_openai())
    openrouter = bool(provider_effective_openrouter())
    primary = await resolve_effective_factory_primary_model(session, tenant_id=tenant_id)
    grok_primary = _is_grok_model_slug(primary)
    openrouter_primary = _is_openrouter_model_slug(primary)
    usable = _usable_decomposition_chain(primary_override=primary)
    chain_usable = bool(usable)
    build_allowed = chain_usable

    return FactoryLlmReadinessOut(
        grok_configured=grok,
        anthropic_configured=anthropic,
        openai_configured=openai,
        openrouter_configured=openrouter,
        chain_usable=chain_usable,
        build_allowed=build_allowed,
        grok_primary=grok_primary,
        openrouter_primary=openrouter_primary,
        primary_model=primary,
        recommended_action=_recommended_action(
            grok=grok,
            anthropic=anthropic,
            openai=openai,
            openrouter=openrouter,
            chain_usable=chain_usable,
            grok_primary=grok_primary,
            openrouter_primary=openrouter_primary,
            primary_model=primary,
        ),
        decomposition_chain=usable,
        available_models=_available_model_options(),
    )


async def run_factory_llm_smoke(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID | None = None,
) -> FactoryLlmReadinessOut:
    """Run live LiteLLM ping and attach smoke_ok / smoke_error."""

    status = await resolve_factory_llm_readiness(session, tenant_id=tenant_id)
    if not status.build_allowed:
        return status.model_copy(
            update={
                "smoke_ok": False,
                "smoke_error": status.recommended_action,
            },
        )

    router = LiteLLMRouter()
    primary = status.primary_model
    messages = [{"role": "user", "content": "Reply OK"}]
    use_primary_only = model_slug_has_configured_credentials(primary)

    try:
        if use_primary_only:
            await router.complete_single_model(
                session,
                model_name=primary,
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
                primary_override=primary,
            )
        return status.model_copy(update={"smoke_ok": True, "smoke_error": None})
    except Exception as exc:
        return status.model_copy(
            update={
                "smoke_ok": False,
                "smoke_error": str(exc)[:500],
            },
        )


def validate_factory_critic_model(model: str) -> str:
    """Normalize and validate a factory/eval critic model slug."""

    cleaned = normalize_factory_model_slug(model.strip())
    if cleaned not in _allowed_factory_primary_models():
        raise ValueError(f"unsupported_critic_model:{model}")
    if not model_slug_has_configured_credentials(cleaned):
        raise ValueError(f"critic_model_not_configured:{cleaned}")
    return cleaned


async def resolve_factory_critic_model(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID | None,
    critic_model: str | None,
) -> str:
    """Resolve eval/factory critic model — explicit override or tenant primary."""

    if critic_model and critic_model.strip():
        return validate_factory_critic_model(critic_model)
    if tenant_id is not None:
        return await resolve_effective_factory_primary_model(session, tenant_id=tenant_id)
    return normalize_factory_model_slug(settings.workflow_breaker_primary_model)


async def assert_factory_build_llm_ready(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID | None = None,
) -> None:
    """Raise ValueError when factory build cannot proceed due to missing LLM."""

    status = await resolve_factory_llm_readiness(session, tenant_id=tenant_id)
    if status.build_allowed and status.chain_usable:
        return
    msg = status.recommended_action or "Factory LLM not configured."
    raise ValueError(msg)


__all__ = [
    "FACTORY_LLM_PRESET_OPTIONS",
    "FactoryLlmOptionOut",
    "FactoryLlmReadinessOut",
    "assert_factory_build_llm_ready",
    "resolve_effective_factory_primary_model",
    "resolve_factory_critic_model",
    "resolve_factory_llm_readiness",
    "run_factory_llm_smoke",
    "save_factory_llm_primary",
    "validate_factory_critic_model",
]
