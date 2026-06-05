"""LiteLLM factory model registry unit tests."""

from __future__ import annotations

from app.core.litellm_model_registry import (
    normalize_factory_model_slug,
    register_litellm_factory_models,
)


def test_normalize_factory_model_slug_fixes_nematron_typo() -> None:
    assert (
        normalize_factory_model_slug("openrouter/nvidia/nematron-3-ultra-550b-a55b:free")
        == "openrouter/nvidia/nemotron-3-ultra-550b-a55b:free"
    )


def test_register_litellm_factory_models_is_idempotent() -> None:
    register_litellm_factory_models()
    register_litellm_factory_models()
