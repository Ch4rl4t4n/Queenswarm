"""Track M LOC13 — Analytics workspace local sovereign inference integration."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.llm_routing import load_routing_config
from app.core.config import settings
from app.core.logging import get_logger

_logger = get_logger(__name__)


class AnalyticsLocalInferenceOut(BaseModel):
    """Resolved local inference lane for analytics bees."""

    model_config = ConfigDict(extra="forbid")

    active: bool = False
    routing_mode: str = "quality"
    local_model_slug: str | None = None
    airgap: bool = False
    operator_hint: str = ""


def _local_model_slug() -> str:
    slug = (settings.ollama_default_model or "").strip()
    return slug or "ollama/qwen2.5:7b"


async def resolve_analytics_local_inference(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID | None,
) -> AnalyticsLocalInferenceOut:
    """Return whether analytics sessions should prefer local Ollama in sovereign mode."""

    if not settings.analytics_local_sovereign_prefer_enabled:
        return AnalyticsLocalInferenceOut(
            operator_hint="Analytics local sovereign prefer disabled.",
        )

    if not settings.local_llm_enabled:
        return AnalyticsLocalInferenceOut(
            operator_hint="Local LLM path disabled — enable LOCAL_LLM_ENABLED.",
        )

    airgap = bool(settings.llm_airgap)
    routing_mode = "quality"
    if airgap:
        sovereign = True
        routing_mode = "local_sovereign"
    elif tenant_id is not None:
        cfg = await load_routing_config(session, tenant_id=tenant_id)
        routing_mode = str(cfg.get("routing_mode") or "quality")
        sovereign = routing_mode == "local_sovereign"
    else:
        sovereign = False

    if not sovereign:
        return AnalyticsLocalInferenceOut(
            routing_mode=routing_mode,
            operator_hint=(
                "Cloud routing active — set Cost Guardian to local_sovereign for offline analytics bees."
            ),
        )

    model_slug = _local_model_slug()
    hint = (
        f"Local sovereign — analytics bees use {model_slug} ($0 hops). "
        "Critic and simulate gates unchanged."
    )
    if airgap:
        hint = f"LLM_AIRGAP=1 — {hint}"

    _logger.info(
        "analytics_local_inference.resolved",
        agent_id="analytics_local_inference",
        swarm_id=str(tenant_id) if tenant_id else "",
        active=True,
        model=model_slug,
        airgap=airgap,
    )

    return AnalyticsLocalInferenceOut(
        active=True,
        routing_mode="local_sovereign",
        local_model_slug=model_slug,
        airgap=airgap,
        operator_hint=hint,
    )


def build_analytics_session_local_context(local: AnalyticsLocalInferenceOut) -> dict[str, object]:
    """Context seed fields for analytics supervisor sessions when sovereign mode applies."""

    if not local.active:
        return {}
    payload: dict[str, object] = {
        "analytics_local_sovereign": True,
        "analytics_prefer_local_model": local.local_model_slug or _local_model_slug(),
        "analytics_inference_mode": "local_sovereign",
    }
    if local.airgap:
        payload["llm_airgap"] = True
    return payload


def append_local_inference_goal_note(*, goal: str, local: AnalyticsLocalInferenceOut) -> str:
    """Append sovereign inference note to supervisor goal when active."""

    if not local.active:
        return goal
    model = local.local_model_slug or _local_model_slug()
    return (
        f"{goal.rstrip()}\n\n"
        f"=== LOCAL INFERENCE (LOC13) ===\n"
        f"Use tenant local_sovereign routing — model `{model}` only. "
        f"No cloud LLM hops. Critic ≥4/5 and export simulate-first still required.\n"
    )


__all__ = [
    "AnalyticsLocalInferenceOut",
    "append_local_inference_goal_note",
    "build_analytics_session_local_context",
    "resolve_analytics_local_inference",
]
