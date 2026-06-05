"""Register factory / OpenRouter slugs missing from LiteLLM's bundled cost map."""

from __future__ import annotations

import litellm

_REGISTERED = False

# Slugs used by Skill Factory picker + WORKFLOW_BREAKER_* env defaults.
_FACTORY_MODEL_REGISTRY: dict[str, dict[str, object]] = {
    "openrouter/nvidia/nemotron-3-ultra-550b-a55b:free": {
        "max_tokens": 131_072,
        "max_input_tokens": 131_072,
        "max_output_tokens": 16_384,
        "input_cost_per_token": 0.0,
        "output_cost_per_token": 0.0,
        "litellm_provider": "openrouter",
        "mode": "chat",
    },
    "xai/grok-3-mini": {
        "max_tokens": 131_072,
        "max_input_tokens": 131_072,
        "max_output_tokens": 16_384,
        "input_cost_per_token": 0.0,
        "output_cost_per_token": 0.0,
        "litellm_provider": "xai",
        "mode": "chat",
    },
    "xai/grok-3": {
        "max_tokens": 131_072,
        "max_input_tokens": 131_072,
        "max_output_tokens": 16_384,
        "input_cost_per_token": 0.0,
        "output_cost_per_token": 0.0,
        "litellm_provider": "xai",
        "mode": "chat",
    },
}

# Legacy typo guard — auto-correct if stored in tenant settings.
FACTORY_MODEL_SLUG_ALIASES: dict[str, str] = {
    "openrouter/nvidia/nematron-3-ultra-550b-a55b:free": "openrouter/nvidia/nemotron-3-ultra-550b-a55b:free",
}


def normalize_factory_model_slug(model_name: str) -> str:
    """Map known typos / legacy slugs to canonical LiteLLM model ids."""

    cleaned = model_name.strip()
    return FACTORY_MODEL_SLUG_ALIASES.get(cleaned, cleaned)


def register_litellm_factory_models() -> None:
    """Idempotently register factory model pricing metadata for LiteLLM routing."""

    global _REGISTERED
    if _REGISTERED:
        return
    litellm.register_model(_FACTORY_MODEL_REGISTRY)
    _REGISTERED = True


__all__ = [
    "FACTORY_MODEL_SLUG_ALIASES",
    "normalize_factory_model_slug",
    "register_litellm_factory_models",
]
