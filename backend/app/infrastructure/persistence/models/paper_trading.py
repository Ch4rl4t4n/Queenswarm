"""Paper trading ledger — accounts and fill history (no live broker)."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String, Text, UniqueConstraint, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.infrastructure.persistence.models.base import TenantScopedMixin


class PaperTradingAccount(Base, TenantScopedMixin):
    """Simulated cash + P&L envelope for one external trading project."""

    __tablename__ = "paper_trading_accounts"
    __table_args__ = (UniqueConstraint("project_id", name="uq_paper_trading_accounts_project_id"),)

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("external_projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    cash_usd: Mapped[Decimal] = mapped_column(Numeric(16, 4), nullable=False, server_default=text("10000"))
    starting_cash_usd: Mapped[Decimal] = mapped_column(Numeric(16, 4), nullable=False, server_default=text("10000"))
    realized_pnl_usd: Mapped[Decimal] = mapped_column(Numeric(16, 4), nullable=False, server_default=text("0"))
    daily_realized_pnl_usd: Mapped[Decimal] = mapped_column(Numeric(16, 4), nullable=False, server_default=text("0"))
    daily_pnl_reset_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_halted: Mapped[bool] = mapped_column(Boolean(), nullable=False, server_default=text("false"))
    halt_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    last_tick_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    watchlist: Mapped[list[str]] = mapped_column(JSONB, nullable=False, server_default=text("'[\"BTC\",\"ETH\"]'::jsonb"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"PaperTradingAccount(project_id={self.project_id!s}, cash={self.cash_usd})"


class PaperTradingFill(Base, TenantScopedMixin):
    """Immutable simulated execution row."""

    __tablename__ = "paper_trading_fills"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("external_projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    account_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("paper_trading_accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    symbol: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    side: Mapped[str] = mapped_column(String(8), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    fill_price_usd: Mapped[Decimal] = mapped_column(Numeric(16, 4), nullable=False)
    fees_usd: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False, server_default=text("0"))
    notional_usd: Mapped[Decimal] = mapped_column(Numeric(16, 4), nullable=False)
    confidence: Mapped[Decimal] = mapped_column(Numeric(6, 4), nullable=False, server_default=text("0"))
    signal_note: Mapped[str] = mapped_column(Text(), nullable=False, server_default=text("''"))
    verified: Mapped[bool] = mapped_column(Boolean(), nullable=False, server_default=text("true"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    def __repr__(self) -> str:
        return f"PaperTradingFill({self.side} {self.quantity} {self.symbol} @ {self.fill_price_usd})"


__all__ = ["PaperTradingAccount", "PaperTradingFill"]
