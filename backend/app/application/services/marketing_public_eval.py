"""Public Eval-as-a-Service lead magnet for letagentscook.org (REV2)."""

from __future__ import annotations

import structlog
from pydantic import BaseModel, ConfigDict, Field
from redis.exceptions import RedisError

from app.application.services.harness_eval_service import HarnessEvalRequest, HarnessEvalResultOut, run_harness_eval
from app.core.config import settings
from app.core.redis_client import sliding_window_reserve

logger = structlog.get_logger(__name__)

_RATE_PREFIX = "queenswarm:marketing_eval:v1"


class MarketingPublicEvalBody(BaseModel):
    """Public eval request — heuristic only, no LLM critic."""

    model_config = ConfigDict(extra="forbid")

    workflow_markdown: str = Field(min_length=40, max_length=20_000)
    title: str = Field(default="Submitted workflow", max_length=200)


async def check_marketing_public_eval_rate_limit(*, client_key: str) -> tuple[bool, str]:
    """Sliding-window cap per client IP for free eval."""

    if not settings.marketing_public_eval_enabled:
        return False, "Public eval disabled."

    limit = int(settings.marketing_public_eval_rate_limit)
    window = float(settings.marketing_public_eval_rate_window_sec)
    bucket = f"{_RATE_PREFIX}:{client_key}"
    try:
        allowed = await sliding_window_reserve(bucket, limit=max(limit, 1), window_sec=window)
    except RedisError as exc:
        logger.warning("marketing_public_eval.rate_limit_redis_error", error=str(exc)[:200])
        return True, ""
    if not allowed:
        return False, f"Free eval limit reached ({limit} per hour). Try again later."
    return True, ""


async def run_marketing_public_eval(body: MarketingPublicEvalBody) -> HarnessEvalResultOut:
    """Run heuristic Eval-as-a-Service for anonymous marketing visitors."""

    return await run_harness_eval(
        HarnessEvalRequest(
            workflow_markdown=body.workflow_markdown,
            title=body.title,
            run_llm_critic=False,
        ),
    )


__all__ = [
    "MarketingPublicEvalBody",
    "check_marketing_public_eval_rate_limit",
    "run_marketing_public_eval",
]
