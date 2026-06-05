"""Public trading transparency — deprecated (paper trading removed)."""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession


class PublicTradingTransparencyOut(BaseModel):
    """Public read-only trading stats — paper lane removed."""

    model_config = ConfigDict(extra="ignore")

    enabled: bool = False
    generated_at: datetime
    mode: str = "polymarket_live"
    total_equity_usd: float = 0.0
    total_pnl_usd: float = 0.0
    total_pnl_pct: float = 0.0
    project_count: int = 0
    recent_fills: list[dict[str, str]] = []
    disclaimer: str = "Paper trading removed. Use Polymarket live lane in authenticated app only."


async def build_public_trading_transparency(_session: AsyncSession) -> PublicTradingTransparencyOut:
    """Return disabled stub — paper transparency no longer published."""

    return PublicTradingTransparencyOut(
        enabled=False,
        generated_at=datetime.now(tz=UTC),
    )


__all__ = ["PublicTradingTransparencyOut", "build_public_trading_transparency"]
