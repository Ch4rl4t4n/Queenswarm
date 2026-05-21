"""Unified savings — merge verified time ROI with LLM cost savings."""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.cost_savings import build_cost_savings_payload
from app.application.services.dashboard_time_saved import build_time_saved_payload

DEFAULT_HOURLY_RATE_USD = 50.0


async def build_unified_savings_payload(
    session: AsyncSession,
    *,
    tenant_id: object | None,
    window_days: int = 30,
    hourly_rate_usd: float = DEFAULT_HOURLY_RATE_USD,
) -> dict[str, Any]:
    """Merge time-saved ROI and LLM cost savings into one dashboard payload.

    Args:
        session: Async SQLAlchemy session.
        tenant_id: Active tenant id for cost ledger aggregation (optional).
        window_days: Rolling window length shared by both calculators.
        hourly_rate_usd: Imputed hourly value for verified workflow time saved.

    Returns:
        Unified payload with headline totals and nested time/LLM sections.
    """

    days = max(1, min(int(window_days), 90))
    rate = max(0.0, float(hourly_rate_usd))
    time_payload = await build_time_saved_payload(session, window_days=days)

    llm_payload: dict[str, Any] | None = None
    if tenant_id is not None:
        llm_payload = await build_cost_savings_payload(
            session,
            tenant_id=tenant_id,
            window_days=days,
        )

    hours_total = float(time_payload.get("hours_saved_total") or 0.0)
    time_value_usd = round(hours_total * rate, 2)
    llm_saved_usd = float(llm_payload.get("saved_usd") or 0.0) if llm_payload else 0.0
    total_value_usd = round(time_value_usd + llm_saved_usd, 2)

    return {
        "window_days": days,
        "hourly_rate_usd": rate,
        "headline": {
            "total_value_usd": total_value_usd,
            "time_value_usd": time_value_usd,
            "llm_saved_usd": round(llm_saved_usd, 4),
            "hours_saved_total": hours_total,
            "hours_saved_projected_monthly": float(
                time_payload.get("hours_saved_projected_monthly") or 0.0,
            ),
            "llm_saved_pct": (
                float(llm_payload.get("saved_pct") or 0.0) if llm_payload else None
            ),
            "verified_task_count": int(time_payload.get("verified_task_count") or 0),
            "llm_call_count": int(llm_payload.get("call_count") or 0) if llm_payload else 0,
        },
        "time_saved": time_payload,
        "llm_savings": llm_payload,
        "llm_savings_available": llm_payload is not None,
        "disclaimer": (
            "Total value = imputed time saved (verified tasks × hourly rate) + estimated LLM "
            "spend avoided vs quality-first baseline. Not payroll or tax advice."
        ),
    }


__all__ = ["DEFAULT_HOURLY_RATE_USD", "build_unified_savings_payload"]
