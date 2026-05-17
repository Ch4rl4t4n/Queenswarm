"""Immutable cached snapshots kept outside Postgres hot paths."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class DynamicConnectorCacheRow:
    """Redis-friendly projection (no ciphertext)."""

    slug: str
    display_name: str
    base_url: str | None
    auth_type: str
    mcp_manifest: dict[str, Any] | None
    allowed_manager_slugs: tuple[str, ...]
    is_active: bool
    is_builtin: bool
    builtin_kind: str | None


__all__ = ["DynamicConnectorCacheRow"]
