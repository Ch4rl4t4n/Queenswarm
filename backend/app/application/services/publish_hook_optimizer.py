"""Publish hook optimizer — recommend winning hook style per channel (P8 #76)."""

from __future__ import annotations

import uuid
from collections import defaultdict

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.publish_pack import TAG_PUBLISH_PACK
from app.core.config import settings
from app.domain.outputs.service import list_owned_deliverables


class HookWinnerOut(BaseModel):
    """Recommended hook style for one channel."""

    model_config = ConfigDict(extra="ignore")

    channel: str
    winning_style: str
    sample_hook: str
    pack_count: int
    confidence: float


async def build_hook_winner_stats(
    session: AsyncSession,
    *,
    dashboard_user_id: uuid.UUID,
    limit: int = 80,
) -> list[HookWinnerOut]:
    """Aggregate hook variant styles from archived publish packs."""

    if not settings.publish_hook_optimizer_enabled:
        return []

    rows = await list_owned_deliverables(
        session,
        dashboard_user_id=dashboard_user_id,
        limit=max(20, min(limit, 120)),
        tag=TAG_PUBLISH_PACK,
    )

    style_counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    style_samples: dict[str, dict[str, str]] = defaultdict(dict)

    for row in rows:
        structured = dict(row.structured_json) if isinstance(row.structured_json, dict) else {}
        channel = str(structured.get("channel") or "unknown").strip() or "unknown"
        hooks_raw = structured.get("hook_variants")
        if not isinstance(hooks_raw, list):
            continue
        for hook in hooks_raw[:8]:
            if not isinstance(hook, dict):
                continue
            style = str(hook.get("style") or hook.get("id") or "unknown").strip() or "unknown"
            style_counts[channel][style] += 1
            if style not in style_samples[channel]:
                sample = str(hook.get("hook") or "")[:200]
                if sample:
                    style_samples[channel][style] = sample

    winners: list[HookWinnerOut] = []
    for channel, counts in style_counts.items():
        if not counts:
            continue
        winning_style = max(counts, key=counts.get)
        total = sum(counts.values())
        winners.append(
            HookWinnerOut(
                channel=channel,
                winning_style=winning_style,
                sample_hook=style_samples[channel].get(winning_style, ""),
                pack_count=total,
                confidence=round(counts[winning_style] / max(total, 1), 3),
            ),
        )

    return sorted(winners, key=lambda row: row.pack_count, reverse=True)[:12]


__all__ = ["HookWinnerOut", "build_hook_winner_stats"]
