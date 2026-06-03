"""Tenant policy for memory evolution proposal approvals."""

from __future__ import annotations

from typing import Any

from app.infrastructure.persistence.models.tenant import Tenant


def _memory_evolution_bucket(operator_settings: dict[str, Any] | None) -> dict[str, Any]:
    root = dict(operator_settings or {})
    bucket = root.get("memory_evolution")
    return dict(bucket) if isinstance(bucket, dict) else {}


def memory_evolution_policy(tenant: Tenant | None) -> dict[str, bool]:
    """Return tenant memory evolution approval policy with safe defaults."""

    bucket = _memory_evolution_bucket(tenant.operator_settings if tenant is not None else None)
    return {
        "auto_approve_enabled": bool(bucket.get("auto_approve_enabled", False)),
        "include_high_importance": bool(bucket.get("include_high_importance", False)),
    }


def tenant_memory_evolution_auto_approve_enabled(tenant: Tenant | None) -> bool:
    """Return True when tenant enables memory evolution auto-approve."""

    return bool(memory_evolution_policy(tenant).get("auto_approve_enabled"))


def merge_memory_evolution_policy_patch(
    operator_settings: dict[str, Any] | None,
    patch: dict[str, Any],
) -> dict[str, Any]:
    """Apply partial memory evolution policy patch into operator_settings."""

    root = dict(operator_settings or {})
    bucket = _memory_evolution_bucket(root)
    if "auto_approve_enabled" in patch:
        bucket["auto_approve_enabled"] = bool(patch["auto_approve_enabled"])
    if "include_high_importance" in patch:
        bucket["include_high_importance"] = bool(patch["include_high_importance"])
    root["memory_evolution"] = bucket
    return root


__all__ = [
    "memory_evolution_policy",
    "merge_memory_evolution_policy_patch",
    "tenant_memory_evolution_auto_approve_enabled",
]
