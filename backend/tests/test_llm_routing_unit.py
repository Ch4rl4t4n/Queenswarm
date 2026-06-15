"""Unit tests for LLM routing mode ordering."""

from __future__ import annotations

from app.application.services.llm_routing import normalize_routing_mode, ordered_model_chain
from app.application.services.platform_features import resolve_platform_features


def test_normalize_routing_mode_defaults_unknown_to_quality() -> None:
    assert normalize_routing_mode("nope") == "quality"
    assert normalize_routing_mode("economy") == "economy"


def test_ordered_model_chain_economy_puts_tertiary_first() -> None:
    chain = ordered_model_chain(
        routing_mode="economy",
        primary="xai/grok-3-mini",
        fallback="anthropic/claude-haiku",
        tertiary="openai/gpt-4o-mini",
        usable=["xai/grok-3-mini", "anthropic/claude-haiku", "openai/gpt-4o-mini"],
    )
    assert chain[0] == "openai/gpt-4o-mini"
    assert chain[-1] == "xai/grok-3-mini"


def test_ordered_model_chain_quality_keeps_primary_first() -> None:
    chain = ordered_model_chain(
        routing_mode="quality",
        primary="xai/grok-3-mini",
        fallback="anthropic/claude-haiku",
        tertiary="openai/gpt-4o-mini",
        usable=["xai/grok-3-mini", "openai/gpt-4o-mini"],
    )
    assert chain[0] == "xai/grok-3-mini"


def test_normalize_routing_mode_accepts_local_sovereign() -> None:
    assert normalize_routing_mode("local_sovereign") == "local_sovereign"


def test_merge_routing_patch_persists_local_sovereign() -> None:
    from app.application.services.llm_routing import merge_routing_patch

    updated = merge_routing_patch({}, {"routing_mode": "local_sovereign"})
    assert updated["llm_routing"]["routing_mode"] == "local_sovereign"


def test_ordered_model_chain_local_sovereign_returns_usable_only() -> None:
    chain = ordered_model_chain(
        routing_mode="local_sovereign",
        primary="xai/grok-3-mini",
        fallback="anthropic/claude-haiku",
        tertiary="openai/gpt-4o-mini",
        usable=["ollama/qwen2.5:7b"],
    )
    assert chain == ["ollama/qwen2.5:7b"]


def test_commercial_free_gets_free_first_routing_feature() -> None:
    features = resolve_platform_features(
        platform_mode="commercial",
        is_admin=False,
        subscription_tier="free",
    )
    assert features["free_first_routing"] is True
