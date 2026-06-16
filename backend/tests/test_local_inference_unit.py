"""Unit tests for Track M local inference service."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from app.application.services.local_inference import (
    assert_model_allowed_when_airgap,
    compose_local_inference_status,
    configured_local_model_slugs,
    enrich_litellm_completion_kwargs,
    is_local_inference_model,
    ping_ollama,
    resolve_ollama_model_slug,
)
from app.core.config import settings


def test_is_local_inference_model_for_ollama_slug() -> None:
    assert is_local_inference_model("ollama/qwen2.5:7b") is True
    assert is_local_inference_model("xai/grok-3-mini") is False


def test_configured_local_model_slugs_includes_ollama(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "local_llm_enabled", True)
    monkeypatch.setattr(settings, "ollama_api_base", "http://127.0.0.1:11434")
    monkeypatch.setattr(settings, "vllm_api_base", "")
    slugs = configured_local_model_slugs()
    assert resolve_ollama_model_slug() in slugs


def test_enrich_litellm_completion_kwargs_sets_ollama_base(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "ollama_api_base", "http://localhost:11434")
    kwargs: dict[str, str] = {"model": "ollama/llama3.2", "api_key": ""}
    enrich_litellm_completion_kwargs(kwargs, "ollama/llama3.2")
    assert kwargs["api_base"] == "http://localhost:11434"
    assert kwargs["api_key"] == "ollama"


def test_assert_model_allowed_when_airgap_blocks_cloud(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "llm_airgap", True)
    with pytest.raises(RuntimeError, match="LLM_AIRGAP"):
        assert_model_allowed_when_airgap("xai/grok-3-mini")


def test_observe_llm_local_inference_increments_counter() -> None:
    from app.core.metrics import LLM_LOCAL_INFERENCE_TOTAL, observe_llm_local_inference

    before = LLM_LOCAL_INFERENCE_TOTAL.labels(model="ollama/qwen2.5:7b")._value.get()  # noqa: SLF001
    observe_llm_local_inference(model_name="ollama/qwen2.5:7b")
    after = LLM_LOCAL_INFERENCE_TOTAL.labels(model="ollama/qwen2.5:7b")._value.get()  # noqa: SLF001
    assert after >= before + 1


@pytest.mark.asyncio
async def test_compose_local_inference_status_without_ping(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "local_llm_enabled", True)
    monkeypatch.setattr(settings, "ollama_api_base", "http://127.0.0.1:11434")
    status = await compose_local_inference_status(run_ping=False)
    assert status.enabled is True
    assert status.pings == []
    assert resolve_ollama_model_slug() in status.configured_models


def test_configured_local_model_slugs_merges_extra(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "local_llm_enabled", True)
    monkeypatch.setattr(settings, "ollama_api_base", "http://127.0.0.1:11434")
    monkeypatch.setattr(settings, "vllm_api_base", "")
    base = resolve_ollama_model_slug()
    slugs = configured_local_model_slugs(extra_slugs=[base, "ollama/queenswarm-v1"])
    assert slugs.count(base) == 1
    assert "ollama/queenswarm-v1" in slugs


@pytest.mark.asyncio
async def test_compose_local_inference_status_with_extra_slugs(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "local_llm_enabled", True)
    monkeypatch.setattr(settings, "ollama_api_base", "http://127.0.0.1:11434")
    status = await compose_local_inference_status(
        run_ping=False,
        extra_model_slugs=["ollama/queenswarm-v1"],
    )
    assert "ollama/queenswarm-v1" in status.configured_models


@pytest.mark.asyncio
async def test_ping_ollama_success(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "ollama_api_base", "http://127.0.0.1:11434")

    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, list[dict[str, str]]]:
            return {"models": [{"name": "qwen2.5:7b"}]}

    class FakeClient:
        async def __aenter__(self) -> FakeClient:
            return self

        async def __aexit__(self, *args: object) -> None:
            return None

        async def get(self, url: str) -> FakeResponse:
            return FakeResponse()

    with patch("app.application.services.local_inference.httpx.AsyncClient", return_value=FakeClient()):
        result = await ping_ollama()
    assert result.ok is True
    assert result.model_count == 1
