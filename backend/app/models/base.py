"""Compatibility shim — canonical ORM: ``app.infrastructure.persistence.models.base``."""

from __future__ import annotations

from app.infrastructure.persistence.models.base import Base, SoftDeleteMixin, TimestampMixin, UUIDMixin

__all__ = ["Base", "SoftDeleteMixin", "TimestampMixin", "UUIDMixin"]
