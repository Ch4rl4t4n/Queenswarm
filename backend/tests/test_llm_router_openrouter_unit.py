"""Unit tests for OpenRouter/Nemotron LiteLLM routing support."""

from __future__ import annotations

from unittest.mock import patch

from app.core.llm_router import model_api_key, model_slug_has_configured_credentials


def test_model_api_key_resolves_openrouter_provider() -> None:
    with patch("app.core.llm_router.provider_effective_openrouter", return_value="sk-or-test"):
        assert model_api_key("openrouter/nvidia/nemotron-3-ultra-550b-a55b:free") == "sk-or-test"


def test_model_slug_has_configured_credentials_accepts_openrouter_slugs() -> None:
    with patch("app.core.llm_router.provider_effective_openrouter", return_value="sk-or-test"):
        assert model_slug_has_configured_credentials("openrouter/nvidia/nemotron-3-ultra-550b-a55b:free") is True
