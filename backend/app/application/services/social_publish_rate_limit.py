"""Redis rate limits for live social publish — ban-risk guardrail."""

from __future__ import annotations

import uuid

import structlog
from pydantic import BaseModel, ConfigDict, Field
from redis.exceptions import RedisError

from app.application.services.social_publish import SOCIAL_OAUTH_CHANNEL_IDS, SocialChannelId, SocialPublishMode
from app.core.config import settings
from app.core.redis_client import sliding_window_count, sliding_window_reserve

logger = structlog.get_logger(__name__)

_BUCKET_PREFIX = "queenswarm:social_publish:live"


class SocialPublishRateLimitChannelOut(BaseModel):
    """Per-channel live publish quota for operator UI."""

    model_config = ConfigDict(extra="ignore")

    channel: SocialChannelId
    used: int = 0
    max_per_channel: int = 10
    remaining: int = 10


class SocialPublishRateLimitSnapshotOut(BaseModel):
    """Read-only rate limit counters for Social publish panel."""

    model_config = ConfigDict(extra="ignore")

    enabled: bool = False
    fail_closed: bool = True
    window_sec: float = 86400.0
    window_hours: int = 24
    global_used: int = 0
    global_max: int = 30
    global_remaining: int = 30
    channels: list[SocialPublishRateLimitChannelOut] = Field(default_factory=list)
    redis_ok: bool = True


async def check_social_publish_rate_limit(
    *,
    dashboard_user_id: uuid.UUID,
    channel: SocialChannelId,
    mode: SocialPublishMode,
) -> tuple[bool, str]:
    """Return (allowed, message). Simulate always allowed."""

    if mode != "live" or not settings.social_publish_rate_limit_enabled:
        return True, ""

    per_channel_max = int(settings.social_publish_live_daily_max_per_channel)
    global_max = int(settings.social_publish_live_daily_max_global)
    window_sec = float(settings.social_publish_rate_limit_window_sec)

    channel_key = f"{_BUCKET_PREFIX}:{dashboard_user_id}:{channel}"
    global_key = f"{_BUCKET_PREFIX}:{dashboard_user_id}:all"

    try:
        channel_ok = await sliding_window_reserve(
            channel_key,
            limit=max(per_channel_max, 1),
            window_sec=window_sec,
        )
        if not channel_ok:
            logger.warning(
                "social_publish.rate_limited",
                agent_id="social_publish",
                swarm_id=channel,
                task_id=str(dashboard_user_id),
                scope="channel",
            )
            return (
                False,
                f"Live publish rate limit reached for {channel} "
                f"({per_channel_max} per {int(window_sec // 3600)}h). Retry later.",
            )

        global_ok = await sliding_window_reserve(
            global_key,
            limit=max(global_max, 1),
            window_sec=window_sec,
        )
        if not global_ok:
            logger.warning(
                "social_publish.rate_limited",
                agent_id="social_publish",
                swarm_id="all",
                task_id=str(dashboard_user_id),
                scope="global",
            )
            return (
                False,
                f"Global live publish rate limit reached ({global_max} per {int(window_sec // 3600)}h).",
            )
    except RedisError as exc:
        logger.error(
            "social_publish.rate_limit_redis_error",
            agent_id="social_publish",
            error=str(exc)[:200],
        )
        if settings.social_publish_rate_limit_fail_closed:
            return False, "Rate limiter unavailable — live publish blocked (fail-closed)."
        return True, ""

    return True, ""


async def build_social_publish_rate_limit_snapshot(
    *,
    dashboard_user_id: uuid.UUID,
) -> SocialPublishRateLimitSnapshotOut:
    """Build read-only quota snapshot for operator dashboard."""

    per_channel_max = int(settings.social_publish_live_daily_max_per_channel)
    global_max = int(settings.social_publish_live_daily_max_global)
    window_sec = float(settings.social_publish_rate_limit_window_sec)
    window_hours = max(int(window_sec // 3600), 1)
    enabled = bool(settings.social_publish_rate_limit_enabled)

    global_key = f"{_BUCKET_PREFIX}:{dashboard_user_id}:all"
    redis_ok = True
    global_used = 0
    channel_rows: list[SocialPublishRateLimitChannelOut] = []

    try:
        global_used = await sliding_window_count(global_key, window_sec=window_sec)
        for channel_id in sorted(SOCIAL_OAUTH_CHANNEL_IDS):
            channel_key = f"{_BUCKET_PREFIX}:{dashboard_user_id}:{channel_id}"
            used = await sliding_window_count(channel_key, window_sec=window_sec)
            channel_rows.append(
                SocialPublishRateLimitChannelOut(
                    channel=channel_id,
                    used=used,
                    max_per_channel=per_channel_max,
                    remaining=max(per_channel_max - used, 0),
                ),
            )
    except RedisError as exc:
        redis_ok = False
        logger.warning(
            "social_publish.rate_limit_snapshot_error",
            agent_id="social_publish",
            task_id=str(dashboard_user_id),
            error=str(exc)[:200],
        )

    return SocialPublishRateLimitSnapshotOut(
        enabled=enabled,
        fail_closed=bool(settings.social_publish_rate_limit_fail_closed),
        window_sec=window_sec,
        window_hours=window_hours,
        global_used=global_used,
        global_max=global_max,
        global_remaining=max(global_max - global_used, 0),
        channels=channel_rows,
        redis_ok=redis_ok,
    )


__all__ = [
    "SocialPublishRateLimitChannelOut",
    "SocialPublishRateLimitSnapshotOut",
    "build_social_publish_rate_limit_snapshot",
    "check_social_publish_rate_limit",
]
