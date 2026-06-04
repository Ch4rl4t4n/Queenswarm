"""Operator LLM keys router regression tests."""

from __future__ import annotations

from unittest.mock import MagicMock

from app.presentation.api.routers.operator_llm_keys import _provider_label_model


def test_provider_label_model_returns_three_tuple() -> None:
    user = MagicMock()
    user.notification_prefs = {
        "llm_operator_labels": {
            "grok": {"label": "Primary", "model_default": "xai/grok-3-mini", "is_primary": True},
        },
    }
    label, model, is_primary = _provider_label_model(user, "grok")
    assert label == "Primary"
    assert model == "xai/grok-3-mini"
    assert is_primary is True


def test_provider_label_model_unpack_pattern_used_in_test_endpoint() -> None:
    """Guard against ValueError: too many values to unpack in test_llm_operator_key."""

    user = MagicMock()
    user.notification_prefs = {}
    _, model_hint, _ = _provider_label_model(user, "openai")
    assert model_hint is None


def test_provider_label_model_openrouter_is_not_primary_by_default() -> None:
    user = MagicMock()
    user.notification_prefs = {}

    label, model_hint, is_primary = _provider_label_model(user, "openrouter")

    assert label == ""
    assert model_hint is None
    assert is_primary is False
