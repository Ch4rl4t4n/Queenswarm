"""Unit tests for Stripe vault credential helpers."""

from __future__ import annotations

import pytest

from app.application.services import stripe_runtime_credentials as svc
from app.core.config import settings


def test_validate_stripe_secret_key_when_rk_prefix_then_accepts() -> None:
    """Restricted keys (recommended) should pass validation."""

    assert svc.validate_stripe_secret_key("rk_live_" + "a" * 24).startswith("rk_live_")


def test_validate_stripe_secret_key_when_invalid_prefix_then_raises() -> None:
    """Reject malformed Stripe secret material."""

    with pytest.raises(ValueError, match="sk_ or rk_"):
        svc.validate_stripe_secret_key("pk_live_invalid")


def test_stripe_effective_secret_key_when_vault_cached_then_overrides_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """In-memory vault cache takes precedence over env Settings."""

    monkeypatch.setattr(settings, "stripe_secret_key", "sk_live_from_env")
    monkeypatch.setattr(svc, "_cache", {"secret_key": "sk_live_from_vault"})
    assert svc.stripe_effective_secret_key() == "sk_live_from_vault"
    assert svc.stripe_secret_key_source() == "vault"


def test_mask_stripe_material_when_long_key_then_masks_prefix() -> None:
    """Operator UI should only reveal last four characters."""

    assert svc.mask_stripe_material("sk_live_abc1234567890").endswith("7890")
    assert svc.mask_stripe_material("sk_live_abc1234567890").startswith("••••")
