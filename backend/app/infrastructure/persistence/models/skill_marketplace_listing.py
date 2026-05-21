"""Tenant-submitted skill listings awaiting curator approval."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

LISTING_PENDING = "pending_review"
LISTING_APPROVED = "approved"
LISTING_REJECTED = "rejected"
LISTING_WITHDRAWN = "withdrawn"


class SkillMarketplaceListing(Base):
    """UGC premium skill listing — curator gate before public marketplace."""

    __tablename__ = "skill_marketplace_listings"
    __table_args__ = (
        UniqueConstraint("recipe_id", name="uq_skill_marketplace_listings_recipe"),
    )

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    publisher_tenant_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    publisher_user_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    recipe_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("recipes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default=LISTING_PENDING, index=True)
    price_eur_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    platform_cut_bps: Mapped[int] = mapped_column(Integer, nullable=False, default=2500)
    pitch: Mapped[str | None] = mapped_column(Text, nullable=True)
    curator_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewer_user_id: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return (
            f"SkillMarketplaceListing(id={self.id!s}, recipe_id={self.recipe_id!s}, "
            f"status={self.status!r}, price_eur_cents={self.price_eur_cents})"
        )


__all__ = [
    "LISTING_APPROVED",
    "LISTING_PENDING",
    "LISTING_REJECTED",
    "LISTING_WITHDRAWN",
    "SkillMarketplaceListing",
]
