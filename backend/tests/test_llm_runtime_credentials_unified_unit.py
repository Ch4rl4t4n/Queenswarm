"""Ensure LLM vault cache is shared between router and dashboard services."""

from __future__ import annotations

import app.application.services.llm_runtime_credentials as app_creds
import app.services.llm_runtime_credentials as router_creds
from app.core.llm_router import model_slug_has_configured_credentials


def test_router_and_application_share_grok_cache(monkeypatch) -> None:
    """Vault Grok key loaded into application cache must be visible to llm_router."""

    app_creds._cache["grok"] = "xai-test-key-123456789012345678901234567890"
    app_creds.apply_llm_cache_to_environ()

    assert router_creds.get_cached_llm_key("grok") == app_creds.get_cached_llm_key("grok")
    assert router_creds.provider_effective_grok() == app_creds.provider_effective_grok()
    assert model_slug_has_configured_credentials("xai/grok-3-mini") is True

    app_creds._cache.pop("grok", None)
    app_creds.apply_llm_cache_to_environ()
