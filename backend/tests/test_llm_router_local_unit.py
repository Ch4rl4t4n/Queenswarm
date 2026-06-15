"""Unit tests for Ollama local routing in LiteLLMRouter."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from app.application.services.llm_routing import ordered_model_chain
from app.core.llm_router import LiteLLMRouter, model_api_key, model_slug_has_configured_credentials
from app.core.config import settings


def test_model_api_key_for_ollama_returns_dummy() -> None:
    assert model_api_key("ollama/qwen2.5:7b") == "ollama"


def test_model_slug_has_configured_credentials_for_ollama(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "local_llm_enabled", True)
    monkeypatch.setattr(settings, "ollama_api_base", "http://127.0.0.1:11434")
    assert model_slug_has_configured_credentials("ollama/qwen2.5:7b") is True


def test_model_slug_has_configured_credentials_cloud_false_when_airgap(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "llm_airgap", True)
    with patch("app.core.llm_router.provider_effective_grok", return_value="sk-test"):
        assert model_slug_has_configured_credentials("xai/grok-3-mini") is False


def test_ordered_model_chain_local_sovereign_preserves_local_only() -> None:
    chain = ordered_model_chain(
        routing_mode="local_sovereign",
        primary="ollama/qwen2.5:7b",
        fallback="",
        tertiary="",
        usable=["ollama/qwen2.5:7b"],
    )
    assert chain == ["ollama/qwen2.5:7b"]


def test_decomposition_chain_local_sovereign_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "local_llm_enabled", True)
    monkeypatch.setattr(settings, "ollama_api_base", "http://127.0.0.1:11434")
    monkeypatch.setattr(settings, "ollama_default_model", "ollama/qwen2.5:7b")
    monkeypatch.setattr(settings, "vllm_api_base", "")
    router = LiteLLMRouter()
    chain = router._decomposition_chain(routing_mode="local_sovereign")
    assert chain == ["ollama/qwen2.5:7b"]
