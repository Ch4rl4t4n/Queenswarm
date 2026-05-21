"""Estimate LLM spend saved vs quality-first baseline from CostRecord ledger."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.llm_routing import load_routing_config
from app.infrastructure.persistence.models.cost import CostRecord


def quality_baseline_multiplier(model_slug: str) -> float:
    """Heuristic multiplier: what quality-primary hop would cost vs this model."""

    lowered = model_slug.lower()
    if "gpt-4o-mini" in lowered or "mini" in lowered:
        return 8.0
    if "haiku" in lowered:
        return 3.5
    if "claude" in lowered:
        return 4.0
    if "grok" in lowered and "mini" in lowered:
        return 2.5
    return 1.0


async def build_cost_savings_payload(
    session: AsyncSession,
    *,
    tenant_id: object,
    window_days: int = 30,
) -> dict[str, Any]:
    """Aggregate actual vs estimated quality-baseline LLM spend for one tenant."""

    days = max(1, min(int(window_days), 365))
    since = datetime.now(tz=UTC) - timedelta(days=days)
    rows = list(
        (
            await session.scalars(
                select(CostRecord).where(
                    CostRecord.tenant_id == tenant_id,
                    CostRecord.created_at >= since,
                ),
            )
        ).all(),
    )
    actual_usd = float(sum(float(r.cost_usd or 0.0) for r in rows))
    baseline_usd = float(
        sum(float(r.cost_usd or 0.0) * quality_baseline_multiplier(r.llm_model) for r in rows),
    )
    saved_usd = max(0.0, baseline_usd - actual_usd)
    tokens_in = int(sum(int(r.tokens_in or 0) for r in rows))
    tokens_out = int(sum(int(r.tokens_out or 0) for r in rows))
    routing = await load_routing_config(session, tenant_id=tenant_id)

    by_model: dict[str, float] = {}
    for row in rows:
        key = str(row.llm_model or "unknown")
        by_model[key] = by_model.get(key, 0.0) + float(row.cost_usd or 0.0)

    return {
        "window_days": days,
        "call_count": len(rows),
        "actual_usd": round(actual_usd, 4),
        "quality_baseline_usd": round(baseline_usd, 4),
        "saved_usd": round(saved_usd, 4),
        "saved_pct": round((saved_usd / baseline_usd * 100.0) if baseline_usd > 0 else 0.0, 1),
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "routing_mode": routing.get("routing_mode", "quality"),
        "cost_guardian_enabled": bool(routing.get("cost_guardian_enabled", True)),
        "spend_by_model": [
            {"model": model, "spend_usd": round(spend, 4)}
            for model, spend in sorted(by_model.items(), key=lambda item: item[1], reverse=True)
        ],
    }


__all__ = ["build_cost_savings_payload", "quality_baseline_multiplier"]
