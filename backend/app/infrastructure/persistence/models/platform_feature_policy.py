"""Admin-editable platform feature matrix overrides."""

from __future__ import annotations

from sqlalchemy import Boolean, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, TimestampMixin


class PlatformFeaturePolicy(Base, TimestampMixin):
    """Per-feature, per-profile switch stored by admin operators."""

    __tablename__ = "platform_feature_policies"
    __table_args__ = (
        UniqueConstraint("feature_key", "profile_key", name="uq_platform_feature_policy"),
    )

    feature_key: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    profile_key: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False)

    def __repr__(self) -> str:
        """Return policy diagnostics."""

        return (
            f"PlatformFeaturePolicy(feature_key={self.feature_key!r}, "
            f"profile_key={self.profile_key!r}, enabled={self.enabled!r})"
        )


__all__ = ["PlatformFeaturePolicy"]
