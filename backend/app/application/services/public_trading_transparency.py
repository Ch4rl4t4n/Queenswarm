"""Public paper-trading transparency — sanitized aggregate (P9 #82)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.paper_trading_service import build_dashboard_paper_summary
from app.core.config import settings


class PublicFillOut(BaseModel):
    """Sanitized fill row — symbol and side only."""

    model_config = ConfigDict(extra="ignore")

    symbol: str
    side: str


class PublicTradingTransparencyOut(BaseModel):
    """Public read-only paper trading stats — no secrets, no user IDs."""

    model_config = ConfigDict(extra="ignore")

    enabled: bool
    generated_at: datetime
    mode: str = "paper"
    total_equity_usd: float = 0.0
    total_pnl_usd: float = 0.0
    total_pnl_pct: float = 0.0
    project_count: int = 0
    recent_fills: list[PublicFillOut] = Field(default_factory=list)
    disclaimer: str = ""


async def build_public_trading_transparency(session: AsyncSession) -> PublicTradingTransparencyOut:
    """Build public-safe aggregate from paper trading projects."""

    if not settings.public_trading_transparency_enabled:
        return PublicTradingTransparencyOut(
            enabled=False,
            generated_at=datetime.now(tz=UTC),
        )

    summary = await build_dashboard_paper_summary(session)
    total_equity = float(summary.get("total_equity_usd") or 0.0)
    total_pnl = float(summary.get("total_pnl_usd") or 0.0)
    starting = max(total_equity - total_pnl, 1.0)
    pnl_pct = round((total_pnl / starting) * 100.0, 2) if starting else 0.0

    fills: list[PublicFillOut] = []
    for proj in summary.get("projects") or []:
        if not isinstance(proj, dict):
            continue
        for fill in proj.get("recent_fills") or []:
            if not isinstance(fill, dict):
                continue
            symbol = str(fill.get("symbol") or "").strip().upper()
            side = str(fill.get("side") or "").strip().lower()
            if symbol and side:
                fills.append(PublicFillOut(symbol=symbol[:16], side=side[:8]))
            if len(fills) >= 10:
                break
        if len(fills) >= 10:
            break

    return PublicTradingTransparencyOut(
        enabled=True,
        generated_at=datetime.now(tz=UTC),
        mode="paper",
        total_equity_usd=round(total_equity, 2),
        total_pnl_usd=round(total_pnl, 2),
        total_pnl_pct=pnl_pct,
        project_count=int(summary.get("project_count") or 0),
        recent_fills=fills,
        disclaimer=str(
            summary.get("disclaimer")
            or "Paper trading only — simulated fills. Not financial advice.",
        ),
    )


__all__ = ["PublicTradingTransparencyOut", "build_public_trading_transparency"]
