"""OP2 — Four-lane durable sessions use tenant Grok primary (no OpenRouter free fallback)."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.factory_llm_readiness_service import (
    _is_grok_model_slug,
    _is_openrouter_model_slug,
)
from app.core.config import settings
from app.core.litellm_model_registry import normalize_factory_model_slug
from app.core.llm_router import model_slug_has_configured_credentials

FOUR_LANE_LLM_BUCKET = "four_lane_llm"
FOUR_LANE_PAYLOAD_KEY = "four_lane_id"
DEFAULT_FOUR_LANE_GROK = "xai/grok-3-mini"


def is_four_lane_session(context_summary: dict[str, Any] | None) -> bool:
    """Return True when supervisor context is a solo-operator four-lane digest."""

    if not isinstance(context_summary, dict):
        return False
    if context_summary.get("solo_operator_four_lane") is True:
        return True
    return bool(str(context_summary.get(FOUR_LANE_PAYLOAD_KEY) or "").strip())


def build_four_lane_llm_context_seed() -> dict[str, object]:
    """Context keys merged into four-lane routine/session payloads (OP2)."""

    return {
        "solo_operator_four_lane": True,
        "four_lane_grok_primary": True,
        "llm_routing_mode_override": "quality",
    }


def _pick_grok_primary() -> str:
    """Resolve first usable Grok slug for four-lane AFK."""

    candidates = (
        settings.workflow_breaker_primary_model,
        DEFAULT_FOUR_LANE_GROK,
        "xai/grok-3",
    )
    seen: set[str] = set()
    for raw in candidates:
        slug = normalize_factory_model_slug(str(raw or "").strip())
        if not slug or slug in seen:
            continue
        seen.add(slug)
        if not _is_grok_model_slug(slug):
            continue
        if model_slug_has_configured_credentials(slug):
            return slug
    return normalize_factory_model_slug(DEFAULT_FOUR_LANE_GROK)


async def resolve_four_lane_primary_model(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID | None,
) -> str:
    """Tenant four-lane primary must be Grok when credentials exist — never OpenRouter free."""

    if tenant_id is not None:
        from app.infrastructure.persistence.models.tenant import Tenant

        tenant = await session.get(Tenant, tenant_id)
        if tenant is not None:
            block = dict((tenant.operator_settings or {}).get(FOUR_LANE_LLM_BUCKET) or {})
            raw = block.get("primary_model")
            if isinstance(raw, str) and raw.strip():
                slug = normalize_factory_model_slug(raw.strip())
                if _is_openrouter_model_slug(slug):
                    return _pick_grok_primary()
                if _is_grok_model_slug(slug) and model_slug_has_configured_credentials(slug):
                    return slug
    return _pick_grok_primary()


__all__ = [
    "FOUR_LANE_LLM_BUCKET",
    "build_four_lane_llm_context_seed",
    "is_four_lane_session",
    "resolve_four_lane_primary_model",
]
