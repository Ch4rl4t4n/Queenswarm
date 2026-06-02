"""Tenant policy for forager auto-spawn approval (manual vs auto)."""

from __future__ import annotations

from typing import Any

from app.infrastructure.persistence.models.tenant import Tenant


def _foragers_bucket(operator_settings: dict[str, Any] | None) -> dict[str, Any]:
    root = dict(operator_settings or {})
    bucket = root.get("foragers")
    return dict(bucket) if isinstance(bucket, dict) else {}


def forager_spawn_policy(tenant: Tenant | None) -> dict[str, bool]:
    """Return tenant forager spawn approval policy with safe defaults."""

    bucket = _foragers_bucket(tenant.operator_settings if tenant is not None else None)
    return {
        "auto_spawn_auto_approve_enabled": bool(bucket.get("auto_spawn_auto_approve_enabled", False)),
    }


def merge_forager_spawn_policy_patch(operator_settings: dict[str, Any] | None, patch: dict[str, Any]) -> dict[str, Any]:
    """Apply partial forager spawn policy patch into operator_settings."""

    root = dict(operator_settings or {})
    bucket = _foragers_bucket(root)
    if "auto_spawn_auto_approve_enabled" in patch:
        bucket["auto_spawn_auto_approve_enabled"] = bool(patch["auto_spawn_auto_approve_enabled"])
    root["foragers"] = bucket
    return root


__all__ = ["forager_spawn_policy", "merge_forager_spawn_policy_patch"]
