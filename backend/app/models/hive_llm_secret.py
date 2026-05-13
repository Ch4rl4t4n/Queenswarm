"""Encrypted LLM API material persisted for dashboard \"vault\" overrides."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class HiveLlmSecret(Base):
    """Per-provider ciphertext; plaintext exists only in process memory after decrypt."""

    __tablename__ = "hive_llm_secrets"

    provider: Mapped[str] = mapped_column(String(32), primary_key=True, nullable=False)
    ciphertext: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        """Return a redacted representation."""

        return f"HiveLlmSecret(provider={self.provider!r})"
