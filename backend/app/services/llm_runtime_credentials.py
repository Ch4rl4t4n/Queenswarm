"""Backward-compatible re-export — single in-process LLM secret cache.

``llm_router`` and dashboard services must share one ``_cache``; duplicate modules
previously caused vault Grok keys to be invisible to decomposition routing.
"""

from __future__ import annotations

from app.application.services.llm_runtime_credentials import (
    apply_llm_cache_to_environ,
    delete_llm_provider_secret,
    get_cached_llm_key,
    persist_llm_provider_secret,
    provider_effective_anthropic,
    provider_effective_deepgram,
    provider_effective_elevenlabs,
    provider_effective_grok,
    provider_effective_openai,
    refresh_llm_secret_cache,
)

__all__ = [
    "apply_llm_cache_to_environ",
    "delete_llm_provider_secret",
    "get_cached_llm_key",
    "persist_llm_provider_secret",
    "provider_effective_anthropic",
    "provider_effective_deepgram",
    "provider_effective_elevenlabs",
    "provider_effective_grok",
    "provider_effective_openai",
    "refresh_llm_secret_cache",
]
