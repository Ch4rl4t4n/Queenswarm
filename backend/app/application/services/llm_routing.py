"""Tenant-scoped LiteLLM routing mode (quality / economy / free_first)."""

from __future__ import annotations

from typing import Any, Literal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger
from app.core.tenant_context import get_current_tenant_uuid
from app.infrastructure.persistence.models.tenant import Tenant

LlmRoutingMode = Literal["quality", "economy", "free_first"]

LLM_ROUTING_BUCKET = "llm_routing"
DEFAULT_ROUTING_MODE: LlmRoutingMode = "quality"

logger = get_logger(__name__)


def normalize_routing_mode(raw: object) -> LlmRoutingMode:
    """Coerce stored value to a supported routing mode."""

    text = str(raw or DEFAULT_ROUTING_MODE).strip().lower()
    if text in {"quality", "economy", "free_first"}:
        return text  # type: ignore[return-value]
    return DEFAULT_ROUTING_MODE


def _routing_bucket(operator_settings: dict[str, Any] | None) -> dict[str, Any]:
    root = dict(operator_settings or {})
    bucket = root.get(LLM_ROUTING_BUCKET)
    return dict(bucket) if isinstance(bucket, dict) else {}


def routing_config_from_tenant(tenant: Tenant | None) -> dict[str, Any]:
    """Read routing config dict from a tenant row."""

    bucket = _routing_bucket(tenant.operator_settings if tenant is not None else None)
    return {
        "routing_mode": normalize_routing_mode(bucket.get("routing_mode")),
        "cost_guardian_enabled": bool(bucket.get("cost_guardian_enabled", True)),
        "auto_upgrade_on_failure": bool(bucket.get("auto_upgrade_on_failure", True)),
    }


async def load_routing_config(session: AsyncSession, *, tenant_id: object | None = None) -> dict[str, Any]:
    """Load effective routing config for tenant context or explicit id."""

    if not settings.free_first_routing_enabled:
        return {
            "routing_mode": DEFAULT_ROUTING_MODE,
            "cost_guardian_enabled": True,
            "auto_upgrade_on_failure": True,
            "feature_enabled": False,
        }

    resolved_id = tenant_id or get_current_tenant_uuid()
    if resolved_id is None:
        return {
            "routing_mode": DEFAULT_ROUTING_MODE,
            "cost_guardian_enabled": True,
            "auto_upgrade_on_failure": True,
            "feature_enabled": True,
        }

    tenant = await session.get(Tenant, resolved_id)
    cfg = routing_config_from_tenant(tenant)
    cfg["feature_enabled"] = True
    return cfg


def merge_routing_patch(operator_settings: dict[str, Any] | None, patch: dict[str, Any]) -> dict[str, Any]:
    """Apply partial llm_routing patch and return updated operator_settings root."""

    root = dict(operator_settings or {})
    bucket = _routing_bucket(root)
    if "routing_mode" in patch:
        bucket["routing_mode"] = normalize_routing_mode(patch["routing_mode"])
    if "cost_guardian_enabled" in patch:
        bucket["cost_guardian_enabled"] = bool(patch["cost_guardian_enabled"])
    if "auto_upgrade_on_failure" in patch:
        bucket["auto_upgrade_on_failure"] = bool(patch["auto_upgrade_on_failure"])
    root[LLM_ROUTING_BUCKET] = bucket
    return root


def ordered_model_chain(
    *,
    routing_mode: LlmRoutingMode,
    primary: str,
    fallback: str,
    tertiary: str,
    usable: list[str],
) -> list[str]:
    """Reorder configured model slugs for the selected routing mode."""

    tier_map = {primary: "primary", fallback: "fallback", tertiary: "tertiary"}
    ordered_tiers: list[str]
    if routing_mode == "quality":
        ordered_tiers = ["primary", "fallback", "tertiary"]
    else:
        ordered_tiers = ["tertiary", "fallback", "primary"]

    slug_by_tier = {
        "primary": primary,
        "fallback": fallback,
        "tertiary": tertiary,
    }
    out: list[str] = []
    seen: set[str] = set()
    for tier in ordered_tiers:
        slug = slug_by_tier[tier]
        if slug not in usable or slug in seen:
            continue
        seen.add(slug)
        out.append(slug)
    for slug in usable:
        if slug not in seen:
            seen.add(slug)
            out.append(slug)
    logger.debug(
        "llm_routing.chain",
        routing_mode=routing_mode,
        chain=out,
        tiers={slug: tier_map.get(slug, "?") for slug in out},
    )
    return out


__all__ = [
    "DEFAULT_ROUTING_MODE",
    "LLM_ROUTING_BUCKET",
    "LlmRoutingMode",
    "load_routing_config",
    "merge_routing_patch",
    "normalize_routing_mode",
    "ordered_model_chain",
    "routing_config_from_tenant",
]
