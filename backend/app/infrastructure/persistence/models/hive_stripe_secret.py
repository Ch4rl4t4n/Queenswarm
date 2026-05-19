"""Encrypted Stripe platform credentials for premium skill checkout."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class HiveStripeSecret(Base):
    """Singleton row (``id=1``) holding ciphertext for Stripe API + webhook secrets."""

    __tablename__ = "hive_stripe_secrets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, nullable=False, default=1)
    secret_key_ciphertext: Mapped[str | None] = mapped_column(Text, nullable=True)
    webhook_secret_ciphertext: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        """Return a redacted representation."""

        return "HiveStripeSecret(id=1)"
