"""Factory LLM readiness service unit tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.application.services.factory_llm_readiness_service import (
    FactoryLlmReadinessOut,
    assert_factory_build_llm_ready,
    resolve_factory_llm_readiness,
    run_factory_llm_smoke,
    save_factory_llm_primary,
)


@pytest.mark.asyncio
async def test_resolve_factory_llm_readiness_when_openai_configured() -> None:
    session = AsyncMock()

    with (
        patch(
            "app.application.services.factory_llm_readiness_service.refresh_llm_secret_cache",
            new=AsyncMock(),
        ),
        patch(
            "app.application.services.factory_llm_readiness_service.provider_effective_grok",
            return_value=False,
        ),
        patch(
            "app.application.services.factory_llm_readiness_service.provider_effective_anthropic",
            return_value=False,
        ),
        patch(
            "app.application.services.factory_llm_readiness_service.provider_effective_openai",
            return_value=True,
        ),
        patch(
            "app.application.services.factory_llm_readiness_service.model_slug_has_configured_credentials",
            return_value=True,
        ),
    ):
        status = await resolve_factory_llm_readiness(session)

    assert status.openai_configured is True
    assert status.build_allowed is True
    assert status.chain_usable is True
    assert "OpenAI" in status.recommended_action


@pytest.mark.asyncio
async def test_resolve_factory_llm_readiness_when_openrouter_primary() -> None:
    session = AsyncMock()

    with (
        patch(
            "app.application.services.factory_llm_readiness_service.refresh_llm_secret_cache",
            new=AsyncMock(),
        ),
        patch(
            "app.application.services.factory_llm_readiness_service.provider_effective_grok",
            return_value=False,
        ),
        patch(
            "app.application.services.factory_llm_readiness_service.provider_effective_anthropic",
            return_value=False,
        ),
        patch(
            "app.application.services.factory_llm_readiness_service.provider_effective_openai",
            return_value=False,
        ),
        patch(
            "app.application.services.factory_llm_readiness_service.provider_effective_openrouter",
            return_value=True,
        ),
        patch(
            "app.application.services.factory_llm_readiness_service.settings.workflow_breaker_primary_model",
            "openrouter/nvidia/nemotron-3-ultra-550b-a55b:free",
        ),
        patch(
            "app.application.services.factory_llm_readiness_service.model_slug_has_configured_credentials",
            return_value=True,
        ),
    ):
        status = await resolve_factory_llm_readiness(session)

    assert status.openrouter_configured is True
    assert status.openrouter_primary is True
    assert status.build_allowed is True
    assert "Nemotron" in status.recommended_action or "OpenRouter" in status.recommended_action


@pytest.mark.asyncio
async def test_resolve_factory_llm_readiness_when_no_providers() -> None:
    session = AsyncMock()

    with (
        patch(
            "app.application.services.factory_llm_readiness_service.refresh_llm_secret_cache",
            new=AsyncMock(),
        ),
        patch(
            "app.application.services.factory_llm_readiness_service.provider_effective_grok",
            return_value=False,
        ),
        patch(
            "app.application.services.factory_llm_readiness_service.provider_effective_anthropic",
            return_value=False,
        ),
        patch(
            "app.application.services.factory_llm_readiness_service.provider_effective_openai",
            return_value=False,
        ),
        patch(
            "app.application.services.factory_llm_readiness_service.model_slug_has_configured_credentials",
            return_value=False,
        ),
    ):
        status = await resolve_factory_llm_readiness(session)

    assert status.build_allowed is False
    assert status.chain_usable is False
    assert "Grok" in status.recommended_action or "OpenRouter" in status.recommended_action


@pytest.mark.asyncio
async def test_resolve_factory_llm_readiness_grok_only() -> None:
    session = AsyncMock()

    with (
        patch(
            "app.application.services.factory_llm_readiness_service.refresh_llm_secret_cache",
            new=AsyncMock(),
        ),
        patch(
            "app.application.services.factory_llm_readiness_service.provider_effective_grok",
            return_value=True,
        ),
        patch(
            "app.application.services.factory_llm_readiness_service.provider_effective_anthropic",
            return_value=True,
        ),
        patch(
            "app.application.services.factory_llm_readiness_service.provider_effective_openai",
            return_value=False,
        ),
        patch(
            "app.application.services.factory_llm_readiness_service.model_slug_has_configured_credentials",
            side_effect=lambda model: "grok" in model or model.startswith("xai/"),
        ),
    ):
        status = await resolve_factory_llm_readiness(session)

    assert status.grok_configured is True
    assert status.build_allowed is True
    assert status.grok_primary is True
    assert "Grok ready" in status.recommended_action
    assert "OpenAI" not in status.recommended_action


@pytest.mark.asyncio
async def test_run_factory_llm_smoke_uses_grok_only_when_primary() -> None:
    session = AsyncMock()
    router = MagicMock()
    router.complete_single_model = AsyncMock(return_value=("OK", 0.0))

    with (
        patch(
            "app.application.services.factory_llm_readiness_service.resolve_factory_llm_readiness",
            new=AsyncMock(
                return_value=FactoryLlmReadinessOut(
                    build_allowed=True,
                    chain_usable=True,
                    grok_configured=True,
                    grok_primary=True,
                    decomposition_chain=["xai/grok-3-mini"],
                ),
            ),
        ),
        patch(
            "app.application.services.factory_llm_readiness_service.model_slug_has_configured_credentials",
            return_value=True,
        ),
        patch(
            "app.application.services.factory_llm_readiness_service.LiteLLMRouter",
            return_value=router,
        ),
    ):
        status = await run_factory_llm_smoke(session)

    assert status.smoke_ok is True
    router.complete_single_model.assert_awaited_once()
    router.complete_with_fallback_messages.assert_not_called()


@pytest.mark.asyncio
async def test_assert_factory_build_llm_ready_raises_when_blocked() -> None:
    session = AsyncMock()

    with patch(
        "app.application.services.factory_llm_readiness_service.resolve_factory_llm_readiness",
        new=AsyncMock(
            return_value=FactoryLlmReadinessOut(
                build_allowed=False,
                chain_usable=False,
                recommended_action="Add Grok API key",
            ),
        ),
    ):
        with pytest.raises(ValueError, match="Grok"):
            await assert_factory_build_llm_ready(session)


@pytest.mark.asyncio
async def test_assert_factory_build_llm_ready_passes_when_ready() -> None:
    session = AsyncMock()

    with patch(
        "app.application.services.factory_llm_readiness_service.resolve_factory_llm_readiness",
        new=AsyncMock(
            return_value=FactoryLlmReadinessOut(
                build_allowed=True,
                chain_usable=True,
            ),
        ),
    ):
        await assert_factory_build_llm_ready(session)


@pytest.mark.asyncio
async def test_run_factory_llm_smoke_skips_ping_when_build_not_allowed() -> None:
    session = AsyncMock()

    with patch(
        "app.application.services.factory_llm_readiness_service.resolve_factory_llm_readiness",
        new=AsyncMock(
            return_value=FactoryLlmReadinessOut(
                build_allowed=False,
                recommended_action="Add OpenAI API key",
            ),
        ),
    ):
        status = await run_factory_llm_smoke(session)

    assert status.smoke_ok is False
    assert status.smoke_error == "Add OpenAI API key"


@pytest.mark.asyncio
async def test_run_factory_llm_smoke_success() -> None:
    session = AsyncMock()
    router = MagicMock()
    router.complete_with_fallback_messages = AsyncMock(return_value=("OK", 0.0))

    with (
        patch(
            "app.application.services.factory_llm_readiness_service.resolve_factory_llm_readiness",
            new=AsyncMock(
                return_value=FactoryLlmReadinessOut(
                    build_allowed=True,
                    chain_usable=True,
                    openai_configured=True,
                    grok_primary=False,
                ),
            ),
        ),
        patch(
            "app.application.services.factory_llm_readiness_service.model_slug_has_configured_credentials",
            return_value=False,
        ),
        patch(
            "app.application.services.factory_llm_readiness_service.LiteLLMRouter",
            return_value=router,
        ),
    ):
        status = await run_factory_llm_smoke(session)

    assert status.smoke_ok is True
    router.complete_with_fallback_messages.assert_awaited_once()


@pytest.mark.asyncio
async def test_save_factory_llm_primary_persists_tenant_selection() -> None:
    tenant_id = __import__("uuid").uuid4()
    tenant = MagicMock()
    tenant.operator_settings = {}
    session = AsyncMock()
    session.get = AsyncMock(return_value=tenant)

    saved = await save_factory_llm_primary(
        session,
        tenant_id=tenant_id,
        primary_model="openrouter/nvidia/nemotron-3-ultra-550b-a55b:free",
    )

    assert saved == "openrouter/nvidia/nemotron-3-ultra-550b-a55b:free"
    assert tenant.operator_settings["factory_llm"]["primary_model"] == saved
    session.flush.assert_awaited_once()
